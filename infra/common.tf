# Common resources used by all tools.

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

# K8s service account for pods
resource "kubernetes_service_account" "workflow" {
  depends_on = [
    time_sleep.wait_for_cluster
  ]
  metadata {
    name = "workflow"
    namespace = "default"
    annotations = {
      "eks.amazonaws.com/role-arn" = aws_iam_role.workflow.arn
    }
  }
}

# IAM role for pods
data "aws_iam_policy_document" "workflow_trust" {
  statement {
    actions = ["sts:AssumeRoleWithWebIdentity"]
    effect = "Allow"
    principals {
      identifiers = [aws_iam_openid_connect_provider.eks.arn]
      type = "Federated"
    }
  }
}

resource "aws_iam_role" "workflow" {
    name = "workflow"
    assume_role_policy = data.aws_iam_policy_document.workflow_trust.json
}

data "aws_iam_policy_document" "workflow" {
  statement {
    actions = ["kms:*"]

    resources = ["*"]
  }

  statement {
    actions = ["s3:*"]

    resources = ["*"]
  }
}

resource "aws_iam_role_policy" "workflow" {
  name = "workflow"
  role = aws_iam_role.workflow.id
  policy = data.aws_iam_policy_document.workflow.json
}
