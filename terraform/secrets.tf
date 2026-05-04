resource "aws_secretsmanager_secret" "db" {
  name                    = "${var.app_name}/db"
  description             = "Database credentials for the 4Sight RDS instance"
  recovery_window_in_days = 0

  tags = {
    Name = "${var.app_name}-db-secret"
  }
}

resource "aws_secretsmanager_secret_version" "db" {
  secret_id = aws_secretsmanager_secret.db.id

  secret_string = jsonencode({
    username = var.db_username
    password = var.db_password
    host     = aws_db_instance.main.address
    port     = "5432"
    dbname   = "reorder_predictor"
  })
}

resource "aws_secretsmanager_secret" "shopify" {
  name                    = "${var.app_name}/shopify"
  description             = "Shopify API credentials for the 4Sight app"
  recovery_window_in_days = 0

  tags = {
    Name = "${var.app_name}-shopify-secret"
  }
}

resource "aws_secretsmanager_secret_version" "shopify" {
  secret_id = aws_secretsmanager_secret.shopify.id

  secret_string = jsonencode({
    SHOPIFY_API_KEY    = var.shopify_api_key
    SHOPIFY_API_SECRET = var.shopify_api_secret
    SHOPIFY_APP_URL    = var.shopify_app_url
    SHOPIFY_API_SCOPES = var.shopify_api_scopes
  })
}
