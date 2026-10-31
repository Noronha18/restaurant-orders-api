import hashlib
import hmac

from fastapi import HTTPException, Request, status

from app.config import settings

SIGNATURE_HEADER = "X-Webhook-Signature"


def assinar(body: bytes, secret: str | None = None) -> str:
    """Assinatura HMAC-SHA256 (hex) do corpo bruto da requisição."""
    key = (secret or settings.WEBHOOK_SECRET).encode()
    return hmac.new(key, body, hashlib.sha256).hexdigest()


async def verificar_assinatura_webhook(request: Request) -> bytes:
    """Garante que o webhook veio do gateway: compara a assinatura em tempo constante."""
    body = await request.body()
    recebida = request.headers.get(SIGNATURE_HEADER, "")
    if not recebida or not hmac.compare_digest(recebida, assinar(body)):
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Assinatura do webhook inválida")
    return body
