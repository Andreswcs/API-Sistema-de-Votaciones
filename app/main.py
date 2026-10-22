from fastapi import FastAPI

from app.api.routers import health

app = FastAPI(
    title="Sistema de Votaciones",
    description="API para gestionar votantes, candidatos y votos, con estadísticas de resultados.",
    version="1.0.0",
)

app.include_router(health.router)
