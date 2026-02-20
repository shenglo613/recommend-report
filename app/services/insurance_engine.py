from datetime import datetime
from typing import Dict, List, Optional

from app.constants.insurance_rates import (
    INSURANCE_RATES,
    COVERAGE_AMOUNTS,
    MAX_INDEX,
    COMPULSORY_RATES,
    DISCOUNT_RATE,
    PACKAGE_NAMES,
    REDUCE_PRIORITY,
    PERSONA_TAG_MAP,
)
from app.exceptions import CarDataMismatchException
from app.models.request import AnalysisQA
from app.models.response import (
    InsuranceItem,
    PriceSummary,
    AdjustableItem,
)


class InsuranceEngine:
    """
    保險推薦核心演算法引擎（PRD v2.0）

    兩層決策架構：
    1. 車齡自動定錨 (apply_initial_anchoring)
    2. 問卷位移微調 (apply_questionnaire)
    + 邊界檢查 (finalize)
    + 減分優先序號 (reduce_premium)
    """

    def __init__(self, registration_year: int, displacement: int):
        current_year = datetime.now().year
        self.car_age = current_year - registration_year
        self.displacement = displacement
        self.package = ""

        # 驗證車齡
        if self.car_age < 0:
            raise CarDataMismatchException(
                f"領牌年份 {registration_year} 不合理，不可大於當前年份 {current_year}"
            )
        if self.car_age > 50:
            raise CarDataMismatchException(
                f"車齡 {self.car_age} 年超過合理範圍，請確認領牌年份是否正確"
            )

        # 所有險種預設序號：0 = 未啟用
        self.indices: Dict[str, int] = {
            "A": 3, "B": 3, "C": 3, "D": 3,
            "E": 0, "F": 0, "G": 0, "H": 0,
            "I": 0, "J": 0, "K": 0,
        }

        self.apply_initial_anchoring()

    def apply_initial_anchoring(self):
        """第一層：車齡與套餐定錨（PRD 第 4、5 章）"""
        if self.car_age <= 5:
            self.package = "deluxe"
            self.indices.update({
                "E": 2,   # 車齡 ≤5 年：乙式（車齡規則覆蓋）
                "F": 3, "G": 3,
                "I": 3, "J": 3, "K": 3,
            })
            if self.car_age <= 3:
                self.indices["H"] = 1  # 車齡 ≤3 年：竊盜險加保
        elif self.car_age <= 10:
            self.package = "advanced"
            self.indices.update({
                "E": 3,   # 車齡 6-10 年：丙式
                "F": 3, "G": 3,
            })
        else:
            self.package = "basic"
            self.indices["E"] = 5  # 車齡 >10 年：不保（強制覆蓋）

    def apply_questionnaire(self, qa: AnalysisQA):
        """第二層：問卷位移邏輯（PRD 第 8 章，每類單選）"""

        # 第一類：車內人安全感
        if qa.passenger_preference == "high_passenger_medical":
            self.indices["C"] += 1
        elif qa.passenger_preference == "high_driver_disability":
            self.indices["D"] += 1
        elif qa.passenger_preference == "basic_passenger":
            self.indices["C"] -= 2
        elif qa.passenger_preference == "high_driver_medical":
            self.indices["D"] += 1

        # 第二類：本車愛護程度
        if qa.vehicle_protection == "repair_perfectionist":
            self.indices["E"] -= 1  # E 反向：升級
        elif qa.vehicle_protection == "waive_subrogation":
            self.indices["F"] = 3   # 解鎖
        elif qa.vehicle_protection == "theft_protection":
            self.indices["H"] = 1   # 解鎖
        elif qa.vehicle_protection == "basic_repair":
            self.indices["E"] += 2  # E 反向：降級

        # 第三類：車外人責任心
        if qa.liability_concern == "high_excess_liability":
            self.indices["B"] += 2
        elif qa.liability_concern == "high_bodily_injury":
            self.indices["K"] = 3   # 解鎖
        elif qa.liability_concern == "statutory_minimum":
            self.indices["A"] -= 1
            self.indices["B"] -= 1
        elif qa.liability_concern == "high_property_damage":
            self.indices["A"] += 1

        # 第四類：費用/服務應援
        if qa.service_needs == "roadside_assistance_100km":
            self.indices["G"] = 4   # 定錨 4
            self.indices["I"] = 3   # 交叉銷售
        elif qa.service_needs == "legal_expense":
            self.indices["I"] = 3   # 解鎖
        elif qa.service_needs == "consolation_money":
            self.indices["J"] = 3   # 解鎖
        elif qa.service_needs == "basic_roadside":
            self.indices["G"] -= 1

        # 第五類：全域預算與性格
        if qa.budget_profile == "safety_first":
            for k in self.indices:
                if self.indices[k] > 0:
                    if k == "E":
                        self.indices[k] -= 1  # E 反向：升級
                    else:
                        self.indices[k] += 1
        elif qa.budget_profile == "budget_saver":
            for k in self.indices:
                if self.indices[k] > 0:
                    if k == "E":
                        self.indices[k] = 4   # E 反向：限額丙式
                    else:
                        self.indices[k] = 1
        # best_value / ai_balanced → 不變

        self.finalize()

    def finalize(self):
        """邊界檢查：確保所有序號在合法範圍內（PRD 第 9.4 節）"""
        for k, v in self.indices.items():
            if v > 0:
                self.indices[k] = max(1, min(MAX_INDEX[k], v))

    def reduce_premium(self, target_amount: int):
        """依減分優先序號降級，直到保費 ≤ target_amount（PRD 第 10 章）"""
        for code in REDUCE_PRIORITY:
            while self.calculate_premium()["final_amount"] > target_amount:
                if self.indices[code] <= 0:
                    break
                if code == "E":
                    # E 反向：+1 = 降級
                    if self.indices[code] >= MAX_INDEX[code]:
                        break
                    self.indices[code] += 1
                elif code in ("F", "H"):
                    # 二元險種：直接移除
                    self.indices[code] = 0
                    break
                else:
                    # 一般險種：-1 = 降級
                    self.indices[code] -= 1
                    if self.indices[code] <= 0:
                        self.indices[code] = 0
                        break

            if self.calculate_premium()["final_amount"] <= target_amount:
                break

        self.finalize()

    def _get_compulsory_premium(self) -> int:
        """查詢強制險保費（依排氣量，PRD 第 7.1 節）"""
        for threshold, premium in COMPULSORY_RATES:
            if threshold is None or self.displacement <= threshold:
                return premium
        return COMPULSORY_RATES[-1][1]

    def calculate_premium(self) -> dict:
        """計算保費（PRD 第 7.3 節）"""
        compulsory = self._get_compulsory_premium()
        voluntary = 0
        for k, v in self.indices.items():
            if v > 0:
                options = INSURANCE_RATES.get(k, {}).get("options", {})
                if v in options:
                    voluntary += options[v]

        subtotal = compulsory + voluntary
        discount = int(subtotal * DISCOUNT_RATE)
        return {
            "compulsory": compulsory,
            "voluntary": voluntary,
            "subtotal": subtotal,
            "discount": discount,
            "final_amount": subtotal - discount,
        }

    def calculate_radar(self) -> dict:
        """動態計算雷達圖三維分數（PRD 第 12.3 節）"""
        def normalize(code: str, index: int) -> float:
            if index <= 0:
                return 0.0
            max_val = MAX_INDEX[code]
            if max_val <= 1:
                return 100.0 if index >= 1 else 0.0
            if code == "E":
                return (max_val - index) / (max_val - 1) * 100
            return (index - 1) / (max_val - 1) * 100

        # 他人責任 = A + B + K
        others = [normalize("A", self.indices["A"]), normalize("B", self.indices["B"])]
        if self.indices.get("K", 0) > 0:
            others.append(normalize("K", self.indices["K"]))
        others_liability = sum(others) / len(others)

        # 自身車體 = E + F + H
        vehicle = []
        for code in ["E", "F", "H"]:
            if self.indices.get(code, 0) > 0:
                vehicle.append(normalize(code, self.indices[code]))
        own_vehicle = sum(vehicle) / len(vehicle) if vehicle else 0.0

        # 乘客保障 = C + D
        passenger = [normalize("C", self.indices["C"]), normalize("D", self.indices["D"])]
        passenger_protection = sum(passenger) / len(passenger)

        return {
            "others_liability": round(others_liability),
            "own_vehicle": round(own_vehicle),
            "passenger_protection": round(passenger_protection),
        }

    def generate_insurance_code(self) -> str:
        """生成險種代碼字串，如 A3B4C3D3E2F3G4H1I3J3K3（PRD 第 14.1 節）"""
        parts = []
        for code in ["A", "B", "C", "D", "E", "F", "G", "H", "I", "J", "K"]:
            if self.indices[code] > 0:
                parts.append(f"{code}{self.indices[code]}")
        return "".join(parts)

    def build_items(self) -> List[InsuranceItem]:
        """建構當前狀態的險種明細列表"""
        items = []
        for code in ["A", "B", "C", "D", "E", "F", "G", "H", "I", "J", "K"]:
            idx = self.indices[code]
            if idx <= 0:
                continue
            rate = INSURANCE_RATES.get(code)
            if not rate:
                continue
            options = rate["options"]
            if idx not in options:
                continue
            items.append(InsuranceItem(
                code=code,
                name=rate["name"],
                index=idx,
                amount=COVERAGE_AMOUNTS.get(code, {}).get(idx, ""),
                premium=options[idx],
            ))
        return items

    def build_price_summary(self) -> PriceSummary:
        """建構價格摘要"""
        p = self.calculate_premium()
        return PriceSummary(**p)

    def build_economy_plan(self) -> dict:
        """建構小資方案：所有已啟用險種降至 1（E 降至 4）（PRD 第 12.2 節）"""
        economy_indices = {}
        for k, v in self.indices.items():
            if v > 0:
                if k == "E":
                    economy_indices[k] = 4  # E 反向：限額丙式
                else:
                    economy_indices[k] = 1
            else:
                economy_indices[k] = 0

        # 建構 items
        items = []
        for code in ["A", "B", "C", "D", "E", "F", "G", "H", "I", "J", "K"]:
            idx = economy_indices[code]
            if idx <= 0:
                continue
            rate = INSURANCE_RATES.get(code)
            if not rate:
                continue
            options = rate["options"]
            if idx not in options:
                continue
            items.append(InsuranceItem(
                code=code,
                name=rate["name"],
                index=idx,
                amount=COVERAGE_AMOUNTS.get(code, {}).get(idx, ""),
                premium=options[idx],
            ))

        # 計算保費
        compulsory = self._get_compulsory_premium()
        voluntary = sum(item.premium for item in items)
        subtotal = compulsory + voluntary
        discount = int(subtotal * DISCOUNT_RATE)

        # 生成 code
        parts = []
        for code in ["A", "B", "C", "D", "E", "F", "G", "H", "I", "J", "K"]:
            if economy_indices[code] > 0:
                parts.append(f"{code}{economy_indices[code]}")
        insurance_code = "".join(parts)

        return {
            "insurance_code": insurance_code,
            "items": items,
            "price_summary": PriceSummary(
                compulsory=compulsory,
                voluntary=voluntary,
                subtotal=subtotal,
                discount=discount,
                final_amount=subtotal - discount,
            ),
        }

    def build_custom_plan(self) -> List[AdjustableItem]:
        """建構自訂方案的可調整項目列表"""
        items = []
        for code in ["A", "B", "C", "D", "E", "F", "G", "H", "I", "J", "K"]:
            rate = INSURANCE_RATES.get(code)
            if not rate:
                continue
            # 核心險種 (A-D) min=1，其他可為 0（移除）
            min_val = 1 if code in ("A", "B", "C", "D") else 0
            items.append(AdjustableItem(
                code=code,
                name=rate["name"],
                current_index=self.indices[code],
                min=min_val,
                max=MAX_INDEX[code],
            ))
        return items

    def generate_persona_tags(self, qa: Optional[AnalysisQA] = None) -> List[str]:
        """生成用戶特徵標籤（PRD 第 12.4 節）"""
        tags = []

        # 車齡標籤
        if self.car_age <= 3:
            tags.append("新車車主")
        elif self.car_age <= 5:
            tags.append("準新車車主")
        elif self.car_age <= 10:
            tags.append("中古車車主")
        else:
            tags.append("老車車主")

        # 套餐標籤
        package_tag = {
            "deluxe": "適合豪華保障",
            "advanced": "適合進階保障",
            "basic": "適合基本保障",
        }
        tags.append(package_tag.get(self.package, ""))

        # 問卷特徵標籤
        if qa:
            for field_val in [
                qa.passenger_preference, qa.vehicle_protection,
                qa.liability_concern, qa.service_needs, qa.budget_profile,
            ]:
                if field_val and field_val in PERSONA_TAG_MAP:
                    tags.append(PERSONA_TAG_MAP[field_val])

        return [t for t in tags if t]

    def get_package_name(self) -> str:
        """取得套餐中文名稱"""
        return PACKAGE_NAMES.get(self.package, self.package)
