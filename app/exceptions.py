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


class PlateNotFoundException(BusinessException):
    """車牌查無資料"""
    def __init__(self, message: str = "查無此車牌資料，請確認車牌號碼是否正確。"):
        super().__init__(message=message)
        self.code = "PLATE_NOT_FOUND"


class InvalidIdFormatException(ValidationException):
    """身分證格式錯誤"""
    def __init__(self, message: str = "身分證格式錯誤，請輸入正確的身分證字號。"):
        super().__init__(message=message)
        self.code = "INVALID_ID_FORMAT"


class InvalidPlateFormatException(ValidationException):
    """車牌格式錯誤"""
    def __init__(self, message: str = "車牌格式錯誤，請輸入正確的車牌號碼。"):
        super().__init__(message=message)
        self.code = "INVALID_PLATE_FORMAT"


class CarDataMismatchException(BusinessException):
    """車籍資料不符"""
    def __init__(self, message: str = "車籍資料異常，請確認資料是否正確。"):
        super().__init__(message=message)
        self.code = "CAR_DATA_MISMATCH"


class QAMissingFieldException(ValidationException):
    """問卷有未填類別"""
    def __init__(self, message: str = "問卷有未填類別，請完成所有 5 類問卷。"):
        super().__init__(message=message)
        self.code = "QA_MISSING_FIELD"