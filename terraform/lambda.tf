# NOTE: Bootstrap order — create ECR repo first (terraform apply -target=aws_ecr_repository.lambda),
# build and push the image, then run a full terraform apply for the Lambda functions.

resource "aws_ecr_repository" "lambda" {
  name         = "${var.app_name}-lambda"
  force_delete = true

  image_scanning_configuration {
    scan_on_push = true
  }

  tags = {
    Name = "${var.app_name}-lambda"
  }
}

resource "aws_ecr_lifecycle_policy" "lambda" {
  repository = aws_ecr_repository.lambda.name

  policy = jsonencode({
    rules = [
      {
        rulePriority = 1
        description  = "Keep only the last 3 untagged images"
        selection = {
          tagStatus   = "untagged"
          countType   = "imageCountMoreThan"
          countNumber = 3
        }
        action = {
          type = "expire"
        }
      }
    ]
  })
}

resource "aws_cloudwatch_log_group" "fetcher_lambda" {
  name              = "/aws/lambda/${var.app_name}-fetcher"
  retention_in_days = 7

  tags = {
    Name = "/aws/lambda/${var.app_name}-fetcher"
  }
}

resource "aws_cloudwatch_log_group" "worker_lambda" {
  name              = "/aws/lambda/${var.app_name}-worker"
  retention_in_days = 7

  tags = {
    Name = "/aws/lambda/${var.app_name}-worker"
  }
}

resource "aws_lambda_function" "fetcher" {
  function_name = "${var.app_name}-fetcher"
  role          = aws_iam_role.fetcher_lambda.arn
  package_type  = "Image"
  image_uri     = "${aws_ecr_repository.lambda.repository_url}:latest"
  timeout       = 900
  memory_size   = 512

  image_config {
    command = ["app.lambdas.fetcher_handler.lambda_handler"]
  }

  vpc_config {
    subnet_ids         = [aws_subnet.private_a.id, aws_subnet.private_b.id]
    security_group_ids = [aws_security_group.ecs.id]
  }

  environment {
    variables = {
      POSTGRES_HOST      = aws_db_instance.main.address
      POSTGRES_PORT      = "5432"
      POSTGRES_DB        = "reorder_predictor"
      DB_SECRET_ARN      = aws_secretsmanager_secret.db.arn
      FORECAST_QUEUE_URL = aws_sqs_queue.forecast.url
    }
  }

  depends_on = [
    aws_nat_gateway.main,
    aws_route_table_association.private_a,
    aws_route_table_association.private_b,
    aws_cloudwatch_log_group.fetcher_lambda,
  ]

  tags = {
    Name = "${var.app_name}-fetcher"
  }
}

resource "aws_lambda_function" "worker" {
  function_name = "${var.app_name}-worker"
  role          = aws_iam_role.worker_lambda.arn
  package_type  = "Image"
  image_uri     = "${aws_ecr_repository.lambda.repository_url}:latest"
  timeout       = 60
  memory_size   = 512

  image_config {
    command = ["app.lambdas.worker_handler.lambda_handler"]
  }

  vpc_config {
    subnet_ids         = [aws_subnet.private_a.id, aws_subnet.private_b.id]
    security_group_ids = [aws_security_group.ecs.id]
  }

  environment {
    variables = {
      POSTGRES_HOST    = aws_db_instance.main.address
      POSTGRES_PORT    = "5432"
      POSTGRES_DB      = "reorder_predictor"
      DB_SECRET_ARN    = aws_secretsmanager_secret.db.arn
      SES_SENDER_EMAIL = var.ses_sender_email
      APP_BASE_URL     = var.shopify_app_url
    }
  }

  depends_on = [
    aws_nat_gateway.main,
    aws_route_table_association.private_a,
    aws_route_table_association.private_b,
    aws_cloudwatch_log_group.worker_lambda,
  ]

  tags = {
    Name = "${var.app_name}-worker"
  }
}

resource "aws_lambda_event_source_mapping" "worker" {
  event_source_arn        = aws_sqs_queue.forecast.arn
  function_name           = aws_lambda_function.worker.arn
  batch_size              = 1
  function_response_types = ["ReportBatchItemFailures"]
}

resource "aws_cloudwatch_metric_alarm" "forecast_dlq_not_empty" {
  alarm_name          = "${var.app_name}-forecast-dlq-not-empty"
  alarm_description   = "Forecast DLQ has at least one message — worker failures need investigation"
  namespace           = "AWS/SQS"
  metric_name         = "ApproximateNumberOfMessagesVisible"
  statistic           = "Maximum"
  period              = 60
  evaluation_periods  = 1
  threshold           = 1
  comparison_operator = "GreaterThanOrEqualToThreshold"
  treat_missing_data  = "notBreaching"

  dimensions = {
    QueueName = aws_sqs_queue.forecast_dlq.name
  }

  alarm_actions = []

  tags = {
    Name = "${var.app_name}-forecast-dlq-not-empty"
  }
}

resource "aws_cloudwatch_metric_alarm" "fetcher_lambda_errors" {
  alarm_name          = "${var.app_name}-fetcher-lambda-errors"
  alarm_description   = "Fetcher Lambda recorded at least one invocation error — investigate function logs"
  namespace           = "AWS/Lambda"
  metric_name         = "Errors"
  statistic           = "Sum"
  period              = 60
  evaluation_periods  = 1
  threshold           = 1
  comparison_operator = "GreaterThanOrEqualToThreshold"
  treat_missing_data  = "notBreaching"

  dimensions = {
    FunctionName = aws_lambda_function.fetcher.function_name
  }

  alarm_actions = []

  tags = {
    Name = "${var.app_name}-fetcher-lambda-errors"
  }
}

resource "aws_cloudwatch_metric_alarm" "worker_lambda_errors" {
  alarm_name          = "${var.app_name}-worker-lambda-errors"
  alarm_description   = "Worker Lambda recorded at least one invocation error — investigate function logs"
  namespace           = "AWS/Lambda"
  metric_name         = "Errors"
  statistic           = "Sum"
  period              = 60
  evaluation_periods  = 1
  threshold           = 1
  comparison_operator = "GreaterThanOrEqualToThreshold"
  treat_missing_data  = "notBreaching"

  dimensions = {
    FunctionName = aws_lambda_function.worker.function_name
  }

  alarm_actions = []

  tags = {
    Name = "${var.app_name}-worker-lambda-errors"
  }
}
