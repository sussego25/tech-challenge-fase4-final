# Plan: 009 — VPC/Networking Terraform

## Objective
Provisionar VPC com subnets públicas e privadas, Internet Gateway, NAT Gateway e route tables via Terraform. Integrar ao módulo raiz para que EKS e MSK consumam os outputs automaticamente.

## Architecture Decisions
- VPC CIDR `10.0.0.0/16` — bloco grande o suficiente para expansão futura (65k IPs)
- 2 AZs (us-east-1a, us-east-1b) — mínimo para EKS e MSK; 3 AZs é overkill para dev
- 1 NAT Gateway (single AZ) — suficiente para dev/staging; variável `enable_ha_nat` para produção com 2 NATs
- Subnets públicas: `10.0.1.0/24`, `10.0.2.0/24` — para NAT Gateway e futuros Load Balancers
- Subnets privadas: `10.0.10.0/24`, `10.0.20.0/24` — para EKS nodes, MSK brokers, SageMaker
- `enable_dns_support` e `enable_dns_hostnames` habilitados — necessários para EKS e endpoints VPC
- Tags `kubernetes.io/role/internal-elb` nas subnets privadas e `kubernetes.io/role/elb` nas públicas — convenção EKS para auto-discovery de subnets pelo AWS Load Balancer Controller

## Flow
```
terraform apply (infra/terraform/)
  └─ module "networking" (novo)
       ├─ aws_vpc
       ├─ aws_internet_gateway
       ├─ aws_subnet "public" x2 (AZ a, b)
       ├─ aws_subnet "private" x2 (AZ a, b)
       ├─ aws_eip (para NAT)
       ├─ aws_nat_gateway (em subnet pública)
       ├─ aws_route_table "public" → IGW
       ├─ aws_route_table "private" → NAT
       ├─ aws_route_table_association x4
       └─ outputs → vpc_id, public_subnet_ids, private_subnet_ids, private_subnet_cidrs
```

## Module Structure
```
infra/networking/terraform/
├── main.tf        # VPC, subnets, IGW, NAT, route tables, associations
├── variables.tf   # aws_region, environment, project_name, vpc_cidr, enable_ha_nat
└── outputs.tf     # vpc_id, public_subnet_ids, private_subnet_ids, private_subnet_cidrs

infra/terraform/
├── main.tf        # adicionar module "networking" + wiring para EKS e Kafka
├── variables.tf   # adicionar vpc_cidr; deprecar eks_vpc_id, kafka_vpc_id
└── outputs.tf     # adicionar outputs de networking
```

## Implementation Steps

### Step 1 — `infra/networking/terraform/variables.tf`
- `aws_region`, `environment`, `project_name`, `common_tags` — padrão
- `vpc_cidr` (default `"10.0.0.0/16"`)
- `enable_ha_nat` (default `false`) — se true, cria 1 NAT per AZ

### Step 2 — `infra/networking/terraform/main.tf`
Recursos na ordem de dependência:
- `data "aws_availability_zones" "available"` — buscar AZs dinamicamente
- `aws_vpc "main"` — CIDR, DNS habilitado, tags
- `aws_internet_gateway "main"` — associado à VPC
- `aws_subnet "public"` (count=2) — CIDRs `10.0.1.0/24`, `10.0.2.0/24`, `map_public_ip_on_launch=true`, tags EKS `kubernetes.io/role/elb=1`
- `aws_subnet "private"` (count=2) — CIDRs `10.0.10.0/24`, `10.0.20.0/24`, tags EKS `kubernetes.io/role/internal-elb=1`
- `aws_eip "nat"` (count = `enable_ha_nat ? 2 : 1`)
- `aws_nat_gateway "main"` (count = `enable_ha_nat ? 2 : 1`) — em subnets públicas
- `aws_route_table "public"` — rota `0.0.0.0/0 → IGW`
- `aws_route_table "private"` (count = `enable_ha_nat ? 2 : 1`) — rota `0.0.0.0/0 → NAT`
- `aws_route_table_association` — associar cada subnet ao route table correto

### Step 3 — `infra/networking/terraform/outputs.tf`
- `vpc_id` — ID da VPC
- `vpc_cidr_block` — CIDR da VPC
- `public_subnet_ids` — lista de IDs das subnets públicas
- `private_subnet_ids` — lista de IDs das subnets privadas
- `private_subnet_cidrs` — lista de CIDRs das subnets privadas (para `allowed_cidr_blocks` do MSK)
- `nat_gateway_ips` — EIPs alocados para os NATs

### Step 4 — Atualizar `infra/terraform/main.tf`
- Adicionar `module "networking"` no topo (sem dependências de outros módulos)
- Alterar `module "eks"`: substituir `var.eks_vpc_id` por `module.networking.vpc_id` e `var.eks_subnet_ids` por `module.networking.private_subnet_ids`
- Alterar `module "kafka"`: substituir `var.kafka_vpc_id` por `module.networking.vpc_id`, `var.kafka_subnet_ids` por `module.networking.private_subnet_ids` e `var.kafka_allowed_cidr_blocks` por `module.networking.private_subnet_cidrs`

### Step 5 — Atualizar `infra/terraform/variables.tf`
- Adicionar `vpc_cidr` (default `"10.0.0.0/16"`)
- Adicionar `enable_ha_nat` (default `false`)
- Marcar como deprecated via description: `eks_vpc_id`, `eks_subnet_ids`, `kafka_vpc_id`, `kafka_subnet_ids`, `kafka_allowed_cidr_blocks`

### Step 6 — Atualizar `infra/terraform/outputs.tf`
- Adicionar `vpc_id`, `public_subnet_ids`, `private_subnet_ids`

## Dependencies
- Nenhum módulo depende do networking ser criado primeiro no Terraform (o count=0 protege EKS/Kafka quando desabilitados)
- EKS e Kafka passam a depender implicitamente do networking via referência de output

## Validation
```powershell
cd tech-challenger/infra/terraform
terraform init -upgrade
terraform validate
terraform plan -var="environment=dev"
```

Após apply:
```bash
aws ec2 describe-vpcs --filters "Name=tag:Project,Values=tech-challenger" --query "Vpcs[].{Id:VpcId,Cidr:CidrBlock}"
aws ec2 describe-subnets --filters "Name=vpc-id,Values=<vpc-id>" --query "Subnets[].{Id:SubnetId,Az:AvailabilityZone,Cidr:CidrBlock,Public:MapPublicIpOnLaunch}"
aws ec2 describe-nat-gateways --filter "Name=vpc-id,Values=<vpc-id>" --query "NatGateways[].{Id:NatGatewayId,State:State,SubnetId:SubnetId}"
```
