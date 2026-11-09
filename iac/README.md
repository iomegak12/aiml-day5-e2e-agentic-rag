# iac/ - NetCore Agentic RAG on AWS EC2 (Terraform)

One EC2 instance (Ubuntu 24.04, Docker CE) running the whole stack from the Docker Hub images.
Use the make targets from the project root; they load the AWS credentials from `.env`:

| Step | Command |
|---|---|
| Push images | `make publish` |
| Providers | `make iac-init` |
| Preview | `make iac-plan` |
| Create + deploy | `make iac-up` |
| Outputs | `make iac-output` |
| SSH / remote command | `make iac-ssh` / `make iac-ssh CMD="docker ps"` |
| Destroy | `make iac-down` |

| File | Purpose |
|---|---|
| `versions.tf` | Terraform and provider versions; AWS provider (region and credentials from the environment) |
| `variables.tf` | `instance_type` (t3.small), `root_volume_gb`, `app_version`, `hub_user`, `ssh_cidr`, upload paths |
| `main.tf` | AMI lookup, default VPC, key pair, security group, instance, EIP, `terraform_data.deploy` |
| `outputs.tf` | `web_url`, `ssh_command`, `tunnel_command`, `public_ip`, ... |
| `cloud-init.yaml` | First boot: Docker CE + compose plugin, swap, log rotation |
| `compose.prod.yaml` | The stack on the server (Hub images, memory limits, only port 80 public) |
| `deploy.sh` | Runs on the server: install files, restore Chroma on first deploy, pull, `up --wait` |
| `prepare.py` | Runs locally: `.build/app.env` (without AWS_/DOCKERHUB_) and `.build/chroma-data.tgz` |
| `ssh.py` | SSH helper (key permissions, optional remote command) |

Generated and git-ignored: `.terraform/`, `terraform.tfstate*` (contains the private key), `.keys/`, `.build/`.
Commit `.terraform.lock.hcl`.
