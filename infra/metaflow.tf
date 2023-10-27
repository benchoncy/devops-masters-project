# All required config to setup Metaflow using EKS.

locals {
  metaflow_resource_prefix = "metaflow"
  metaflow_resource_suffix = ""
}

# Metaflow Setup
resource "aws_kms_key" "metaflow_datastore" {
	description = "Metaflow datastore KMS key"
}

resource "aws_s3_bucket" "metaflow_store" {
  bucket = "bstuart-${local.project_name}-metaflow-store"
	force_destroy = true
}

resource "aws_s3_bucket_server_side_encryption_configuration" "metaflow_store" {
	bucket = aws_s3_bucket.metaflow_store.bucket
	rule {
		apply_server_side_encryption_by_default {
			sse_algorithm = "aws:kms"
			kms_master_key_id = aws_kms_key.metaflow_datastore.arn
		}
	}
	
}

resource "random_password" "metaflow_db_password" {
  length = 8
  special = false
}

resource "aws_rds_cluster" "metaflow" {
  cluster_identifier      = "${local.project_name}-metaflow"
  engine                  = "aurora-postgresql"
  engine_mode             = "provisioned"
  engine_version          = "13.6"
  database_name           = "metaflow"
  master_username         = "master"
  master_password         = random_password.metaflow_db_password.result
  skip_final_snapshot     = true
  apply_immediately       = true
  availability_zones      = local.azs
  db_subnet_group_name    = aws_db_subnet_group.default.name

  serverlessv2_scaling_configuration {
    max_capacity = 1.0
    min_capacity = 0.5
  }
}

resource "aws_rds_cluster_instance" "metaflow" {
  cluster_identifier   = aws_rds_cluster.metaflow.id
  instance_class       = "db.serverless"
  engine               = aws_rds_cluster.metaflow.engine
  engine_version       = aws_rds_cluster.metaflow.engine_version
  db_subnet_group_name = aws_db_subnet_group.default.name
}

module "metaflow-common" {
  source  = "outerbounds/metaflow/aws//modules/common"
  version = "0.9.4"
}

module "metaflow-metadata-service" {
  source  = "outerbounds/metaflow/aws//modules/metadata-service"
  version = "0.9.4"

  resource_prefix = local.metaflow_resource_prefix
  resource_suffix = local.metaflow_resource_suffix

  access_list_cidr_blocks          = []
  enable_api_basic_auth            = true
  enable_api_gateway               = true
  database_name                    = aws_rds_cluster.metaflow.database_name
  database_password                = random_password.metaflow_db_password.result
  database_username                = aws_rds_cluster.metaflow.master_username
  datastore_s3_bucket_kms_key_arn  = aws_kms_key.metaflow_datastore.arn
  fargate_execution_role_arn       = aws_iam_role.ecs_execution_role.arn
  metaflow_vpc_id                  = module.vpc.vpc_id
  metadata_service_container_image = module.metaflow-common.default_metadata_service_container_image
  rds_master_instance_endpoint     = aws_rds_cluster_instance.metaflow.endpoint
  s3_bucket_arn                    = aws_s3_bucket.metaflow_store.arn
  subnet1_id                       = module.vpc.private_subnets[0]
  subnet2_id                       = module.vpc.private_subnets[1]
  vpc_cidr_blocks                  = [module.vpc.vpc_cidr_block]
  with_public_ip                   = false
  standard_tags				       = {}
}

# Metaflow config
data "aws_api_gateway_api_key" "metadata_api_key" {
  depends_on = [module.metaflow-metadata-service]
  id = module.metaflow-metadata-service.api_gateway_rest_api_id_key_id
}

data "aws_caller_identity" "current" {}

resource "local_file" "metaflow_config_argo" {
  content  = <<-EOT
    {
      "METAFLOW_DATASTORE_SYSROOT_S3": "s3://${aws_s3_bucket.metaflow_store.id}/metaflow",
      "METAFLOW_DATATOOLS_S3ROOT": "s3://${aws_s3_bucket.metaflow_store.id}/data",
      "METAFLOW_SERVICE_URL": "${module.metaflow-metadata-service.METAFLOW_SERVICE_URL}",
      "METAFLOW_SERVICE_INTERNAL_URL": "${module.metaflow-metadata-service.METAFLOW_SERVICE_URL}",
      "METAFLOW_SERVICE_AUTH_KEY": "${data.aws_api_gateway_api_key.metadata_api_key.value}",
      "METAFLOW_KUBERNETES_CONTAINER_REGISTRY": "${data.aws_caller_identity.current.account_id}.dkr.ecr.${var.aws_region}.amazonaws.com/",
      "METAFLOW_KUBERNETES_CONTAINER_IMAGE": "benchoncy-${local.project_name}/metaflow:latest",
      "METAFLOW_KUBERNETES_NAMESPACE": "default",
      "METAFLOW_KUBERNETES_SERVICE_ACCOUNT": "workflow",
      "METAFLOW_DEFAULT_DATASTORE": "s3",
      "METAFLOW_DEFAULT_METADATA": "service"
    }
    EOT
  filename = "${path.module}/config/config_argo.json"
}

resource "local_file" "metaflow_config_airflow" {
  content  = jsonencode({
    "METAFLOW_DEFAULT_CONTAINER_REGISTRY"  = "${data.aws_caller_identity.current.account_id}.dkr.ecr.${var.aws_region}.amazonaws.com/"
    "METAFLOW_DEFAULT_CONTAINER_IMAGE"     = "benchoncy-${local.project_name}/metaflow:latest"
    "METAFLOW_DATASTORE_SYSROOT_S3"        = "s3://${aws_s3_bucket.metaflow_store.arn}/metaflow"
    "METAFLOW_DATATOOLS_S3ROOT"            = "s3://${aws_s3_bucket.metaflow_store.arn}/data"
    "METAFLOW_SERVICE_URL"                 = module.metaflow-metadata-service.METAFLOW_SERVICE_URL
    "METAFLOW_KUBERNETES_NAMESPACE"        = local.airflow_namespace
    "METAFLOW_DEFAULT_DATASTORE"           = "s3"
    "METAFLOW_DEFAULT_METADATA"            = "service"
  })
  filename = "${path.module}/config/config_airflow.json"
}


# IAM Setup
data "aws_iam_policy_document" "ecs_execution_role_assume_role" {
  statement {
    actions = [
      "sts:AssumeRole"
    ]

    effect = "Allow"

    principals {
      identifiers = [
        "ec2.amazonaws.com",
        "ecs.amazonaws.com",
        "ecs-tasks.amazonaws.com",
        "batch.amazonaws.com"
      ]
      type = "Service"
    }
  }
}

resource "aws_iam_role" "ecs_execution_role" {
  name = "${local.metaflow_resource_prefix}ecs-execution-role${local.metaflow_resource_suffix}"
  description        = "Metaflow ECS Execution Role"
  assume_role_policy = data.aws_iam_policy_document.ecs_execution_role_assume_role.json
}

data "aws_iam_policy_document" "ecs_task_execution_policy" {
  statement {
    effect = "Allow"
    actions = [
      "ecr:GetAuthorizationToken",
      "ecr:BatchCheckLayerAvailability",
      "ecr:GetDownloadUrlForLayer",
      "ecr:BatchGetImage",
      "logs:CreateLogStream",
      "logs:PutLogEvents"
    ]
    resources = [
      "*"
    ]
  }
}

resource "aws_iam_role_policy" "grant_ecs_access" {
  name   = "ecs_access"
  role   = aws_iam_role.ecs_execution_role.name
  policy = data.aws_iam_policy_document.ecs_task_execution_policy.json
}
