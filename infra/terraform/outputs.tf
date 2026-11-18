output "mcp_url" {
  description = "Streamable HTTP endpoint to give MCP clients"
  value       = var.create_service ? "https://${aws_apprunner_service.server[0].service_url}/mcp" : null
}

output "ecr_repository" {
  value = aws_ecr_repository.server.repository_url
}

output "github_deploy_role_arn" {
  description = "Set as the AWS_ROLE_ARN repository variable in GitHub"
  value       = aws_iam_role.github_deploy.arn
}
