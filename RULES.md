# RULES.md - Regras e Convenções do Projeto Tech-Challenge-fase-4

Este documento estabelece as regras, convenções e melhores práticas para desenvolvimento no projeto Tech-Challenge-fase-4, garantindo consistência, qualidade e colaboração eficiente.

## 1. Estrutura do Código
- **Organização**: Seguir a estrutura de pastas definida (services/, infra/, shared/, etc.). Cada serviço deve ter src/ com camadas: domain/, application/, infrastructure/, presentation/.
- **Contratos Compartilhados**: Usar shared/contracts/ para DTOs, entidades e eventos. Evitar duplicação entre serviços.
- **Infraestrutura**: IaC em infra/ com Terraform. Manter módulos reutilizáveis.

## 2. Convenções de Código
- **Linguagens**:
  - Python: Seguir PEP 8, SOLID e usar type hints obrigatórios, Black para formatação automática.
  - Convenção: snake_case para variáveis/funções, PascalCase para classes.
- **Commits**: Mensagens claras em inglês (ex.: "feat: add order validation"). Usar conventional commits.
- **Branches**: feature/nome-da-feature, bugfix/issue-id, hotfix/urgente. Merge via PR.

## 3. Desenvolvimento
- **Microserviços**: Cada serviço independente, com API Gateway para roteamento (infra/api-gateway/).
- **Mensageria**: Usar Kafka para eventos internos, SQS para externos. Documentar tópicos/filas em messaging/.
- **Banco de Dados**: DynamoDB para dados NoSQL. Evitar queries complexas; otimizar com índices.
- **Segurança**: Usar IAM roles, VPC isolada. Secrets em Kubernetes Secrets ou AWS Secrets Manager.


## 5. Pull Requests (PRs)
- **Revisão**: Pelo menos 1 aprovador. Descrever mudanças, impacto e testes.
- **Checks**: CI/CD deve passar (build, lint, tests). Não merge com conflitos.
- **Tamanho**: Pequenas mudanças preferidas; dividir grandes features.

## 6. Deploy e Operações
- **Containers**: Dockerfile em cada serviço. Usar multi-stage para otimização.
- **Kubernetes**: Deploys via Helm. ConfigMaps/Secrets para configuração.
- **Monitoramento**: Logs estruturados, métricas em CloudWatch/Prometheus.
- **Rollback**: Estratégia clara para reversões em caso de falhas.

## 7. Documentação
- **README**: Em cada serviço e na raiz. Incluir setup, API docs.
- **Docs**: Arquitetura em docs/arquitetura.md, diagramas em docs/diagramas/.
- **APIs**: Usar OpenAPI/Swagger para endpoints.

## 8. Boas Práticas Gerais
- **Versionamento**: Semântico (SemVer) para releases.
- **Dependências**: Manter atualizadas, auditar vulnerabilidades.
- **Performance**: Otimizar queries, usar cache (ex.: Redis se aplicável).
- **Acessibilidade**: Código legível, comentários em inglês.
- **Ética**: Respeitar leis de dados (LGPD/GDPR), evitar bias em LLM.

## Violações
- Código não testado ou sem lint: Rejeitado em PR.
- Mudanças sem documentação: Solicitar atualização.
- Conflitos não resolvidos: Resolver antes do merge.

Este documento é vivo; contribua com sugestões via issue/PR. Última atualização: [Data Atual].

retonro do sagemake
{
  "predictions": [
    {
      "class_id": 3,
      "label": "cloudfront",
      "confidence": 0.6794843077659607,
      "x1": 401.8503112792969,
      "y1": 318.7760925292969,
      "x2": 479.7858581542969,
      "y2": 402.1646423339844
    },
    {
      "class_id": 3,
      "label": "cloudfront",
      "confidence": 0.6294493079185486,
      "x1": 142.47381591796875,
      "y1": 344.940185546875,
      "x2": 227.85284423828125,
      "y2": 444.92303466796875
    },
    {
      "class_id": 0,
      "label": "apigateway",
      "confidence": 0.330269455909729,
      "x1": 285.68310546875,
      "y1": 0.0,
      "x2": 364.3458251953125,
      "y2": 40.727237701416016
    }
  ]
}


aws sagemaker-runtime invoke-endpoint \
    --endpoint-name tech-challenger-yolo-prod \
    --body fileb://foto_teste.jpg \
    --content-type image/jpeg \
    resultado.json