locals {
  airflow_namespace = "airflow"
  airflow_values = {
    FERNET_KEY = random_id.fernet_key.id
    WEB_SERVER_SECRET_KEY = random_password.web_server_secret_key.result
    AIRFLOW_ADMIN_PASSWORD = random_password.admin_password.result
    WORKFLOW_CPU_ALLOCATION = local.workflow_cpu_allocation
    WORKFLOW_MEMORY_ALLOCATION = local.workflow_memory_allocation
    AIRFLOW_DB_HOST = aws_rds_cluster.airflow.endpoint
    AIRFLOW_DB_PORT = aws_rds_cluster.airflow.port
    AIRFLOW_DB_USERNAME = aws_rds_cluster.airflow.master_username
    AIRFLOW_DB_PASSWORD = aws_rds_cluster.airflow.master_password
  }
}

resource "helm_release" "airflow_community" {
  depends_on = [
    time_sleep.wait_for_cluster,
    aws_rds_cluster_instance.serverless
  ]

  name = "${local.project_name}-airflow-community"
  namespace = local.airflow_namespace
  chart = "https://github.com/airflow-helm/charts/releases/download/airflow-8.7.1/airflow-8.7.1.tgz"
  create_namespace = true

  values = [
    "${templatefile("values_templates/airflow.yaml", local.airflow_values)}"
  ]
}

resource "random_id" "fernet_key" {
  byte_length = 32
}

resource "random_password" "web_server_secret_key" {
  length = 32
  special = true
}

resource "random_password" "airflow_db_password" {
  length = 8
  special = false
}

resource "aws_rds_cluster" "airflow" {
  cluster_identifier      = "${local.project_name}-airflow-community"
  engine                  = "aurora-postgresql"
  engine_mode             = "provisioned"
  engine_version          = "13.6"
  database_name           = "airflow"
  master_username         = "master"
  master_password         = random_password.airflow_db_password.result
  skip_final_snapshot     = true
  apply_immediately       = true
  availability_zones      = local.azs
  db_subnet_group_name    = aws_db_subnet_group.default.name

  serverlessv2_scaling_configuration {
    max_capacity = 1.0
    min_capacity = 0.5
  }
}

resource "aws_rds_cluster_instance" "serverless" {
  cluster_identifier   = aws_rds_cluster.airflow.id
  instance_class       = "db.serverless"
  engine               = aws_rds_cluster.airflow.engine
  engine_version       = aws_rds_cluster.airflow.engine_version
  db_subnet_group_name = aws_db_subnet_group.default.name
}

data "kubernetes_service" "airflow" {
  depends_on = [
    helm_release.airflow_community
  ]
  metadata {
    name = "devops-masters-project-airflow-community-web"
    namespace = local.airflow_namespace
  }
}

output "airflow_url" {
  value = "http://${data.kubernetes_service.airflow.status.0.load_balancer.0.ingress.0.hostname}"
}