# The lab's cloud resources — what should exist in "AWS" (Floci).
#
# These mirror what the real app uses: a bucket for original files,
# a registry for the backend image, and stored settings.

locals {
  # One prefix for every name, so all lab resources are easy to spot.
  name = "awm-lab"
}

# ---------- File storage ----------

resource "aws_s3_bucket" "files" {
  bucket = "${local.name}-files"

  tags = {
    Purpose = "original-files"
  }
}

# ---------- Container registry ----------

resource "aws_ecr_repository" "backend" {
  name                 = "${local.name}/backend"
  image_tag_mutability = "MUTABLE"
}

# ---------- Settings, stored where the app could read them ----------

resource "aws_ssm_parameter" "files_bucket" {
  name  = "/${local.name}/files-bucket"
  type  = "String"
  value = aws_s3_bucket.files.bucket
}

resource "aws_ssm_parameter" "backend_image_repo" {
  name  = "/${local.name}/backend-image-repo"
  type  = "String"
  value = aws_ecr_repository.backend.repository_url
}