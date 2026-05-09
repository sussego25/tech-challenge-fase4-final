output "vpc_id" {
  description = "ID of the VPC"
  value       = aws_vpc.main.id
}

output "vpc_cidr_block" {
  description = "CIDR block of the VPC"
  value       = aws_vpc.main.cidr_block
}

output "public_subnet_ids" {
  description = "IDs of the public subnets"
  value       = aws_subnet.public[*].id
}

output "private_subnet_ids" {
  description = "IDs of the private subnets"
  value       = aws_subnet.private[*].id
}

output "private_subnet_cidrs" {
  description = "CIDR blocks of the private subnets (for MSK allowed_cidr_blocks)"
  value       = aws_subnet.private[*].cidr_block
}

output "nat_gateway_ips" {
  description = "Elastic IPs allocated to NAT Gateway(s)"
  value       = aws_eip.nat[*].public_ip
}

output "eks_nodes_security_group_id" {
  description = "ID of the security group for EKS worker nodes"
  value       = aws_security_group.eks_nodes.id
}
