from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from src.api import deps
from src.api.routes import router
from src.core.config import settings


@asynccontextmanager
async def _lifespan(app: FastAPI):
    deps.startup()
    try:
        yield
    finally:
        deps.shutdown()


def create_app() -> FastAPI:
    app = FastAPI(title='Agentic SDLC API', version='1.0.0', lifespan=_lifespan)
    app.add_middleware(
        CORSMiddleware,
        allow_origins=[settings.STREAMLIT_ORIGIN, 'http://localhost:8501'],
        allow_credentials=True,
        allow_methods=['*'],
        allow_headers=['*'],
    )
    app.include_router(router)

    @app.get('/health')
    def health():
        return {'status': 'ok'}

    return app


app = create_app()
