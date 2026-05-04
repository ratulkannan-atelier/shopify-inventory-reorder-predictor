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
