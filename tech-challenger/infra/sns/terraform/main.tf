resource "aws_sns_topic" "analysis_results" {
  name = "${var.project_name}-analysis-results-${var.environment}"

  tags = merge(var.common_tags, {
    Name = "${var.project_name}-analysis-results-${var.environment}"
  })
}
