import logging
from typing import List

from openai import AsyncOpenAI, APIError, APIConnectionError, RateLimitError

from app.config import settings

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
                "你是一位專業的汽車保險顧問，請根據以下客戶資料，"
                "用 100~150 字的繁體中文生成一段推薦理由。\n\n"
                "## 寫作規範\n"
                "- 語氣親切自然，像朋友般給建議，不要過度正式或諂媚\n"
                "- 內容必須前後一致，不可出現矛盾（例如車齡 4 年不能說「新車」也不能說「老車」）\n"
                "- 車齡分類參考：≤3 年為新車、4~5 年為準新車、6~10 年為中古車、>10 年為老車\n"
                "- 根據車齡與套餐層級，說明為何這個保障組合適合客戶\n"
                "- 不要使用「尊敬的客戶」等過度客套的稱呼，直接以「您」稱呼即可\n"
                "- 不要逐一列舉險種名稱，而是用概括性語言描述保障重點\n\n"
                "## 客戶資料\n"
                f"- 客戶特徵：{', '.join(persona_tags)}\n"
                f"- 套餐層級：{package_name}\n"
                f"- 車齡：{car_age} 年\n\n"
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

    async def generate_economy_commentary(
        self,
        diff_data: dict,
        package_name: str,
        car_age: int,
    ) -> str:
        """
        呼叫 OpenAI 生成小資方案差異點評（混合模式）

        Args:
            diff_data: compute_plan_diff 產出的差異資料
            package_name: 套餐中文名稱
            car_age: 車齡

        Returns:
            AI 生成的差異文案（80~150 字）
        """
        if not diff_data["changes"]:
            return "小資方案與推薦方案內容相同，已是最精簡的保障組合。"

        if not self.client:
            logger.warning("OpenAI API Key not configured, using default economy commentary")
            return self._get_default_economy_commentary(diff_data)

        changes_text = "\n".join(
            f"- {c['name']}：{c['recommended']} → {c['economy']}（省 ${c['premium_diff']}）"
            for c in diff_data["changes"]
        )

        try:
            prompt = (
                "你是一位專業的汽車保險顧問，請根據以下「小資方案」相較於「推薦方案」的差異，"
                "用 80~150 字的繁體中文概述差異重點與省下的費用。\n\n"
                "## 寫作規範\n"
                "- 語氣親切，用簡潔的方式說明哪些保障降低或移除\n"
                "- 必須提到省下的總金額\n"
                "- 不要逐一列舉所有變更，挑重點說明\n"
                "- 結尾可簡短提醒取捨\n\n"
                "## 差異資料\n"
                f"- 套餐層級：{package_name}\n"
                f"- 車齡：{car_age} 年\n"
                f"- 總共省下：${diff_data['total_savings']}\n"
                f"- 變更項目：\n{changes_text}\n\n"
                "請直接輸出點評，不要加引號或前綴。"
            )

            response = await self.client.chat.completions.create(
                model=settings.openai_model,
                messages=[{"role": "user", "content": prompt}],
                max_tokens=300,
                temperature=0.7,
            )
            return response.choices[0].message.content.strip()

        except RateLimitError as e:
            logger.warning(f"OpenAI rate limit exceeded: {e}")
            return self._get_default_economy_commentary(diff_data)
        except APIConnectionError as e:
            logger.error(f"OpenAI connection error: {e}")
            return self._get_default_economy_commentary(diff_data)
        except APIError as e:
            logger.error(f"OpenAI API error: {e}")
            return self._get_default_economy_commentary(diff_data)
        except Exception as e:
            logger.error(f"Unexpected error calling OpenAI: {e}", exc_info=True)
            return self._get_default_economy_commentary(diff_data)

    @staticmethod
    def _get_default_economy_commentary(diff_data: dict) -> str:
        """預設小資方案點評（當 OpenAI 不可用時）"""
        savings = diff_data["total_savings"]
        count = len(diff_data["changes"])
        return (
            f"小資方案調整了 {count} 項險種保障等級，"
            f"為您省下約 ${savings:,} 元，"
            "在預算與保障之間取得平衡。"
        )

    @staticmethod
    def _get_default_commentary(package_name: str, car_age: int) -> str:
        """預設文案（當 OpenAI 不可用時）"""
        return (
            f"根據您的愛車資料分析，車齡{car_age}年，"
            f"我們為您推薦「{package_name}」，為您量身打造最適合的保障組合。"
        )


openai_service = OpenAIService()
