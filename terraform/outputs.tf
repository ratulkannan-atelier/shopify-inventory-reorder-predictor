output "alb_dns_name" {
  description = "Public DNS name of the application load balancer"
  value       = aws_lb.main.dns_name
}

output "ecr_repository_url" {
  description = "URI to push the app's Docker image to"
  value       = aws_ecr_repository.app.repository_url
}

output "rds_endpoint" {
  description = "Endpoint (host:port) of the RDS Postgres instance"
  value       = aws_db_instance.main.endpoint
}

output "lambda_ecr_repository_url" {
  description = "URI to push the Lambda container image to"
  value       = aws_ecr_repository.lambda.repository_url
}

output "forecast_queue_url" {
  description = "URL of the SQS queue used to trigger forecast computation"
  value       = aws_sqs_queue.forecast.url
}

output "fetcher_lambda_name" {
  description = "Name of the fetcher Lambda function"
  value       = aws_lambda_function.fetcher.function_name
}

output "worker_lambda_name" {
  description = "Name of the worker Lambda function"
  value       = aws_lambda_function.worker.function_name
}
