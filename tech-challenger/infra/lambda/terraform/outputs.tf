output "lambda_function_name" {
  description = "Nome da funcao Lambda order-handler"
  value       = aws_lambda_function.order_handler.function_name
}

output "lambda_function_arn" {
  description = "ARN da funcao Lambda order-handler"
  value       = aws_lambda_function.order_handler.arn
}
