import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI
from starlette.middleware.cors import CORSMiddleware

from app.config import settings
from app.handlers import register_exception_handlers
from app.routers import insurance_router

# 設定 logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(_: FastAPI):
    """應用程式生命週期管理"""
    # Startup
    logger.info(f"Starting {settings.app_name}")
    logger.info(f"Debug mode: {settings.debug}")
    yield
    # Shutdown
    logger.info(f"Shutting down {settings.app_name}")


def create_app() -> FastAPI:
    """建立 FastAPI 應用程式"""
    app = FastAPI(
        title=settings.app_name,
        description="AI 車險推薦系統 API",
        version="1.0.0",
        lifespan=lifespan,
    )

    # CORS 設定
    app.add_middleware(
        CORSMiddleware,
        allow_origins=[
            "http://localhost:3000",
            "http://localhost:8080",
            "https://recommend-report.vercel.app",
            "https://*.vercel.app",
        ],
        allow_credentials=True,
        allow_methods=["GET", "POST", "PUT", "DELETE"],
        allow_headers=["*"],
    )

    # 註冊例外處理器
    register_exception_handlers(app)

    # 註冊路由
    app.include_router(insurance_router)

    # 健康檢查
    @app.get("/", tags=["Health"])
    def health_check():
        return {
            "status": "healthy",
            "app": settings.app_name,
            "version": "1.0.0"
        }

    return app


app = create_app()
