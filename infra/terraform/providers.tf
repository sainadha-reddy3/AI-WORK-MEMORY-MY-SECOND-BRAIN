# Which plugins Terraform needs, and how to reach "AWS".
#
# Here "AWS" is Floci on localhost:4566. To use real AWS instead, you'd
# remove the endpoints block and the fake credentials — the resources
# in main.tf would stay exactly the same.

terraform {
  required_version = ">= 1.9.0"

  required_providers {
    aws = {
      source  = "hashicorp/aws"
      version = "~> 6.0"
    }
  }
}

provider "aws" {
  region = "us-east-1"

  # Floci accepts any credentials. These are not real keys.
  access_key = "test"
  secret_key = "test"

  # Real AWS would check these; Floci doesn't need them checked.
  skip_credentials_validation = true
  skip_metadata_api_check     = true
  skip_requesting_account_id  = true

  # Address buckets as http://host/bucket — what local emulators expect.
  s3_use_path_style = true

  # Send every service we use to Floci instead of real AWS.
  endpoints {
    s3  = "http://localhost:4566"
    ecr = "http://localhost:4566"
    ssm = "http://localhost:4566"
  }

  # Labels added to every resource Terraform creates.
  default_tags {
    tags = {
      Project   = "ai-work-memory"
      ManagedBy = "terraform"
      Env       = "lab"
    }
  }
}