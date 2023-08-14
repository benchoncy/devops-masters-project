locals {
  project_name = "devops-masters-project"
}

variable "aws_region" {
  type    = string
  default = "eu-west-1"
}

terraform {
  backend "s3" {
    bucket         = "bstuart-tf-state"
    key            = "devops-masters-project/terraform.tfstate"
    dynamodb_table = "tf-state-locking-table"
    region         = "eu-west-1"
  }
  required_providers {
    aws = {
      source  = "hashicorp/aws"
      version = "~> 5.7"
    }
    helm = {
      source  = "hashicorp/helm"
      version = "~> 2.10"
    }
    kubernetes = {
      source  = "hashicorp/kubernetes"
      version = "~> 2.22"
    }
    random = {
      source  = "hashicorp/random"
      version = "~> 3.1"
    }
  }
}

provider "aws" {
  region = var.aws_region
  default_tags {
    tags = {
      Project = local.project_name
      Repo = "https://github.com/benchoncy/${local.project_name}"
      ManagedBy = "Terraform"
    }
  }
}

provider "helm" {
  kubernetes {
    config_path = "~/.kube/config"
  }
}

provider "kubernetes" {
  config_path = "~/.kube/config"
}
