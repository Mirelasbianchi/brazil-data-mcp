variable "project" {
  description = "Name prefix for every resource"
  type        = string
  default     = "brazil-data-mcp"
}

variable "region" {
  type    = string
  default = "us-east-1"
}

variable "github_repository" {
  description = "owner/repo allowed to push images through GitHub Actions OIDC"
  type        = string
  default     = "Mirelasbianchi/brazil-data-mcp"
}

variable "create_github_oidc_provider" {
  description = "Set to false if the account already has the token.actions.githubusercontent.com provider"
  type        = bool
  default     = true
}

variable "create_service" {
  description = "Create the App Runner service. Apply with false first, push an image, then true."
  type        = bool
  default     = true
}
