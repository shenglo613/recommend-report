import logging
from typing import Dict

from openai import OpenAI, APIError, APIConnectionError, RateLimitError

from app.config import settings
from app.exceptions import ExternalServiceException
from app.models import Profile

logger = logging.getLogger(__name__)


class OpenAIService:
    """OpenAI API 服務"""

    def __init__(self):
        self.api_key = settings.openai_api_key
        self.model = settings.openai_model
        self.client = None
        if self.api_key:
            self.client = OpenAI(api_key=self.api_key)

    async def generate_commentary(
        self,
        car_age: int,
        package_type: str,
        premium_details: Dict,
        profile: Profile
    ) -> str:
        """
        呼叫 OpenAI 生成 AI 推薦報告

        Args:
            car_age: 車齡
            package_type: 套餐類型 (deluxe/advanced/basic)
            premium_details: 保費詳情
            profile: 用戶資料

        Returns:
            AI 生成的推薦文案
        """
        if not self.client:
            logger.warning("OpenAI API Key not configured, using default commentary")
            return self._get_default_commentary(car_age, package_type, premium_details)

        try:
            prompt = self._build_prompt(car_age, package_type, premium_details, profile)

            response = self.client.chat.completions.create(
                model=self.model,
                messages=[{"role": "user", "content": prompt}],
                max_tokens=500,
                temperature=0.7
            )

            return response.choices[0].message.content

        except RateLimitError as e:
            logger.warning(f"OpenAI rate limit exceeded: {e}")
            # Rate limit 時使用預設文案，不中斷服務
            return self._get_default_commentary(car_age, package_type, premium_details)

        except APIConnectionError as e:
            logger.error(f"OpenAI connection error: {e}")
            # 連線錯誤時使用預設文案
            return self._get_default_commentary(car_age, package_type, premium_details)

        except APIError as e:
            logger.error(f"OpenAI API error: {e}")
            # API 錯誤時使用預設文案
            return self._get_default_commentary(car_age, package_type, premium_details)

        except Exception as e:
            logger.error(f"Unexpected error calling OpenAI: {e}", exc_info=True)
            return self._get_default_commentary(car_age, package_type, premium_details)

    def _build_prompt(
        self,
        car_age: int,
        package_type: str,
        premium_details: Dict,
        profile: Profile
    ) -> str:
        """建構 OpenAI prompt"""
        package_names = {
            "deluxe": "豪華套餐",
            "advanced": "進階套餐",
            "basic": "基本套餐"
        }
        package_name = package_names.get(package_type, package_type)

        items_desc = [
            f"{item['name']}-{item['amount']}"
            for item in premium_details['items']
        ]

        return f"""
你是專業的汽車保險顧問。請根據以下資料，生成一段專業的保險推薦說明（約150-200字）：

車主資料：
- 姓名：{profile.name}
- 車齡：{car_age}年
- 車型：{profile.car_details.vehicle_type}
- 排氣量：{profile.car_details.displacement}cc

推薦套餐：{package_name}
保障內容：{items_desc}
總保費：{premium_details['total']}元

請用專業但親切的語氣，說明為什麼推薦這個方案，以及這個方案如何保障車主。
請以 JSON 格式回覆，包含以下結構：
{{
    "summary": "一句話摘要",
    "risk_analysis": "風險分析（2-3句）",
    "recommendation_reason": "推薦理由（2-3句）",
    "coverage_highlights": ["重點保障1", "重點保障2", "重點保障3"]
}}
"""

    def _get_default_commentary(
        self,
        car_age: int,
        package_type: str,
        premium_details: Dict
    ) -> str:
        """取得預設文案（當 OpenAI 不可用時）"""
        package_names = {
            "deluxe": "豪華套餐",
            "advanced": "進階套餐",
            "basic": "基本套餐"
        }
        package_name = package_names.get(package_type, package_type)

        return (
            f"根據您的愛車資料分析，車齡{car_age}年，"
            f"我們為您推薦「{package_name}」，"
            f"總保費約 {premium_details['total']:,} 元，"
            f"折扣後只要 {premium_details['total'] - premium_details.get('discount', 0):,} 元。"
        )


# 單例模式
openai_service = OpenAIService()
