output "cluster_name" {
  description = "Nome do cluster EKS"
  value       = aws_eks_cluster.main.name
}

output "cluster_endpoint" {
  description = "Endpoint HTTPS do cluster EKS"
  value       = aws_eks_cluster.main.endpoint
}

output "cluster_ca_certificate" {
  description = "Certificado CA do cluster EKS (base64)"
  value       = aws_eks_cluster.main.certificate_authority[0].data
  sensitive   = true
}

output "oidc_provider_arn" {
  description = "ARN do OIDC provider do EKS (usado para IRSA)"
  value       = aws_iam_openid_connect_provider.eks.arn
}

output "oidc_provider_url" {
  description = "URL do OIDC provider do EKS (usado para IRSA)"
  value       = aws_iam_openid_connect_provider.eks.url
}

output "cluster_version" {
  description = "Versao do Kubernetes no cluster"
  value       = aws_eks_cluster.main.version
}
