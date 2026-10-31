from decimal import Decimal


def _pagar(enviar_webhook, pedido_id, tx="tx_123", status="aprovado"):
    return enviar_webhook({"pedido_id": pedido_id, "status_transacao": status, "id_transacao_gateway": tx})


# --- Fluxo feliz ---

def test_ciclo_completo_do_pedido(client, enviar_webhook, pedido_criado):
    pid = pedido_criado["id"]
    assert pedido_criado["status"] == "CRIADO"
    assert Decimal(pedido_criado["total"]) == Decimal("70.00")

    assert _pagar(enviar_webhook, pid).status_code == 200
    assert client.get(f"/pedidos/{pid}").json()["status"] == "PAGO"

    fila_cozinha = client.get("/pedidos/?status=PAGO").json()
    assert [p["id"] for p in fila_cozinha] == [pid]

    for proximo in ("PREPARANDO", "PRONTO", "ENTREGUE"):
        r = client.patch(f"/pedidos/{pid}", json={"status": proximo})
        assert r.status_code == 200
        assert r.json()["status"] == proximo


# --- Máquina de estados ---

def test_patch_nao_marca_como_pago(client, pedido_criado):
    r = client.patch(f"/pedidos/{pedido_criado['id']}", json={"status": "PAGO"})
    assert r.status_code == 400


def test_transicao_para_tras_e_bloqueada(client, enviar_webhook, pedido_criado):
    pid = pedido_criado["id"]
    _pagar(enviar_webhook, pid)
    client.patch(f"/pedidos/{pid}", json={"status": "PREPARANDO"})
    r = client.patch(f"/pedidos/{pid}", json={"status": "CRIADO"})
    assert r.status_code == 400
    assert "Transição inválida" in r.json()["detail"]


def test_pedido_cancelado_nao_pode_ser_pago(client, enviar_webhook, pedido_criado):
    pid = pedido_criado["id"]
    client.patch(f"/pedidos/{pid}", json={"status": "CANCELADO"})
    assert _pagar(enviar_webhook, pid).status_code == 409
    assert client.get(f"/pedidos/{pid}").json()["status"] == "CANCELADO"


def test_webhook_nao_regride_pedido_em_preparo(client, enviar_webhook, pedido_criado):
    pid = pedido_criado["id"]
    _pagar(enviar_webhook, pid, tx="tx_1")
    client.patch(f"/pedidos/{pid}", json={"status": "PREPARANDO"})
    assert _pagar(enviar_webhook, pid, tx="tx_2").status_code == 409
    assert client.get(f"/pedidos/{pid}").json()["status"] == "PREPARANDO"


# --- Webhook: segurança e idempotência ---

def test_webhook_sem_assinatura_valida_e_rejeitado(client, enviar_webhook, pedido_criado):
    r = enviar_webhook(
        {"pedido_id": pedido_criado["id"], "status_transacao": "aprovado", "id_transacao_gateway": "tx"},
        assinatura="forjada",
    )
    assert r.status_code == 401
    assert client.get(f"/pedidos/{pedido_criado['id']}").json()["status"] == "CRIADO"


def test_reentrega_da_mesma_transacao_e_idempotente(client, enviar_webhook, pedido_criado):
    pid = pedido_criado["id"]
    _pagar(enviar_webhook, pid, tx="tx_dup")
    client.patch(f"/pedidos/{pid}", json={"status": "PREPARANDO"})
    r = _pagar(enviar_webhook, pid, tx="tx_dup")
    assert r.status_code == 200
    assert client.get(f"/pedidos/{pid}").json()["status"] == "PREPARANDO"


def test_mesma_transacao_nao_paga_dois_pedidos(client, enviar_webhook, pedido_criado):
    produto_id = pedido_criado["itens"][0]["produto_id"]
    outro = client.post("/pedidos/", json={"itens": [{"produto_id": produto_id, "quantidade": 1}]}).json()
    _pagar(enviar_webhook, pedido_criado["id"], tx="tx_unica")
    assert _pagar(enviar_webhook, outro["id"], tx="tx_unica").status_code == 409


def test_pagamento_recusado_nao_altera_pedido(client, enviar_webhook, pedido_criado):
    r = _pagar(enviar_webhook, pedido_criado["id"], status="recusado")
    assert r.status_code == 200
    assert client.get(f"/pedidos/{pedido_criado['id']}").json()["status"] == "CRIADO"


# --- Cardápio ---

def test_preco_do_pedido_fica_congelado(client, pedido_criado):
    produto_id = pedido_criado["itens"][0]["produto_id"]
    r = client.patch(f"/produtos/{produto_id}", json={"preco": "40.00"})
    assert r.status_code == 200
    assert Decimal(client.get(f"/produtos/{produto_id}").json()["preco_atual"]) == Decimal("40.00")
    assert Decimal(client.get(f"/pedidos/{pedido_criado['id']}").json()["total"]) == Decimal("70.00")


def test_pedido_com_produto_inexistente(client):
    r = client.post("/pedidos/", json={"itens": [{"produto_id": 999, "quantidade": 1}]})
    assert r.status_code == 404
