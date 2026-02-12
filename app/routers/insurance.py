import uuid
import logging

from fastapi import APIRouter

from app.models import (
    InsuranceRecommendRequest,
    InsuranceRecommendResponse,
    AnalysisResults,
    RadarData,
    AIProposal,
    PriceSummary,
    ErrorResponse,
)
from app.services.insurance_service import InsuranceService
from app.services.openai_service import openai_service

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/v1/insurance", tags=["Insurance"])


@router.post(
    "/recommend",
    response_model=InsuranceRecommendResponse,
    responses={
        400: {
            "model": ErrorResponse,
            "description": "業務邏輯錯誤（如車籍資料錯誤）"
        },
        422: {
            "model": ErrorResponse,
            "description": "請求資料驗證失敗"
        },
        500: {
            "model": ErrorResponse,
            "description": "系統內部錯誤"
        },
        502: {
            "model": ErrorResponse,
            "description": "外部服務錯誤（如 OpenAI）"
        }
    }
)
async def recommend_insurance(request: InsuranceRecommendRequest):
    """
    AI 車險推薦 API

    根據用戶車籍資料與車齡，自動推薦三種保險方案：
    - AI 推薦首選：根據車齡自動配置最適合的套餐
    - 小資基礎選：最低保費的基本保障
    - 自訂調整：用戶可自行調整的方案

    套餐規則：
    - 車齡 ≤5年：豪華套餐
    - 車齡 5-10年：進階套餐
    - 車齡 >10年：基本套餐
    - 車齡 ≤3年：額外含竊盜險
    """
    # 生成用戶 ID
    user_id = f"USR-{uuid.uuid4().hex[:8].upper()}"

    # 計算車齡
    car_age = InsuranceService.calculate_car_age(
        request.profile.car_details.car_year
    )
    logger.info(f"Processing recommendation for car_age={car_age}")

    # 根據車齡決定套餐等級
    package_type, insurance_codes = InsuranceService.determine_package(car_age)
    logger.info(f"Package type: {package_type}, codes: {insurance_codes}")

    # 計算保費
    premium_details = InsuranceService.calculate_premium(insurance_codes)

    # 生成雷達圖數據
    radar_data = InsuranceService.generate_radar_data(package_type)

    # 生成用戶標籤
    persona_tags = InsuranceService.generate_persona_tags(car_age, package_type)

    # 呼叫 OpenAI 生成 AI 推薦報告
    ai_commentary = await openai_service.generate_commentary(
        car_age=car_age,
        package_type=package_type,
        premium_details=premium_details,
        profile=request.profile
    )

    # 組裝三種方案
    plans = InsuranceService.build_plans(premium_details)

    return InsuranceRecommendResponse(
        status="success",
        user_id=user_id,
        analysis_results=AnalysisResults(
            persona_tags=persona_tags,
            radar_data=RadarData(**radar_data)
        ),
        ai_proposal=AIProposal(
            commentary=ai_commentary,
            plans=plans,
            price_summary=PriceSummary(
                original_total=premium_details["total"],
                discount=premium_details.get("discount", 0),
                final_amount=premium_details["total"] - premium_details.get("discount", 0)
            )
        )
    )
