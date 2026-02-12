from typing import Any, Optional


class AppException(Exception):
    """應用程式基礎例外"""

    def __init__(
        self,
        code: str,
        message: str,
        status_code: int = 400,
        details: Optional[Any] = None
    ):
        self.code = code
        self.message = message
        self.status_code = status_code
        self.details = details
        super().__init__(message)


class ValidationException(AppException):
    """資料驗證錯誤"""

    def __init__(self, message: str, details: Optional[Any] = None):
        super().__init__(
            code="VALIDATION_ERROR",
            message=message,
            status_code=422,
            details=details
        )


class BusinessException(AppException):
    """業務邏輯錯誤"""

    def __init__(self, message: str, details: Optional[Any] = None):
        super().__init__(
            code="BUSINESS_ERROR",
            message=message,
            status_code=400,
            details=details
        )


class ExternalServiceException(AppException):
    """外部服務錯誤（如 OpenAI）"""

    def __init__(self, service: str, message: str, details: Optional[Any] = None):
        super().__init__(
            code="EXTERNAL_SERVICE_ERROR",
            message=f"{service} 服務錯誤: {message}",
            status_code=502,
            details=details
        )


class CarDataException(BusinessException):
    """車籍資料錯誤"""

    def __init__(self, message: str):
        super().__init__(message=message)
        self.code = "CAR_DATA_ERROR"


class InsuranceCalculationException(BusinessException):
    """保費計算錯誤"""

    def __init__(self, message: str):
        super().__init__(message=message)
        self.code = "INSURANCE_CALCULATION_ERROR"
