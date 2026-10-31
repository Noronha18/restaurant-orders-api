import logging

from fastapi import FastAPI

from app.routers import pedidos, produtos, webhooks

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(name)s: %(message)s")

app = FastAPI(
    title="Restaurant Orders API",
    description="Cardápio, pedidos com máquina de estados e confirmação de pagamento por webhook.",
    version="1.0.0",
)

app.include_router(produtos.router)
app.include_router(pedidos.router)
app.include_router(webhooks.router)


@app.get("/health", tags=["Health"])
def health_check():
    return {"status": "ok"}
