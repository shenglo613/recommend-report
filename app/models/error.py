from typing import Any, List, Optional
from pydantic import BaseModel


class ErrorDetail(BaseModel):
    """錯誤詳情"""
    field: str
    message: str
    type: str


class ErrorInfo(BaseModel):
    """錯誤資訊"""
    code: str
    message: str
    details: Optional[List[ErrorDetail]] = None


class ErrorResponse(BaseModel):
    """錯誤回應"""
    status: str = "error"
    error: ErrorInfo

    class Config:
        json_schema_extra = {
            "example": {
                "status": "error",
                "error": {
                    "code": "VALIDATION_ERROR",
                    "message": "請求資料驗證失敗",
                    "details": [
                        {
                            "field": "body -> profile -> car_details -> car_year",
                            "message": "Field required",
                            "type": "missing"
                        }
                    ]
                }
            }
        }
