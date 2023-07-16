locals {
  workflow_cpu_allocation = "1"
  workflow_memory_allocation = "1GB"
}

# Generate and store the admin password in AWS SSM Parameter Store
resource "random_password" "admin_password" {
  length = 32
  special = true
}

resource "aws_ssm_parameter" "admin_password" {
  name = "/${local.project_name}/common/admin_password"
  type = "SecureString"
  value = random_password.admin_password.result
}

# Shared Database resources
resource "aws_db_subnet_group" "default" {
  name       = "main"
  subnet_ids = module.vpc.private_subnets
}