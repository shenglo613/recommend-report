import random
from datetime import datetime
from typing import Dict, List, Optional

from app.constants.insurance_rates import (
    INSURANCE_RATES,
    COVERAGE_AMOUNTS,
    MAX_INDEX,
    MAX_VOLUNTARY_PREMIUM,
    COMPULSORY_RATES,
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

        # 第一類：車內人安全感（影響 C 乘客、D 駕駛）
        if qa.passenger_preference == "high_passenger_medical":
            self.indices["C"] += 1
        elif qa.passenger_preference == "high_driver_disability":
            self.indices["D"] += 1
        elif qa.passenger_preference == "basic_passenger":
            self.indices["C"] -= 2
        elif qa.passenger_preference == "high_driver_medical":
            self.indices["D"] += 1

        # 第二類：本車愛護程度（影響 E 車體、F 免追償、H 竊盜）
        if qa.vehicle_protection == "repair_perfectionist":
            self.indices["E"] -= 1  # E 反向：升級（例如丙升乙）
        elif qa.vehicle_protection == "waive_subrogation":
            self.indices["F"] = 3   # 解鎖免追償
        elif qa.vehicle_protection == "theft_protection":
            self.indices["H"] = 1   # 解鎖竊盜險
        elif qa.vehicle_protection == "basic_repair":
            self.indices["E"] += 2  # E 反向：降級或移除

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

        # 第四類：費用/服務應援（影響 G 救援、I 刑事、J 慰問金）
        if qa.service_needs == "roadside_assistance_100km":
            self.indices["G"] = 4   # 定錨 4
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
            if v < 0:
                self.indices[k] = 0
            elif v > 0:
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
        return {
            "compulsory": compulsory,
            "voluntary": voluntary,
            "subtotal": subtotal,
            "final_amount": subtotal,
        }

    def calculate_radar(self, indices: Optional[Dict[str, int]] = None) -> dict:
        """
        動態計算雷達圖五維分數（70-95 範圍）

        Args:
            indices: 外部險種序號 dict，預設使用 self.indices
        """
        idx = indices or self.indices

        def normalize(code: str, index: int) -> float:
            if index <= 0:
                return 0.0
            max_val = MAX_INDEX[code]
            if max_val <= 1:
                return 100.0 if index >= 1 else 0.0
            if code in ("E", "H"):
                return (max_val - index) / (max_val - 1) * 100
            return (index - 1) / (max_val - 1) * 100

        def to_visual(raw_0_100: float) -> int:
            """映射 0-100 → 70-95，加 ±2 隨機抖動"""
            base = round(70 + (raw_0_100 / 100) * 25)
            jitter = random.randint(-2, 2)
            return max(70, min(95, base + jitter))

        # passenger_preference: C, D（兩者 normalized 取平均）
        passenger_raw = (normalize("C", idx["C"]) + normalize("D", idx["D"])) / 2

        # vehicle_protection: E, F, H（加權平均，H 權重較低因多數人不保）
        vehicle_weights = {"E": 1.0, "F": 1.0, "H": 0.3}
        vehicle_pairs = [
            (normalize(c, idx[c]), vehicle_weights[c])
            for c in ["E", "F", "H"] if idx.get(c, 0) > 0
        ]
        vehicle_raw = (
            sum(v * w for v, w in vehicle_pairs) / sum(w for _, w in vehicle_pairs)
            if vehicle_pairs else 0.0
        )

        # liability_concern: A, B 必算，K 啟用時加入
        liability_vals = [normalize("A", idx["A"]), normalize("B", idx["B"])]
        if idx.get("K", 0) > 0:
            liability_vals.append(normalize("K", idx["K"]))
        liability_raw = sum(liability_vals) / len(liability_vals)

        # service_needs: G, I, J（僅計算已啟用的險種取平均）
        service_vals = [normalize(c, idx[c]) for c in ["G", "I", "J"] if idx.get(c, 0) > 0]
        service_raw = sum(service_vals) / len(service_vals) if service_vals else 0.0

        # budget_profile: voluntary_premium / MAX_VOLUNTARY_PREMIUM
        voluntary = 0
        for k, v in idx.items():
            if v > 0:
                options = INSURANCE_RATES.get(k, {}).get("options", {})
                if v in options:
                    voluntary += options[v]
        budget_raw = min(voluntary / MAX_VOLUNTARY_PREMIUM * 100, 100.0)

        return {
            "passenger_preference": to_visual(passenger_raw),
            "vehicle_protection": to_visual(vehicle_raw),
            "liability_concern": to_visual(liability_raw),
            "service_needs": to_visual(service_raw),
            "budget_profile": to_visual(budget_raw),
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
                final_amount=subtotal,
            ),
            "economy_indices": economy_indices,
        }

    def compute_plan_diff(self, economy_indices: Dict[str, int]) -> dict:
        """計算推薦方案與小資方案的險種變化與保費差異"""
        changes = []
        for code in ["A", "B", "C", "D", "E", "F", "G", "H", "I", "J", "K"]:
            rec_idx = self.indices[code]
            eco_idx = economy_indices[code]
            if rec_idx == eco_idx:
                continue
            name = INSURANCE_RATES[code]["name"]
            rec_amount = COVERAGE_AMOUNTS.get(code, {}).get(rec_idx, "不保") if rec_idx > 0 else "不保"
            eco_amount = COVERAGE_AMOUNTS.get(code, {}).get(eco_idx, "不保") if eco_idx > 0 else "不保"
            rec_premium = INSURANCE_RATES[code]["options"].get(rec_idx, 0) if rec_idx > 0 else 0
            eco_premium = INSURANCE_RATES[code]["options"].get(eco_idx, 0) if eco_idx > 0 else 0
            changes.append({
                "code": code,
                "name": name,
                "recommended": rec_amount,
                "economy": eco_amount,
                "premium_diff": rec_premium - eco_premium,
            })

        rec_total = sum(
            INSURANCE_RATES[k]["options"].get(v, 0)
            for k, v in self.indices.items() if v > 0
        )
        eco_total = sum(
            INSURANCE_RATES[k]["options"].get(v, 0)
            for k, v in economy_indices.items() if v > 0
        )
        return {
            "changes": changes,
            "total_savings": rec_total - eco_total,
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
