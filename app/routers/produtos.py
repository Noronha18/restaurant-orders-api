from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.database import get_db
from app.models import Produto
from app.schemas import ProdutoCreate, ProdutoResponse, ProdutoUpdate

router = APIRouter(prefix="/produtos", tags=["Produtos"])


def _buscar(db: Session, produto_id: int) -> Produto:
    produto = db.get(Produto, produto_id)
    if not produto:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Produto não encontrado")
    return produto


@router.get("/", response_model=list[ProdutoResponse])
def listar_produtos(categoria: Optional[str] = None, db: Session = Depends(get_db)):
    """Lista o cardápio, opcionalmente filtrado por categoria."""
    query = db.query(Produto).order_by(Produto.categoria, Produto.nome)
    if categoria:
        query = query.filter(Produto.categoria == categoria)
    return query.all()


@router.get("/{produto_id}", response_model=ProdutoResponse)
def obter_produto(produto_id: int, db: Session = Depends(get_db)):
    return _buscar(db, produto_id)


@router.post("/", response_model=ProdutoResponse, status_code=status.HTTP_201_CREATED)
def criar_produto(produto: ProdutoCreate, db: Session = Depends(get_db)):
    novo = Produto(
        nome=produto.nome,
        preco_atual=produto.preco,
        categoria=produto.categoria,
        descricao=produto.descricao,
    )
    db.add(novo)
    db.commit()
    db.refresh(novo)
    return novo


@router.patch("/{produto_id}", response_model=ProdutoResponse)
def editar_produto(produto_id: int, dados: ProdutoUpdate, db: Session = Depends(get_db)):
    """Atualiza campos do produto. Pedidos já feitos mantêm o preço da época (snapshot)."""
    produto = _buscar(db, produto_id)
    campos = dados.model_dump(exclude_unset=True)
    if "preco" in campos:
        campos["preco_atual"] = campos.pop("preco")
    for campo, valor in campos.items():
        setattr(produto, campo, valor)
    db.commit()
    db.refresh(produto)
    return produto
