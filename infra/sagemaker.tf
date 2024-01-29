# IAM role for pods
#data "aws_iam_policy_document" "sm_trust" {
#  statement {
#    actions = ["sts:AssumeRole"]
#    effect = "Allow"
#    principals {
#        type = "Service"
#        identifiers = ["sagemaker.amazonaws.com"]
#    }
#  }
#}
#
#resource "aws_iam_role" "sm" {
#    name = "sm-workflow"
#    assume_role_policy = data.aws_iam_policy_document.sm_trust.json
#}
#
#data "aws_iam_policy_document" "sm_policy" {
#  statement {
#    actions = ["kms:*"]
#
#    resources = ["*"]
#  }
#
#  statement {
#    actions = ["s3:*"]
#
#    resources = ["*"]
#  }
#}
#
#resource "aws_iam_role_policy" "sm_policy" {
#  name = "sm-policy"
#  role = aws_iam_role.sm.id
#  policy = data.aws_iam_policy_document.sm_policy.json
#}
#
#resource "aws_iam_role_policy_attachment" "sm_policy_attach" {
#  role = aws_iam_role.sm.name
#  policy_arn = "arn:aws:iam::aws:policy/AmazonSageMakerFullAccess"
#}
