# Shared EKS Cluster resources for all tools.

# Create EKS cluster
resource "aws_eks_cluster" "main" {
  depends_on = [ 
    aws_iam_role_policy_attachment.node_role_aws_managed_policy_attachment,
    aws_iam_role_policy_attachment.cluster_role_aws_managed_policy_attachment
  ]

  name = local.project_name
  role_arn = aws_iam_role.cluster_role.arn

  version = "1.27"

  vpc_config {
    subnet_ids = module.vpc.private_subnets #module.vpc.public_subnets
  }
}

# Set EKS cluster addons
resource "aws_eks_addon" "coredns" {
  depends_on = [
    aws_eks_cluster.main,
    aws_eks_node_group.main
  ]

  cluster_name = aws_eks_cluster.main.name
  addon_name   = "coredns"
}

resource "aws_eks_addon" "kube_proxy" {
  cluster_name = aws_eks_cluster.main.name
  addon_name   = "kube-proxy"
}

resource "aws_eks_addon" "vpc_cni" {
  cluster_name = aws_eks_cluster.main.name
  addon_name   = "vpc-cni"
}

# Create EKS node group
resource "aws_eks_node_group" "main" {
  depends_on = [
    aws_iam_role_policy_attachment.node_role_aws_managed_policy_attachment,
    aws_iam_role_policy_attachment.cluster_role_aws_managed_policy_attachment
  ]

  cluster_name    = aws_eks_cluster.main.name
  node_group_name = "${local.project_name}-node-group"
  node_role_arn   = aws_iam_role.node_role.arn

  subnet_ids = module.vpc.private_subnets

  ami_type = "AL2_x86_64"
  capacity_type = "ON_DEMAND"
  disk_size = 20
  instance_types = ["t3.medium"]

  scaling_config {
    desired_size = 2
    max_size     = 2
    min_size     = 2
  }

  update_config {
    max_unavailable = 1
  }


  lifecycle {
    
  }
}

# Create IAM role for EKS cluster
resource "aws_iam_role" "cluster_role" {
  name = "${local.project_name}-cluster-role"

  assume_role_policy = data.aws_iam_policy_document.cluster_assume_role_policy.json
}

data "aws_iam_policy_document" "cluster_assume_role_policy" {
  statement {
    actions = ["sts:AssumeRole"]

    principals {
      type        = "Service"
      identifiers = ["eks.amazonaws.com"]
    }
  }
}

# Add IAM policies to the EKS cluster role
resource "aws_iam_role_policy_attachment" "cluster_role_aws_managed_policy_attachment" {
  for_each = toset([
    "AmazonEKSClusterPolicy",
    "AmazonEKSVPCResourceController"
  ])

  role       = aws_iam_role.cluster_role.name
  policy_arn = "arn:aws:iam::aws:policy/${each.value}"
}

# Create IAM role for EKS node group
resource "aws_iam_role" "node_role" {
  name = "${local.project_name}-node-role"

  assume_role_policy = data.aws_iam_policy_document.node_assume_role_policy.json
}

data "aws_iam_policy_document" "node_assume_role_policy" {
  statement {
    actions = ["sts:AssumeRole"]

    principals {
      type        = "Service"
      identifiers = ["ec2.amazonaws.com"]
    }
  }
}

# Add IAM policies to the EKS node group role
resource "aws_iam_role_policy_attachment" "node_role_aws_managed_policy_attachment" {
  for_each = toset([
    "AmazonEKSWorkerNodePolicy",
    "AmazonEKS_CNI_Policy",
    "AmazonEC2ContainerRegistryReadOnly",
  ])

  role       = aws_iam_role.node_role.name
  policy_arn = "arn:aws:iam::aws:policy/${each.value}"
}

resource "null_resource" "kubectl" {
  depends_on = [ aws_eks_cluster.main ]

  provisioner "local-exec" {
    command = "aws eks --region ${var.aws_region} update-kubeconfig --name ${aws_eks_cluster.main.name}"
  }

  lifecycle {
    replace_triggered_by = [ aws_eks_cluster.main ]
  }
}

# Wait a little bit for the cluster to be ready
resource "time_sleep" "wait_for_cluster" {
  depends_on = [
    aws_eks_cluster.main,
    aws_eks_node_group.main,
    null_resource.kubectl,
    aws_eks_addon.coredns,
    aws_eks_addon.kube_proxy,
    aws_eks_addon.vpc_cni
  ]

  create_duration = "15s"
}

data "tls_certificate" "eks" {
  url = aws_eks_cluster.main.identity[0].oidc[0].issuer
}

# Create OIDC provider
resource "aws_iam_openid_connect_provider" "eks" {
  url             = aws_eks_cluster.main.identity[0].oidc[0].issuer
  client_id_list  = ["sts.amazonaws.com"]
  thumbprint_list = [data.tls_certificate.eks.certificates[0].sha1_fingerprint]
}
