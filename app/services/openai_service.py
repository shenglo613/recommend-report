import logging
from typing import List

from openai import AsyncOpenAI, APIError, APIConnectionError, RateLimitError

from app.config import settings
from app.constants.insurance_rates import PACKAGE_NAMES

logger = logging.getLogger(__name__)


class OpenAIService:
    """OpenAI API 服務（AsyncOpenAI）"""

    def __init__(self):
        self.client = None
        if settings.openai_api_key:
            self.client = AsyncOpenAI(api_key=settings.openai_api_key)

    async def generate_commentary(
        self,
        persona_tags: List[str],
        insurance_code: str,
        package_name: str,
        car_age: int,
    ) -> str:
        """
        呼叫 OpenAI 生成 AI 推薦點評（PRD 第 12.4 節）

        Args:
            persona_tags: 用戶特徵標籤列表
            insurance_code: 險種代碼字串
            package_name: 套餐中文名稱
            car_age: 車齡

        Returns:
            AI 生成的推薦文案（100~300 字）
        """
        if not self.client:
            logger.warning("OpenAI API Key not configured, using default commentary")
            return self._get_default_commentary(package_name, car_age)

        try:
            prompt = (
                "你是一位專業的汽車保險顧問。根據以下客戶資料，"
                "用 100~300 字的中文生成一段溫暖且專業的保險推薦理由。\n\n"
                f"客戶特徵標籤：{', '.join(persona_tags)}\n"
                f"保險代碼組合：{insurance_code}\n"
                f"套餐層級：{package_name}\n"
                f"車齡：{car_age} 年\n\n"
                "請直接輸出推薦理由，不要加引號或前綴。"
            )

            response = await self.client.chat.completions.create(
                model=settings.openai_model,
                messages=[{"role": "user", "content": prompt}],
                max_tokens=500,
                temperature=0.7,
            )
            return response.choices[0].message.content.strip()

        except RateLimitError as e:
            logger.warning(f"OpenAI rate limit exceeded: {e}")
            return self._get_default_commentary(package_name, car_age)
        except APIConnectionError as e:
            logger.error(f"OpenAI connection error: {e}")
            return self._get_default_commentary(package_name, car_age)
        except APIError as e:
            logger.error(f"OpenAI API error: {e}")
            return self._get_default_commentary(package_name, car_age)
        except Exception as e:
            logger.error(f"Unexpected error calling OpenAI: {e}", exc_info=True)
            return self._get_default_commentary(package_name, car_age)

    @staticmethod
    def _get_default_commentary(package_name: str, car_age: int) -> str:
        """預設文案（當 OpenAI 不可用時）"""
        return (
            f"根據您的愛車資料分析，車齡{car_age}年，"
            f"我們為您推薦「{package_name}」，為您量身打造最適合的保障組合。"
        )


openai_service = OpenAIService()
