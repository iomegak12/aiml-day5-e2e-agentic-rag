terraform {
  required_version = ">= 1.6"

  required_providers {
    aws = {
      source  = "hashicorp/aws"
      version = "~> 6.72"
    }
    tls = {
      source  = "hashicorp/tls"
      version = "~> 4.4"
    }
    http = {
      source  = "hashicorp/http"
      version = "~> 3.6"
    }
    local = {
      source  = "hashicorp/local"
      version = "~> 2.9"
    }
  }
}

# Credentials and region come from the environment: AWS_ACCESS_KEY_ID, AWS_SECRET_ACCESS_KEY, AWS_REGION
# (the make iac-* targets load them from the project .env with `uv run --env-file .env`).
provider "aws" {
  default_tags {
    tags = {
      Project   = var.name
      ManagedBy = "terraform"
      Version   = var.app_version
    }
  }
}
