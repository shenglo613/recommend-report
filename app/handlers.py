import logging
from typing import Union

from fastapi import FastAPI, Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from pydantic import ValidationError

from app.exceptions import AppException

logger = logging.getLogger(__name__)


def create_error_response(
    code: str,
    message: str,
    status_code: int,
    details: Union[dict, list, None] = None
) -> JSONResponse:
    """建立統一的錯誤回應格式"""
    content = {
        "status": "error",
        "error": {
            "code": code,
            "message": message,
        }
    }
    if details:
        content["error"]["details"] = details

    return JSONResponse(status_code=status_code, content=content)


def register_exception_handlers(app: FastAPI) -> None:
    """註冊全域例外處理器"""

    @app.exception_handler(AppException)
    async def app_exception_handler(request: Request, exc: AppException):
        """處理應用程式自定義例外"""
        logger.warning(
            f"AppException: {exc.code} - {exc.message}",
            extra={"path": request.url.path, "details": exc.details}
        )
        return create_error_response(
            code=exc.code,
            message=exc.message,
            status_code=exc.status_code,
            details=exc.details
        )

    @app.exception_handler(RequestValidationError)
    async def validation_exception_handler(request: Request, exc: RequestValidationError):
        """處理 Request 驗證錯誤"""
        errors = []
        for error in exc.errors():
            field = " -> ".join(str(loc) for loc in error["loc"])
            errors.append({
                "field": field,
                "message": error["msg"],
                "type": error["type"]
            })

        logger.warning(
            f"Validation error on {request.url.path}",
            extra={"errors": errors}
        )

        return create_error_response(
            code="VALIDATION_ERROR",
            message="請求資料驗證失敗",
            status_code=422,
            details=errors
        )

    @app.exception_handler(ValidationError)
    async def pydantic_validation_handler(request: Request, exc: ValidationError):
        """處理 Pydantic 驗證錯誤"""
        errors = []
        for error in exc.errors():
            field = " -> ".join(str(loc) for loc in error["loc"])
            errors.append({
                "field": field,
                "message": error["msg"],
                "type": error["type"]
            })

        return create_error_response(
            code="VALIDATION_ERROR",
            message="資料驗證失敗",
            status_code=422,
            details=errors
        )

    @app.exception_handler(ValueError)
    async def value_error_handler(request: Request, exc: ValueError):
        """處理值錯誤"""
        logger.error(f"ValueError: {exc}", exc_info=True)
        return create_error_response(
            code="VALUE_ERROR",
            message=str(exc),
            status_code=400
        )

    @app.exception_handler(Exception)
    async def general_exception_handler(request: Request, exc: Exception):
        """處理未預期的例外"""
        logger.error(
            f"Unexpected error on {request.url.path}: {exc}",
            exc_info=True
        )
        return create_error_response(
            code="INTERNAL_ERROR",
            message="系統發生未預期的錯誤，請稍後再試",
            status_code=500
        )
