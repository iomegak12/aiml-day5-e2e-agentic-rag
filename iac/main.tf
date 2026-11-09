# NetCore Agentic RAG on one EC2 instance: Ubuntu 24.04 + Docker CE, all containers from Docker Hub.
#
#   EIP:80  -> web (Nginx gateway) -> api -> mcp / chroma / redis / postgres      (only 22 + 80 are open)

locals {
  ssh_cidr     = var.ssh_cidr != "" ? var.ssh_cidr : "${chomp(data.http.my_ip.response_body)}/32"
  key_path     = "${path.module}/.keys/${var.name}-ec2.pem"
  remote_dir   = "/tmp/netcore"
  deploy_files = ["compose.prod.yaml", "deploy.sh"]
}

# ---------------------------- lookups ----------------------------

data "aws_ami" "ubuntu" {
  most_recent = true
  owners      = ["099720109477"] # Canonical

  filter {
    name   = "name"
    values = ["ubuntu/images/hvm-ssd-gp3/ubuntu-noble-24.04-amd64-server-*"]
  }
  filter {
    name   = "virtualization-type"
    values = ["hvm"]
  }
}

data "aws_vpc" "default" {
  default = true
}

data "aws_subnets" "default" {
  filter {
    name   = "vpc-id"
    values = [data.aws_vpc.default.id]
  }
  filter {
    name   = "default-for-az"
    values = ["true"]
  }
}

data "http" "my_ip" {
  url = "https://checkip.amazonaws.com"
}

# ---------------------------- SSH key pair (new, generated here) ----------------------------

resource "tls_private_key" "ssh" {
  algorithm = "ED25519"
}

resource "aws_key_pair" "this" {
  key_name   = "${var.name}-key"
  public_key = tls_private_key.ssh.public_key_openssh
}

resource "local_sensitive_file" "private_key" {
  filename        = local.key_path
  content         = tls_private_key.ssh.private_key_openssh
  file_permission = "0600"
}

# ---------------------------- network ----------------------------

resource "aws_security_group" "this" {
  name        = "${var.name}-sg"
  description = "NetCore RAG: SSH from the operator IP, HTTP (web gateway) from anywhere"
  vpc_id      = data.aws_vpc.default.id

  ingress {
    description = "SSH (operator only)"
    from_port   = 22
    to_port     = 22
    protocol    = "tcp"
    cidr_blocks = [local.ssh_cidr]
  }

  ingress {
    description = "Web UI + API gateway (Nginx)"
    from_port   = 80
    to_port     = 80
    protocol    = "tcp"
    cidr_blocks = ["0.0.0.0/0"]
  }

  egress {
    description = "All outbound (Docker Hub, OpenAI, Serper, Jira, apt)"
    from_port   = 0
    to_port     = 0
    protocol    = "-1"
    cidr_blocks = ["0.0.0.0/0"]
  }
}

# ---------------------------- instance ----------------------------

resource "aws_instance" "this" {
  ami                         = data.aws_ami.ubuntu.id
  instance_type               = var.instance_type
  subnet_id                   = sort(data.aws_subnets.default.ids)[0]
  vpc_security_group_ids      = [aws_security_group.this.id]
  key_name                    = aws_key_pair.this.key_name
  associate_public_ip_address = true
  user_data                   = file("${path.module}/cloud-init.yaml")
  user_data_replace_on_change = true

  root_block_device {
    volume_size           = var.root_volume_gb
    volume_type           = "gp3"
    encrypted             = true
    delete_on_termination = true
  }

  metadata_options {
    http_tokens   = "required" # IMDSv2 only
    http_endpoint = "enabled"
  }

  tags = {
    Name = var.name
  }
}

resource "aws_eip" "this" {
  domain   = "vpc"
  instance = aws_instance.this.id

  tags = {
    Name = "${var.name}-eip"
  }
}

# ---------------------------- deployment (SSH) ----------------------------
# Re-runs when the instance, the version or any uploaded file changes. Only file hashes are kept in state.

resource "terraform_data" "deploy" {
  triggers_replace = {
    instance = aws_instance.this.id
    version  = var.app_version
    hub_user = var.hub_user
    files    = join(",", [for f in local.deploy_files : filesha256("${path.module}/${f}")])
    app_env  = filesha256("${path.module}/${var.app_env_file}")
  }

  connection {
    type        = "ssh"
    host        = aws_eip.this.public_ip
    user        = "ubuntu"
    private_key = tls_private_key.ssh.private_key_openssh
    timeout     = "10m"
  }

  # 1. wait until cloud-init has installed Docker CE (exit code 2 = finished with warnings)
  provisioner "remote-exec" {
    inline = [
      "cloud-init status --wait > /dev/null || true",
      "docker --version && docker compose version",
      "rm -rf ${local.remote_dir} && mkdir -p ${local.remote_dir}",
    ]
  }

  provisioner "file" {
    source      = "${path.module}/compose.prod.yaml"
    destination = "${local.remote_dir}/compose.prod.yaml"
  }

  provisioner "file" {
    source      = "${path.module}/deploy.sh"
    destination = "${local.remote_dir}/deploy.sh"
  }

  provisioner "file" {
    source      = "${path.module}/${var.app_env_file}"
    destination = "${local.remote_dir}/app.env"
  }

  provisioner "file" {
    source      = "${path.module}/${var.chroma_snapshot}"
    destination = "${local.remote_dir}/chroma-data.tgz"
  }

  # 2. install the files, restore Chroma (first deploy), pull and start everything
  provisioner "remote-exec" {
    inline = [
      "sed -i 's/\\r$//' ${local.remote_dir}/deploy.sh ${local.remote_dir}/app.env",
      "sudo bash ${local.remote_dir}/deploy.sh ${var.hub_user} ${var.app_version}",
    ]
  }
}
