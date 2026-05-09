# Arquitetura do Sistema

## Visão Geral

Este documento descreve a arquitetura de microsserviços do Tech Challenger.

## Componentes Principais

### Serviços

1. **Lambda Publisher**: recebe eventos de upload no S3, cria o registro inicial no DynamoDB e publica a mensagem na fila SQS
2. **Worker Service**: consome a fila SQS no EKS, executa YOLO + LLM e grava o relatório no DynamoDB

### Mensageria

- **SQS**: fila assíncrona entre Lambda e Worker Service

## Fluxo de Dados

S3 upload -> Lambda -> SQS -> Worker Service no EKS -> YOLO -> LLM -> DynamoDB

## Infraestrutura

- **EKS**: Kubernetes gerenciado
- **DynamoDB**: persistência dos diagramas, status e relatório de análise
- **SQS**: fila de processamento assíncrono

