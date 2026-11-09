output "public_ip" {
  description = "Elastic IP of the instance."
  value       = aws_eip.this.public_ip
}

output "web_url" {
  description = "Web UI (sign in with a key from API_KEYS)."
  value       = "http://${aws_eip.this.public_ip}/"
}

output "ssh_command" {
  description = "SSH into the instance (or: make iac-ssh)."
  value       = "ssh -i iac/.keys/${var.name}-ec2.pem ubuntu@${aws_eip.this.public_ip}"
}

output "tunnel_command" {
  description = "Reach the API docs (8080) and the MCP server (9090) through SSH; they are not exposed publicly."
  value       = "ssh -i iac/.keys/${var.name}-ec2.pem -N -L 8080:localhost:8080 -L 9090:localhost:9090 ubuntu@${aws_eip.this.public_ip}"
}

output "private_key_path" {
  description = "Generated SSH private key (git-ignored)."
  value       = local_sensitive_file.private_key.filename
}

output "instance_id" {
  value = aws_instance.this.id
}

output "ami" {
  description = "Ubuntu 24.04 AMI used."
  value       = "${data.aws_ami.ubuntu.id} (${data.aws_ami.ubuntu.name})"
}

output "ssh_allowed_from" {
  value = local.ssh_cidr
}
