resource "aws_ecr_repository" "server" {
  name                 = var.project
  image_tag_mutability = "MUTABLE"
  force_delete         = true
  image_scanning_configuration {
    scan_on_push = true
  }
}

resource "aws_ecr_lifecycle_policy" "server" {
  repository = aws_ecr_repository.server.name
  policy = jsonencode({
    rules = [{
      rulePriority = 1
      description  = "Keep the last 10 images"
      selection    = { tagStatus = "any", countType = "imageCountMoreThan", countNumber = 10 }
      action       = { type = "expire" }
    }]
  })
}

# Lets App Runner pull from the private ECR repository
resource "aws_iam_role" "apprunner_ecr" {
  name = "${var.project}-apprunner-ecr"
  assume_role_policy = jsonencode({
    Version = "2012-10-17"
    Statement = [{
      Effect    = "Allow"
      Action    = "sts:AssumeRole"
      Principal = { Service = "build.apprunner.amazonaws.com" }
    }]
  })
}

resource "aws_iam_role_policy_attachment" "apprunner_ecr" {
  role       = aws_iam_role.apprunner_ecr.name
  policy_arn = "arn:aws:iam::aws:policy/service-role/AWSAppRunnerServicePolicyForECRAccess"
}

resource "aws_apprunner_auto_scaling_configuration_version" "small" {
  auto_scaling_configuration_name = "${var.project}-small"
  min_size                        = 1
  max_size                        = 2
  max_concurrency                 = 50
}

# App Runner gives an HTTPS URL out of the box and redeploys when :latest is pushed to ECR.
resource "aws_apprunner_service" "server" {
  count        = var.create_service ? 1 : 0
  service_name = var.project

  source_configuration {
    auto_deployments_enabled = true
    authentication_configuration {
      access_role_arn = aws_iam_role.apprunner_ecr.arn
    }
    image_repository {
      image_identifier      = "${aws_ecr_repository.server.repository_url}:latest"
      image_repository_type = "ECR"
      image_configuration {
        port = "8000"
      }
    }
  }

  instance_configuration {
    cpu    = "256"
    memory = "512"
  }

  health_check_configuration {
    protocol = "HTTP"
    path     = "/health"
  }

  auto_scaling_configuration_arn = aws_apprunner_auto_scaling_configuration_version.small.arn

  depends_on = [aws_iam_role_policy_attachment.apprunner_ecr]
}
