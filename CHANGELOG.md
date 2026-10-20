# Changelog

Formato baseado em [Keep a Changelog](https://keepachangelog.com/pt-BR/1.1.0/).
Versões seguem [SemVer](https://semver.org/lang/pt-BR/).

## [1.0.0] - 2026-10-20

### Adicionado

- Consumer Kafka (grupo `marketplace-analytics`) dos tópicos `order.paid`,
  `product.created`, `product.updated` e `product.viewed`, idempotente por
  `eventId` na tabela `processed_events`.
- Banco SQLite em `data/analytics.db` com migrations numeradas em
  `schema_migrations`: `sales`, `products`, `product_views`.
- Relatórios em pandas: série de vendas por dia, semana ou mês, ranking de
  produtos por receita e por quantidade, visualizações com taxa de conversão.
- Rotas `GET /reports/sales`, `GET /reports/sales.csv`,
  `GET /reports/top-products` e `GET /reports/views`, protegidas por JWT
  RS256 validado no JWKS do `marketplace-auth`. Vendedor consulta só o
  próprio `sellerId`; admin consulta qualquer um.
- `GET /health` com estado do SQLite e do consumer Kafka.
- Dockerfile em `python:3.13-slim` e CI com ruff e pytest.
