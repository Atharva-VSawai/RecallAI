from fastapi import APIRouter
from .routes import activity_routes, file_routes, graph_routes, health_routes, ingestion_routes, query_routes

api_router = APIRouter()
api_router.include_router(health_routes.router)
api_router.include_router(query_routes.router)
api_router.include_router(ingestion_routes.router)
api_router.include_router(activity_routes.router)
api_router.include_router(file_routes.router)
api_router.include_router(graph_routes.router)
