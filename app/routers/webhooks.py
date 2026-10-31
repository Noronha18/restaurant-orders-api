import logging

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import ValidationError
from sqlalchemy.orm import Session

from app.database import get_db
from app.models import Pedido
from app.order_status import ORIGEM_PAGAMENTO
from app.schemas import StatusPedido, WebhookPagamento
from app.security import verificar_assinatura_webhook

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/webhooks", tags=["Webhooks"])


@router.post("/pagamento", status_code=status.HTTP_200_OK)
def receber_webhook_pagamento(
    body: bytes = Depends(verificar_assinatura_webhook),
    db: Session = Depends(get_db),
):
    """
    Recebe a confirmação de pagamento do gateway (assinada com HMAC-SHA256).

    - **aprovado**: move o pedido de CRIADO para PAGO e registra a transação.
    - **recusado**: não altera o pedido.
    - A mesma transação reenviada é ignorada (idempotência por `id_transacao_gateway`).
    """
    try:
        evento = WebhookPagamento.model_validate_json(body)
    except ValidationError as exc:
        raise HTTPException(status_code=422, detail=exc.errors(include_url=False, include_context=False))

    logger.info("Webhook de pagamento: pedido=%s transacao=%s status=%s",
                evento.pedido_id, evento.id_transacao_gateway, evento.status_transacao)

    pedido = db.get(Pedido, evento.pedido_id, with_for_update=True)
    if not pedido:
        raise HTTPException(status_code=404, detail="Pedido não encontrado para este pagamento")

    # Reentrega da mesma notificação: responde 200 sem efeito colateral
    if pedido.id_transacao_gateway == evento.id_transacao_gateway:
        return {"msg": "Notificação já processada.", "status": pedido.status}

    if evento.status_transacao == "recusado":
        return {"msg": "Pagamento recusado pelo gateway. Pedido inalterado.", "status": pedido.status}

    if pedido.status != ORIGEM_PAGAMENTO:
        # Pedido já pago por outra transação, cancelado ou em andamento: não regride o fluxo
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=f"Pedido em '{pedido.status}' não pode receber pagamento.",
        )

    transacao_em_uso = (
        db.query(Pedido.id).filter(Pedido.id_transacao_gateway == evento.id_transacao_gateway).first()
    )
    if transacao_em_uso:
        raise HTTPException(status_code=409, detail="Transação já usada em outro pedido.")

    pedido.status = StatusPedido.PAGO.value
    pedido.id_transacao_gateway = evento.id_transacao_gateway
    db.commit()
    return {"msg": f"Pedido {pedido.id} pago.", "status": pedido.status}
