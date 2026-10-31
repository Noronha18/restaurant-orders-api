from decimal import Decimal

from sqlalchemy import Column, DateTime, ForeignKey, Integer, Numeric, String
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func

from app.database import Base


class Produto(Base):
    __tablename__ = "produtos"

    id = Column(Integer, primary_key=True, index=True)
    nome = Column(String, nullable=False, index=True)
    preco_atual = Column(Numeric(10, 2), nullable=False)  # preço de tabela hoje
    categoria = Column(String, nullable=False, index=True)
    descricao = Column(String)

    itens_vendidos = relationship("ItemPedido", back_populates="produto")


class Pedido(Base):
    __tablename__ = "pedidos"

    id = Column(Integer, primary_key=True, index=True)
    data_criacao = Column(DateTime(timezone=True), server_default=func.now())
    status = Column(String, nullable=False, default="CRIADO", index=True)
    # Transação do gateway que pagou o pedido. UNIQUE garante que uma transação paga um único pedido.
    id_transacao_gateway = Column(String, unique=True, nullable=True)

    itens = relationship("ItemPedido", back_populates="pedido", cascade="all, delete-orphan")

    @property
    def total(self) -> Decimal:
        return sum((item.subtotal for item in self.itens), Decimal("0.00"))


class ItemPedido(Base):
    __tablename__ = "item_pedidos"

    id = Column(Integer, primary_key=True, index=True)
    pedido_id = Column(Integer, ForeignKey("pedidos.id"), nullable=False)
    produto_id = Column(Integer, ForeignKey("produtos.id"), nullable=False)
    quantidade = Column(Integer, nullable=False, default=1)
    # Preço congelado no momento da compra: mudanças no cardápio não alteram pedidos antigos
    preco_unitario_snapshot = Column(Numeric(10, 2), nullable=False)

    pedido = relationship("Pedido", back_populates="itens")
    produto = relationship("Produto", back_populates="itens_vendidos")

    @property
    def subtotal(self) -> Decimal:
        return Decimal(self.preco_unitario_snapshot) * self.quantidade
