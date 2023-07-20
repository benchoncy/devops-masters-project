locals {
  argo_namespace = "argo"
  argo_jobs_namespace = "${local.argo_namespace}-jobs"
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
  create_namespace = true
  force_update = true

  values = [
    "${templatefile("values_templates/argo.yaml", local.argo_values)}"
  ]
}

resource "kubernetes_namespace" "jobs" {
  depends_on = [
      helm_release.argo_metaflow
  ]
  metadata {
    name = local.argo_jobs_namespace
  }
}

module "argo_events" {
  depends_on     = [
    helm_release.argo_metaflow,
    kubernetes_namespace.jobs
  ]
  source         = "git::git@github.com:outerbounds/metaflow-tools//common/terraform/argo_events?ref=v2.0.0"
  jobs_namespace = local.argo_jobs_namespace
}
