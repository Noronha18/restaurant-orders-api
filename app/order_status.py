"""Máquina de estados do pedido. Única fonte de verdade sobre quais transições são válidas."""
from app.schemas import StatusPedido as S

# Transições permitidas pela API operacional (balcão/cozinha/entrega).
# CRIADO -> PAGO NÃO está aqui: só o webhook de pagamento confirmado pode marcar um pedido como pago.
TRANSICOES_MANUAIS: dict[S, set[S]] = {
    S.CRIADO: {S.CANCELADO},
    S.PAGO: {S.PREPARANDO, S.CANCELADO},
    S.PREPARANDO: {S.PRONTO},
    S.PRONTO: {S.ENTREGUE},
    S.ENTREGUE: set(),
    S.CANCELADO: set(),
}

# Estado de origem exigido para o webhook aprovar um pagamento.
ORIGEM_PAGAMENTO = S.CRIADO


def destinos_manuais(atual: S) -> set[S]:
    return TRANSICOES_MANUAIS.get(atual, set())
