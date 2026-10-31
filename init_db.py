"""Cria as tabelas no banco configurado em DATABASE_URL. Uso: python init_db.py"""
from app.database import Base, engine
from app import models  # noqa: F401  (registra os models no metadata)

if __name__ == "__main__":
    Base.metadata.create_all(bind=engine)
    print("Tabelas criadas.")
