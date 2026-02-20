"""
AI 車險推薦系統 - 應用程式入口
"""
import uvicorn

from app.config import settings

if __name__ == "__main__":
    uvicorn.run(
        "app.index:app",
        host=settings.host,
        port=settings.port,
        reload=settings.debug,
        log_level="info"
    )
