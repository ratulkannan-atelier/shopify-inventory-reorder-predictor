resource "aws_sqs_queue" "forecast_dlq" {
  name                      = "${var.app_name}-forecast-dlq"
  message_retention_seconds = 1209600 # 14 days

  tags = {
    Name = "${var.app_name}-forecast-dlq"
  }
}

resource "aws_sqs_queue" "forecast" {
  name                       = "${var.app_name}-forecast-queue"
  visibility_timeout_seconds = 360 # 6× the worker Lambda timeout (60s)

  redrive_policy = jsonencode({
    deadLetterTargetArn = aws_sqs_queue.forecast_dlq.arn
    maxReceiveCount     = 3
  })

  tags = {
    Name = "${var.app_name}-forecast-queue"
  }
}

resource "aws_sqs_queue_redrive_allow_policy" "forecast_dlq" {
  queue_url = aws_sqs_queue.forecast_dlq.url

  redrive_allow_policy = jsonencode({
    redrivePermission = "byQueue"
    sourceQueueArns   = [aws_sqs_queue.forecast.arn]
  })
}
