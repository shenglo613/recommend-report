from datetime import datetime
from typing import Tuple, Dict, List

from app.constants.insurance_rates import (
    INSURANCE_RATES,
    COVERAGE_AMOUNTS,
    RADAR_CONFIGS,
    PACKAGE_NAMES,
)
from app.exceptions import CarDataException, InsuranceCalculationException
from app.models import (
    CoverageOption,
    RecommendedPlan,
    CustomPlan,
    Plans,
)


class InsuranceService:
    """保險推薦業務邏輯"""

    @staticmethod
    def calculate_car_age(car_year: int) -> int:
        """計算車齡"""
        current_year = datetime.now().year
        car_age = current_year - car_year

        # 驗證車齡合理性
        if car_age < 0:
            raise CarDataException(f"出廠年份 {car_year} 不合理，不可大於當前年份 {current_year}")
        if car_age > 50:
            raise CarDataException(f"車齡 {car_age} 年超過合理範圍，請確認出廠年份是否正確")

        return car_age

    @staticmethod
    def determine_package(car_age: int) -> Tuple[str, Dict[str, int]]:
        """
        根據車齡決定套餐等級和險種代碼組合

        規則:
        - ≤5年: 豪華套餐
        - 5-10年: 進階套餐
        - >10年: 基本套餐
        - ≤3年: 額外含竊盜險
        """
        if car_age <= 5:
            # 豪華套餐: A3 B3 C3 D3 E2 F3 G3 H1(若≤3年) I3 J3 K3
            package_type = "deluxe"
            codes = {
                "A": 3, "B": 3, "C": 3, "D": 3,
                "E": 2, "F": 3, "G": 3,
                "I": 3, "J": 3, "K": 3
            }
            if car_age <= 3:
                codes["H"] = 1  # 3年內含竊盜險
            else:
                codes["H"] = 2  # 超過3年不含
        elif car_age <= 10:
            # 進階套餐: A3 B3 C3 D3 E3 F3 G3
            package_type = "advanced"
            codes = {
                "A": 3, "B": 3, "C": 3, "D": 3,
                "E": 3, "F": 3, "G": 3
            }
        else:
            # 基本套餐: A3 B3 C3 D3
            package_type = "basic"
            codes = {"A": 3, "B": 3, "C": 3, "D": 3}

        return package_type, codes

    @staticmethod
    def calculate_premium(insurance_codes: Dict[str, int]) -> Dict:
        """計算保費"""
        items = []
        total = 0

        for code, option in insurance_codes.items():
            # 驗證險種代碼
            if code not in INSURANCE_RATES:
                raise InsuranceCalculationException(f"無效的險種代碼: {code}")

            rate = INSURANCE_RATES[code]

            # 驗證保額選項
            if option not in rate["options"]:
                valid_options = list(rate["options"].keys())
                raise InsuranceCalculationException(
                    f"險種 {code} ({rate['name']}) 的保額選項 {option} 無效，"
                    f"有效選項為: {valid_options}"
                )

            premium = rate["options"].get(option, 0)
            amount = COVERAGE_AMOUNTS[code].get(option, "")

            if premium > 0:
                items.append({
                    "code": code,
                    "name": rate["name"],
                    "amount": amount,
                    "premium": premium
                })
                total += premium

        if total == 0:
            raise InsuranceCalculationException("計算結果異常：總保費為 0")

        return {
            "items": items,
            "total": total,
            "discount": int(total * 0.1)  # 預設9折優惠
        }

    @staticmethod
    def generate_radar_data(package_type: str) -> Dict[str, int]:
        """根據套餐類型生成雷達圖數據"""
        return RADAR_CONFIGS.get(package_type, RADAR_CONFIGS["basic"])

    @staticmethod
    def generate_persona_tags(car_age: int, package_type: str) -> List[str]:
        """生成用戶標籤"""
        tags = []

        if car_age <= 3:
            tags.append("新車車主")
        elif car_age <= 5:
            tags.append("準新車車主")
        elif car_age <= 10:
            tags.append("中古車車主")
        else:
            tags.append("老車車主")

        package_tag = {
            "deluxe": "適合豪華保障",
            "advanced": "適合進階保障",
            "basic": "適合基本保障"
        }
        tags.append(package_tag.get(package_type, ""))

        return tags

    @staticmethod
    def build_plans(premium_details: Dict) -> Plans:
        """組裝三種方案"""
        # 推薦方案（完整套餐）
        recommended_items = [
            f"{item['name']}-{item['amount']}"
            for item in premium_details['items']
        ]
        recommended = RecommendedPlan(
            name="AI 推薦首選",
            total=premium_details['total'] - premium_details.get('discount', 0),
            items=recommended_items
        )

        # 小資方案（只有基本險種 A, B, C, D）
        basic_codes = {"A": 3, "B": 2, "C": 2, "D": 2}
        basic_premium = InsuranceService.calculate_premium(basic_codes)
        economy_items = [
            f"{item['name']}-{item['amount']}"
            for item in basic_premium['items']
        ]
        economy = RecommendedPlan(
            name="小資基礎選",
            total=basic_premium['total'],
            items=economy_items
        )

        # 自訂方案（列出所有可調整選項）
        custom_options = []
        for code, rate in INSURANCE_RATES.items():
            default_option = 3 if 3 in rate["options"] else 1
            custom_options.append(CoverageOption(
                coverage=rate["name"],
                amount=COVERAGE_AMOUNTS[code].get(default_option, ""),
                premium=rate["options"].get(default_option, 0)
            ))

        custom = CustomPlan(
            name="自訂調整",
            options=custom_options
        )

        return Plans(recommended=recommended, economy=economy, custom=custom)

    @staticmethod
    def get_package_name(package_type: str) -> str:
        """取得套餐中文名稱"""
        return PACKAGE_NAMES.get(package_type, package_type)
