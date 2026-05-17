resource "aws_cloudwatch_event_rule" "fetcher_daily" {
  name                = "${var.app_name}-fetcher-daily"
  description         = "Triggers the 4Sight fetcher Lambda on a daily schedule"
  schedule_expression = var.fetcher_schedule_expression

  tags = {
    Name = "${var.app_name}-fetcher-daily"
  }
}

resource "aws_cloudwatch_event_target" "fetcher_daily" {
  rule      = aws_cloudwatch_event_rule.fetcher_daily.name
  target_id = "FetcherLambda"
  arn       = aws_lambda_function.fetcher.arn
}

resource "aws_lambda_permission" "allow_eventbridge" {
  statement_id  = "AllowEventBridgeInvoke"
  action        = "lambda:InvokeFunction"
  function_name = aws_lambda_function.fetcher.function_name
  principal     = "events.amazonaws.com"
  source_arn    = aws_cloudwatch_event_rule.fetcher_daily.arn
}
