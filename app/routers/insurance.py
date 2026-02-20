import logging

from fastapi import APIRouter

from app.models import (
    InsuranceRecommendRequest,
    InsuranceRecommendResponse,
    ErrorResponse,
)
from app.services.insurance_service import InsuranceService

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/v1/insurance", tags=["Insurance"])


@router.post(
    "/recommend",
    response_model=InsuranceRecommendResponse,
    responses={
        400: {"model": ErrorResponse, "description": "業務邏輯錯誤"},
        422: {"model": ErrorResponse, "description": "請求資料驗證失敗"},
        500: {"model": ErrorResponse, "description": "系統內部錯誤"},
        502: {"model": ErrorResponse, "description": "外部服務錯誤"},
    },
)
async def recommend_insurance(request: InsuranceRecommendRequest):
    """
    AI 車險推薦 API (PRD v2.0)

    根據用戶車籍資料、車齡自動定錨、問卷位移、預算降級，
    產出個人化的三種保險推薦方案。
    """
    return await InsuranceService.recommend(request)
