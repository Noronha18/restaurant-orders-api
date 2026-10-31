import json
import os

# Configuração de teste antes de importar a aplicação
os.environ["DATABASE_URL"] = "sqlite://"
os.environ["WEBHOOK_SECRET"] = "segredo-de-teste"

import pytest  # noqa: E402
from fastapi.testclient import TestClient  # noqa: E402
from sqlalchemy import create_engine  # noqa: E402
from sqlalchemy.orm import sessionmaker  # noqa: E402
from sqlalchemy.pool import StaticPool  # noqa: E402

from app.database import Base, get_db  # noqa: E402
from app.main import app  # noqa: E402
from app.security import SIGNATURE_HEADER, assinar  # noqa: E402

engine = create_engine("sqlite://", connect_args={"check_same_thread": False}, poolclass=StaticPool)
TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)


@pytest.fixture
def db_session():
    Base.metadata.create_all(bind=engine)
    db = TestingSessionLocal()
    try:
        yield db
    finally:
        db.close()
        Base.metadata.drop_all(bind=engine)


@pytest.fixture
def client(db_session):
    def override_get_db():
        yield db_session

    app.dependency_overrides[get_db] = override_get_db
    with TestClient(app) as c:
        yield c
    app.dependency_overrides.clear()


@pytest.fixture
def enviar_webhook(client):
    """Envia o webhook de pagamento assinado como o gateway faria."""

    def _enviar(payload: dict, assinatura: str | None = None):
        body = json.dumps(payload).encode()
        headers = {"Content-Type": "application/json", SIGNATURE_HEADER: assinatura or assinar(body)}
        return client.post("/webhooks/pagamento", content=body, headers=headers)

    return _enviar


@pytest.fixture
def pedido_criado(client):
    """Cria um produto de R$ 35,00 e um pedido com 2 unidades."""
    produto = client.post(
        "/produtos/", json={"nome": "X-Bacon", "preco": "35.00", "categoria": "Lanches"}
    ).json()
    pedido = client.post("/pedidos/", json={"itens": [{"produto_id": produto["id"], "quantidade": 2}]}).json()
    return pedido
