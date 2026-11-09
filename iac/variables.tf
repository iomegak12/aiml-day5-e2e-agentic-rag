variable "name" {
  description = "Name prefix for every resource (instance, key pair, security group, EIP)."
  type        = string
  default     = "netcore-rag"
}

variable "instance_type" {
  description = "EC2 instance type. t3.small (2 GiB) fits the six containers; a 2 GiB swap file adds headroom."
  type        = string
  default     = "t3.small"
}

variable "root_volume_gb" {
  description = "Root EBS volume size (gp3, encrypted). Images take about 4 GiB."
  type        = number
  default     = 30
}

variable "app_version" {
  description = "Image tag deployed from Docker Hub (make passes VERSION from the Makefile)."
  type        = string
  default     = "0.10.0"
}

variable "hub_user" {
  description = "Docker Hub user that owns the netcore-rag-* images (make passes HUB_USER)."
  type        = string
  default     = "iomega"
}

variable "ssh_cidr" {
  description = "CIDR allowed to SSH (port 22). Empty = your current public IP (/32), detected at plan time."
  type        = string
  default     = ""
}

variable "app_env_file" {
  description = "Filtered application env uploaded to the instance (written by prepare.py; no AWS_* / DOCKERHUB_*)."
  type        = string
  default     = ".build/app.env"
}

variable "chroma_snapshot" {
  description = "Tarball of the local chroma-data volume (written by prepare.py); restored when the remote volume is empty."
  type        = string
  default     = ".build/chroma-data.tgz"
}
