# ─────────────────────────────────────────────
# Data Sources
# ─────────────────────────────────────────────
data "aws_availability_zones" "available" {
  state = "available"

  filter {
    name   = "opt-in-status"
    values = ["opt-in-not-required"]
  }
}

locals {
  azs = slice(data.aws_availability_zones.available.names, 0, 2)

  public_subnet_cidrs  = ["10.0.1.0/24", "10.0.2.0/24"]
  private_subnet_cidrs = ["10.0.10.0/24", "10.0.20.0/24"]

  nat_count = var.enable_ha_nat ? 2 : 1

  tags = merge(var.common_tags, {
    Environment = var.environment
    Project     = var.project_name
    Terraform   = "true"
  })
}

# ─────────────────────────────────────────────
# VPC
# ─────────────────────────────────────────────
resource "aws_vpc" "main" {
  cidr_block           = var.vpc_cidr
  enable_dns_support   = true
  enable_dns_hostnames = true

  tags = merge(local.tags, {
    Name = "${var.project_name}-vpc-${var.environment}"
  })
}

# ─────────────────────────────────────────────
# Internet Gateway
# ─────────────────────────────────────────────
resource "aws_internet_gateway" "main" {
  vpc_id = aws_vpc.main.id

  tags = merge(local.tags, {
    Name = "${var.project_name}-igw-${var.environment}"
  })
}

# ─────────────────────────────────────────────
# Public Subnets
# ─────────────────────────────────────────────
resource "aws_subnet" "public" {
  count = 2

  vpc_id                  = aws_vpc.main.id
  cidr_block              = local.public_subnet_cidrs[count.index]
  availability_zone       = local.azs[count.index]
  map_public_ip_on_launch = true

  tags = merge(local.tags, {
    Name                                                           = "${var.project_name}-public-${local.azs[count.index]}-${var.environment}"
    "kubernetes.io/role/elb"                                       = "1"
    "kubernetes.io/cluster/${var.project_name}-${var.environment}" = "shared"
  })
}

# ─────────────────────────────────────────────
# Private Subnets
# ─────────────────────────────────────────────
resource "aws_subnet" "private" {
  count = 2

  vpc_id                  = aws_vpc.main.id
  cidr_block              = local.private_subnet_cidrs[count.index]
  availability_zone       = local.azs[count.index]
  map_public_ip_on_launch = false

  tags = merge(local.tags, {
    Name                                                           = "${var.project_name}-private-${local.azs[count.index]}-${var.environment}"
    "kubernetes.io/role/internal-elb"                              = "1"
    "kubernetes.io/cluster/${var.project_name}-${var.environment}" = "shared"
  })
}

# ─────────────────────────────────────────────
# NAT Gateway(s) + Elastic IP(s)
# ─────────────────────────────────────────────
resource "aws_eip" "nat" {
  count  = local.nat_count
  domain = "vpc"

  tags = merge(local.tags, {
    Name = "${var.project_name}-nat-eip-${count.index}-${var.environment}"
  })

  depends_on = [aws_internet_gateway.main]
}

resource "aws_nat_gateway" "main" {
  count = local.nat_count

  allocation_id = aws_eip.nat[count.index].id
  subnet_id     = aws_subnet.public[count.index].id

  tags = merge(local.tags, {
    Name = "${var.project_name}-nat-${count.index}-${var.environment}"
  })

  depends_on = [aws_internet_gateway.main]
}

# ─────────────────────────────────────────────
# Route Tables
# ─────────────────────────────────────────────

# Public route table (single, shared by all public subnets)
resource "aws_route_table" "public" {
  vpc_id = aws_vpc.main.id

  route {
    cidr_block = "0.0.0.0/0"
    gateway_id = aws_internet_gateway.main.id
  }

  tags = merge(local.tags, {
    Name = "${var.project_name}-public-rt-${var.environment}"
  })
}

# Private route table(s) — one per NAT when HA, otherwise shared
resource "aws_route_table" "private" {
  count  = local.nat_count
  vpc_id = aws_vpc.main.id

  route {
    cidr_block     = "0.0.0.0/0"
    nat_gateway_id = aws_nat_gateway.main[count.index].id
  }

  tags = merge(local.tags, {
    Name = "${var.project_name}-private-rt-${count.index}-${var.environment}"
  })
}

# ─────────────────────────────────────────────
# Route Table Associations
# ─────────────────────────────────────────────

# Public subnets → public route table
resource "aws_route_table_association" "public" {
  count = 2

  subnet_id      = aws_subnet.public[count.index].id
  route_table_id = aws_route_table.public.id
}

# Private subnets → private route table(s)
# When enable_ha_nat=true, each private subnet gets its own NAT via its own route table
# When enable_ha_nat=false, both private subnets share the single route table
resource "aws_route_table_association" "private" {
  count = 2

  subnet_id      = aws_subnet.private[count.index].id
  route_table_id = aws_route_table.private[var.enable_ha_nat ? count.index : 0].id
}

# ─────────────────────────────────────────────
# Security Group — EKS Nodes
# ─────────────────────────────────────────────
resource "aws_security_group" "eks_nodes" {
  name_prefix = "${var.project_name}-eks-nodes-${var.environment}-"
  description = "Security group for EKS worker nodes"
  vpc_id      = aws_vpc.main.id

  # Allow all egress (needed for SageMaker, AWS APIs, ECR, etc.)
  egress {
    description = "Allow all outbound traffic"
    from_port   = 0
    to_port     = 0
    protocol    = "-1"
    cidr_blocks = ["0.0.0.0/0"]
  }

  tags = merge(local.tags, {
    Name = "${var.project_name}-eks-nodes-sg-${var.environment}"
  })

  lifecycle {
    create_before_destroy = true
  }
}
