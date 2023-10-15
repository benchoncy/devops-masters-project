locals {
  argo_namespace = "argo"
  argo_values = {
    ARTIFACTS_BUCKET_NAME = aws_s3_bucket.metaflow_store.bucket
    ARTIFACTS_KEY_FORMAT = "argo-artifacts/{{workflow.creationTimestamp.Y}}/{{workflow.creationTimestamp.m}}/{{workflow.creationTimestamp.d}}/{{workflow.name}}/{{pod.name}}"
    AWS_REGION = var.aws_region
  }
}

# Argo Workflows Setup
resource "helm_release" "argo_metaflow" {
  depends_on = [
    time_sleep.wait_for_cluster
  ]

  name = "${local.project_name}-argo-metaflow"
  namespace = local.argo_namespace
  repository   = "https://argoproj.github.io/argo-helm"
  chart        = "argo-workflows"
  version      = "0.32.0"
  create_namespace = true
  force_update = true

  values = [
    "${templatefile("values_templates/argo.yaml", local.argo_values)}"
  ]
}
