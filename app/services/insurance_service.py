import asyncio
import re
import uuid
import logging

from app.exceptions import (
    InvalidIdFormatException,
    InvalidPlateFormatException,
    CarDataMismatchException,
)
from app.models.request import InsuranceRecommendRequest
from app.models.response import (
    InsuranceRecommendResponse,
    AnalysisResults,
    RadarData,
    CompulsoryInsurance,
    RecommendedPlan,
    CustomPlan,
    Plans,
    AIProposal,
)

from app.services.insurance_engine import InsuranceEngine
from app.services.openai_service import openai_service

logger = logging.getLogger(__name__)


class InsuranceService:
    """保險推薦服務（orchestration 層）"""

    @staticmethod
    def _validate_input(request: InsuranceRecommendRequest):
        """輸入驗證（PRD 第 11.3 節 error codes）"""
        # 身分證格式：1 英文 + 1 性別碼(1|2) + 8 數字
        if not re.match(r"^[A-Z][12]\d{8}$", request.profile.id_number):
            raise InvalidIdFormatException()

        # 車牌格式：支援多種台灣車牌格式
        plate = request.profile.license_plate.replace("-", "")
        if not re.match(r"^[A-Z0-9]{4,7}$", plate):
            raise InvalidPlateFormatException()

        # 排氣量合理性
        if request.profile.car_details.displacement <= 0:
            raise CarDataMismatchException("排氣量資料異常")

    @staticmethod
    async def recommend(request: InsuranceRecommendRequest) -> InsuranceRecommendResponse:
        """
        主流程：車齡定錨 → 問卷位移 → 預算降級 → 三方案產出

        Args:
            request: 保險推薦請求

        Returns:
            InsuranceRecommendResponse
        """
        # 1. 驗證輸入
        InsuranceService._validate_input(request)

        # 2. 建立引擎（自動執行車齡定錨）
        engine = InsuranceEngine(
            registration_year=request.profile.car_details.registration_year,
            displacement=request.profile.car_details.displacement,
        )
        logger.info(f"Package: {engine.package}, car_age: {engine.car_age}")

        # 3. 問卷位移（如有）
        qa = request.analysis_qa
        if qa:
            engine.apply_questionnaire(qa)
            logger.info(f"After questionnaire: {engine.indices}")

        # 4. 預算降級（如有）
        if request.target_amount:
            engine.reduce_premium(request.target_amount)
            logger.info(f"After reduce: {engine.indices}")

        # 5. 推薦方案基本資料
        recommended_code = engine.generate_insurance_code()
        recommended_items = engine.build_items()
        recommended_summary = engine.build_price_summary()

        # 6. 小資方案基本資料
        economy_data = engine.build_economy_plan()
        economy_indices = economy_data["economy_indices"]

        # 7. 自訂方案
        custom_plan = CustomPlan(
            name="自訂調整",
            base_code=recommended_code,
            adjustable_items=engine.build_custom_plan(),
        )

        # 8. 雷達圖（各方案獨立計算）
        recommended_radar = engine.calculate_radar()
        economy_radar = engine.calculate_radar(indices=economy_indices)

        # 9. Persona tags
        persona_tags = engine.generate_persona_tags(qa)

        # 10. 計算方案差異（供小資點評使用）
        diff_data = engine.compute_plan_diff(economy_indices)

        # 11. AI 點評（推薦 + 小資並行呼叫）
        recommended_commentary, economy_commentary = await asyncio.gather(
            openai_service.generate_commentary(
                persona_tags=persona_tags,
                insurance_code=recommended_code,
                package_name=engine.get_package_name(),
                car_age=engine.car_age,
            ),
            openai_service.generate_economy_commentary(
                diff_data=diff_data,
                package_name=engine.get_package_name(),
                car_age=engine.car_age,
            ),
        )

        # 12. 組裝方案（含 radar_data 和 commentary）
        recommended_plan = RecommendedPlan(
            name="AI 推薦首選",
            insurance_code=recommended_code,
            items=recommended_items,
            price_summary=recommended_summary,
            radar_data=RadarData(**recommended_radar),
            commentary=recommended_commentary,
        )

        economy_plan = RecommendedPlan(
            name="小資基礎選",
            insurance_code=economy_data["insurance_code"],
            items=economy_data["items"],
            price_summary=economy_data["price_summary"],
            radar_data=RadarData(**economy_radar),
            commentary=economy_commentary,
        )

        # 13. 強制險
        compulsory_premium = engine._get_compulsory_premium()

        # 14. 組裝 response
        return InsuranceRecommendResponse(
            status="success",
            user_id=f"USR-{uuid.uuid4().hex[:8].upper()}",
            analysis_results=AnalysisResults(
                persona_tags=persona_tags,
                insurance_code=recommended_code,
            ),
            compulsory_insurance=CompulsoryInsurance(
                premium=compulsory_premium,
            ),
            ai_proposal=AIProposal(
                plans=Plans(
                    recommended=recommended_plan,
                    economy=economy_plan,
                    custom=custom_plan,
                ),
            ),
        )
