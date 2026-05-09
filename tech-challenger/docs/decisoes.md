# Decisões de Design

## ADR (Architecture Decision Records)

### 1. Uso de Microsserviços
**Problema**: Necessidade de escalabilidade e independência de serviços
**Decisão**: Arquitetura de microsserviços
**Consequências**: Complexidade aumentada, mas maior flexibilidade

### 2. Mensageria Assíncrona com SQS
**Problema**: Processamento de imagens e análise LLM pode ser demorado
**Decisão**: Usar SQS como único canal assíncrono entre Lambda e Worker Service
**Consequências**: Fluxo mais simples, menor custo operacional e menos infraestrutura

### 3. Deploy em Kubernetes
**Problema**: Necessidade de orquestração eficiente
**Decisão**: Usar EKS (Elastic Kubernetes Service)
**Consequências**: DevOps mais complexo, deployment mais robusto

[Adicione mais ADRs conforme necessário]
