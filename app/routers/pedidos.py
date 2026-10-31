from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session, selectinload

from app.database import get_db
from app.models import ItemPedido, Pedido, Produto
from app.order_status import destinos_manuais
from app.schemas import PedidoCreate, PedidoResponse, PedidoUpdate, StatusPedido

router = APIRouter(prefix="/pedidos", tags=["Pedidos"])


def _buscar(db: Session, pedido_id: int) -> Pedido:
    pedido = db.query(Pedido).options(selectinload(Pedido.itens)).filter(Pedido.id == pedido_id).first()
    if not pedido:
        raise HTTPException(status_code=404, detail="Pedido não encontrado")
    return pedido


@router.get("/", response_model=list[PedidoResponse])
def listar_pedidos(status: Optional[StatusPedido] = None, db: Session = Depends(get_db)):
    """Lista pedidos, do mais antigo ao mais novo. Com `?status=PAGO`, vira a fila da cozinha (KDS)."""
    query = db.query(Pedido).options(selectinload(Pedido.itens)).order_by(Pedido.data_criacao, Pedido.id)
    if status:
        query = query.filter(Pedido.status == status.value)
    return query.all()


@router.get("/{pedido_id}", response_model=PedidoResponse)
def consultar_pedido(pedido_id: int, db: Session = Depends(get_db)):
    return _buscar(db, pedido_id)


@router.post("/", response_model=PedidoResponse, status_code=status.HTTP_201_CREATED)
def criar_pedido(pedido_in: PedidoCreate, db: Session = Depends(get_db)):
    """Valida os itens, congela o preço atual de cada produto e cria o pedido em CRIADO."""
    ids = {item.produto_id for item in pedido_in.itens}
    produtos = {p.id: p for p in db.query(Produto).filter(Produto.id.in_(ids)).all()}
    faltando = sorted(ids - produtos.keys())
    if faltando:
        raise HTTPException(status_code=404, detail=f"Produto(s) não encontrado(s): {faltando}")

    pedido = Pedido(status=StatusPedido.CRIADO.value)
    pedido.itens = [
        ItemPedido(
            produto_id=item.produto_id,
            quantidade=item.quantidade,
            preco_unitario_snapshot=produtos[item.produto_id].preco_atual,
        )
        for item in pedido_in.itens
    ]
    db.add(pedido)
    db.commit()
    db.refresh(pedido)
    return pedido


@router.patch("/{pedido_id}", response_model=PedidoResponse)
def atualizar_status_pedido(pedido_id: int, atualizacao: PedidoUpdate, db: Session = Depends(get_db)):
    """
    Avança o pedido pela máquina de estados. A marcação como PAGO só acontece pelo
    webhook de pagamento; qualquer transição fora do fluxo retorna 400.
    """
    pedido = _buscar(db, pedido_id)
    atual = StatusPedido(pedido.status)
    permitidos = destinos_manuais(atual)

    if atualizacao.status not in permitidos:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Transição inválida: '{atual.value}' só pode ir para {sorted(s.value for s in permitidos)}",
        )

    pedido.status = atualizacao.status.value
    db.commit()
    db.refresh(pedido)
    return pedido
