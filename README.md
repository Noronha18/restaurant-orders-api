# Restaurant Orders API

API REST para o ciclo de vida dos pedidos de um restaurante: cardápio, criação do pedido com preço congelado, **máquina de estados** do preparo à entrega e confirmação de pagamento por **webhook assinado e idempotente**.

O foco não é o CRUD, e sim manter o pedido consistente quando várias partes mexem nele: o gateway de pagamento, a cozinha e o balcão.

---

## Destaques

- **Máquina de estados explícita:** as transições válidas ficam num único lugar ([`app/order_status.py`](app/order_status.py)). Qualquer outra retorna `400`, inclusive voltar de PREPARANDO para CRIADO.
- **"Pago" só pelo gateway:** a API operacional não consegue marcar um pedido como PAGO. Isso só acontece pelo webhook de pagamento.
- **Webhook assinado (HMAC-SHA256):** o gateway assina o corpo bruto com um segredo compartilhado. Sem assinatura válida a resposta é `401`, e a comparação é feita em tempo constante.
- **Idempotência por transação:** a mesma notificação reenviada responde `200` sem efeito colateral. Uma transação não paga dois pedidos (`UNIQUE` no banco), e um pagamento atrasado não reabre um pedido cancelado nem faz regredir um pedido em preparo (`409`).
- **Preço congelado:** cada item guarda o preço do momento da compra, então mudar o cardápio não altera pedidos antigos. O total é calculado a partir desses itens.
- **Dinheiro em `Numeric(10,2)` e `Decimal`**, nunca `float`.
- **Fila da cozinha (KDS):** `GET /pedidos/?status=PAGO` lista o que deve ser preparado, em ordem de chegada.

---

## Fluxo do pedido

```
                 webhook aprovado
      CRIADO ─────────────────────► PAGO ──► PREPARANDO ──► PRONTO ──► ENTREGUE
        │                            │
        └──────► CANCELADO ◄─────────┘
```

| De | Para (via `PATCH /pedidos/{id}`) |
|---|---|
| CRIADO | CANCELADO |
| PAGO | PREPARANDO, CANCELADO |
| PREPARANDO | PRONTO |
| PRONTO | ENTREGUE |
| ENTREGUE / CANCELADO | estados finais |

CRIADO → PAGO só ocorre via `POST /webhooks/pagamento`.

---

## Endpoints

| Método | Rota | Descrição |
|---|---|---|
| `GET` | `/produtos/?categoria=` | Lista o cardápio (filtro opcional por categoria) |
| `GET` | `/produtos/{id}` | Detalha um produto |
| `POST` | `/produtos/` | Cadastra um produto |
| `PATCH` | `/produtos/{id}` | Edita nome, descrição, preço ou categoria |
| `POST` | `/pedidos/` | Cria o pedido com os itens e o preço atual de cada um |
| `GET` | `/pedidos/?status=` | Lista pedidos (com `status=PAGO`, vira a fila da cozinha) |
| `GET` | `/pedidos/{id}` | Detalha o pedido, com itens, subtotais e total |
| `PATCH` | `/pedidos/{id}` | Avança o status pela máquina de estados |
| `POST` | `/webhooks/pagamento` | Confirmação de pagamento do gateway (assinada) |
| `GET` | `/health` | Health check |

A documentação interativa (Swagger) fica em `http://localhost:8000/docs`.

### Assinando o webhook

O gateway envia o cabeçalho `X-Webhook-Signature` com o HMAC-SHA256 (hex) do corpo bruto:

```bash
BODY='{"pedido_id":1,"status_transacao":"aprovado","id_transacao_gateway":"tx_123"}'
SIG=$(printf '%s' "$BODY" | openssl dgst -sha256 -hmac "$WEBHOOK_SECRET" | awk '{print $2}')

curl -X POST http://localhost:8000/webhooks/pagamento \
  -H "Content-Type: application/json" -H "X-Webhook-Signature: $SIG" -d "$BODY"
```

| Situação | Resposta |
|---|---|
| Assinatura ausente ou inválida | `401` |
| `aprovado` e pedido em CRIADO | `200`, pedido vai para PAGO |
| Mesma transação reenviada | `200`, sem alterações |
| `recusado` | `200`, pedido inalterado |
| Pedido já pago, cancelado ou em andamento, ou transação usada em outro pedido | `409` |

---

## Stack

| Camada | Tecnologia |
|---|---|
| API | Python 3.12 · FastAPI · Pydantic v2 · pydantic-settings |
| Banco | PostgreSQL 16 · SQLAlchemy 2 · psycopg 3 |
| Infra | Docker · Docker Compose · uv |
| Testes | pytest · FastAPI TestClient (SQLite em memória) |

---

## Estrutura

```
app/
├── main.py              # App FastAPI e routers
├── config.py            # Configuração por variáveis de ambiente
├── database.py          # Engine e sessão
├── models.py            # Produto, Pedido, ItemPedido
├── schemas.py           # Contratos de entrada e saída (Pydantic)
├── order_status.py      # Máquina de estados do pedido
├── security.py          # Assinatura HMAC do webhook
├── routers/             # produtos, pedidos, webhooks
└── scripts/seed.py      # Cardápio de exemplo
tests/                   # Fluxo completo, FSM, webhook e cardápio
init_db.py               # Cria as tabelas
Dockerfile · docker-compose.yml
```

---

## Como rodar

### Com Docker (recomendado)

```bash
git clone https://github.com/Noronha18/restaurant-orders-api.git
cd restaurant-orders-api
echo "WEBHOOK_SECRET=$(openssl rand -hex 32)" > .env
docker compose up --build
```

A API sobe em `http://localhost:8000`, já com as tabelas criadas. Para carregar o cardápio de exemplo:

```bash
docker compose exec api python -m app.scripts.seed
```

### Localmente

Requisitos: Python 3.12+, [uv](https://docs.astral.sh/uv/) e PostgreSQL.

```bash
uv sync
cp .env.example .env              # ajuste DATABASE_URL e WEBHOOK_SECRET
uv run python init_db.py
uv run python -m app.scripts.seed # opcional
uv run uvicorn app.main:app --reload
```

### Variáveis de ambiente

| Variável | Descrição |
|---|---|
| `DATABASE_URL` | Conexão PostgreSQL (`postgresql+psycopg://usuario:senha@host:5432/banco`) |
| `WEBHOOK_SECRET` | **Obrigatória.** Segredo compartilhado com o gateway para assinar os webhooks |

---

## Testes

```bash
uv run pytest
```

São 11 testes de integração que cobrem o ciclo completo do pedido, as transições bloqueadas, a impossibilidade de marcar PAGO pelo `PATCH`, o webhook sem assinatura, a idempotência, a transação reutilizada, o pagamento de pedido cancelado ou em preparo e o preço congelado após a edição do cardápio.

---

## Próximos passos

- Autenticação e papéis (balcão, cozinha, admin) nas rotas operacionais
- Migrações com Alembic
- Histórico de transições do pedido (auditoria)

---

## Autor

**Emmanuel Noronha**, desenvolvedor Full-Stack.
