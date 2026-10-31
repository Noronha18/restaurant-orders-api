from datetime import datetime
from decimal import Decimal
from enum import Enum
from typing import Literal, Optional

from pydantic import BaseModel, ConfigDict, Field


class StatusPedido(str, Enum):
    CRIADO = "CRIADO"
    PAGO = "PAGO"
    PREPARANDO = "PREPARANDO"
    PRONTO = "PRONTO"
    ENTREGUE = "ENTREGUE"
    CANCELADO = "CANCELADO"


# --- Produtos ---

class ProdutoCreate(BaseModel):
    nome: str = Field(..., min_length=2, description="Nome do item do cardápio")
    descricao: Optional[str] = None
    preco: Decimal = Field(..., gt=0, max_digits=10, decimal_places=2, description="Preço maior que zero")
    categoria: str = Field(..., min_length=2, description="Ex.: Lanches, Bebidas")


class ProdutoUpdate(BaseModel):
    nome: Optional[str] = Field(None, min_length=2)
    descricao: Optional[str] = None
    preco: Optional[Decimal] = Field(None, gt=0, max_digits=10, decimal_places=2)
    categoria: Optional[str] = Field(None, min_length=2)


class ProdutoResponse(BaseModel):
    id: int
    nome: str
    descricao: Optional[str] = None
    preco_atual: Decimal
    categoria: str

    model_config = ConfigDict(from_attributes=True)


# --- Pedidos ---

class ItemPedidoCreate(BaseModel):
    produto_id: int
    quantidade: int = Field(..., gt=0, examples=[1])


class PedidoCreate(BaseModel):
    itens: list[ItemPedidoCreate] = Field(..., min_length=1)


class ItemPedidoResponse(BaseModel):
    produto_id: int
    quantidade: int
    preco_unitario_snapshot: Decimal
    subtotal: Decimal

    model_config = ConfigDict(from_attributes=True)


class PedidoResponse(BaseModel):
    id: int
    status: StatusPedido
    data_criacao: datetime
    total: Decimal
    itens: list[ItemPedidoResponse]

    model_config = ConfigDict(from_attributes=True)


class PedidoUpdate(BaseModel):
    status: StatusPedido


# --- Webhook ---

class WebhookPagamento(BaseModel):
    pedido_id: int
    status_transacao: Literal["aprovado", "recusado"]
    id_transacao_gateway: str = Field(..., min_length=1)
