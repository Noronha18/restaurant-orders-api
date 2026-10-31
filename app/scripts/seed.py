"""Popula o cardápio com dados de exemplo. Uso: python -m app.scripts.seed"""
from decimal import Decimal

from app.database import SessionLocal
from app.models import Produto

CARDAPIO = [
    ("Burger da Casa", "Lanches", "45.90"),
    ("Smash Burger Duplo", "Lanches", "28.50"),
    ("Batata Frita Rústica", "Acompanhamentos", "18.00"),
    ("Refrigerante Lata 350ml", "Bebidas", "6.50"),
    ("Suco de Laranja Natural", "Bebidas", "12.00"),
    ("Pudim de Leite", "Sobremesas", "15.00"),
]


def popular_banco() -> None:
    with SessionLocal() as db:
        if db.query(Produto).count() > 0:
            print("O banco já contém produtos. Seed ignorado.")
            return
        db.add_all(Produto(nome=n, categoria=c, preco_atual=Decimal(p)) for n, c, p in CARDAPIO)
        db.commit()
        print(f"{len(CARDAPIO)} produtos adicionados.")


if __name__ == "__main__":
    popular_banco()
