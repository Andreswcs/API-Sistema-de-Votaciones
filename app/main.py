from fastapi import FastAPI

from app.api.routers import candidates, health, voters
from app.core.error_handlers import register_error_handlers

app = FastAPI(
    title="Sistema de Votaciones",
    description="API para gestionar votantes, candidatos y votos, con estadísticas de resultados.",
    version="1.0.0",
)

register_error_handlers(app)
app.include_router(health.router)
app.include_router(voters.router)
app.include_router(candidates.router)
