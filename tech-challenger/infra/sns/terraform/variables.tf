variable "environment" {
  description = "Environment name"
  type        = string
}

variable "project_name" {
  description = "Project name"
  type        = string
  default     = "tech-challenger"
}

variable "common_tags" {
  description = "Common tags"
  type        = map(string)
  default = {
    Terraform = "true"
    Project   = "tech-challenger"
  }
}
