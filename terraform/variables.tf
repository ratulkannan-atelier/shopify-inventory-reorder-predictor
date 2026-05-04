variable "aws_region" {
  description = "AWS region for all resources"
  type        = string
  default     = "us-east-1"
}

variable "app_name" {
  description = "Application name used as a prefix for resources"
  type        = string
  default     = "foursight"
}

variable "db_username" {
  description = "Master username for the RDS Postgres instance"
  type        = string
  default     = "reorder_user"
}

variable "db_password" {
  description = "Master password for the RDS Postgres instance"
  type        = string
  sensitive   = true
}

variable "shopify_api_key" {
  description = "Shopify Partner app API key"
  type        = string
  sensitive   = true
}

variable "shopify_api_secret" {
  description = "Shopify Partner app API secret"
  type        = string
  sensitive   = true
}

variable "shopify_app_url" {
  description = "Public base URL of the deployed app (used for OAuth redirect)"
  type        = string
}

variable "shopify_api_scopes" {
  description = "Comma-separated Shopify Admin API scopes requested at install"
  type        = string
  default     = "read_orders,read_products,read_inventory"
}
