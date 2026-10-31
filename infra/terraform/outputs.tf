# What Terraform prints after `terraform apply`, and what other tools
# can read with `terraform output`.

output "files_bucket" {
  description = "S3 bucket for original files"
  value       = aws_s3_bucket.files.bucket
}

output "backend_image_repo_url" {
  description = "ECR repository for the backend image"
  value       = aws_ecr_repository.backend.repository_url
}

output "ssm_parameter_names" {
  description = "Settings stored in SSM Parameter Store"
  value = [
    aws_ssm_parameter.files_bucket.name,
    aws_ssm_parameter.backend_image_repo.name,
  ]
}