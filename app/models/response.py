from typing import List, Optional
from pydantic import BaseModel, Field


class RadarData(BaseModel):
    """雷達圖數據（三維）"""
    others_liability: int = Field(..., description="他人責任 0-100")
    own_vehicle: int = Field(..., description="自身車體 0-100")
    passenger_protection: int = Field(..., description="乘客保障 0-100")


class AnalysisResults(BaseModel):
    """分析結果"""
    persona_tags: List[str] = Field(..., description="用戶特徵標籤")
    radar_data: RadarData
    insurance_code: str = Field(..., description="險種代碼字串，如 A3B4C3D3E2F3G4H1I3J3K3")


class CompulsoryInsurance(BaseModel):
    """強制險"""
    name: str = "強制汽車責任保險"
    premium: int = Field(..., description="強制險保費")
    note: str = "法規要求，不可取消"


class InsuranceItem(BaseModel):
    """單一險種明細"""
    code: str = Field(..., description="險種代碼 A-K")
    name: str = Field(..., description="險種名稱")
    index: int = Field(..., description="保額組合序號")
    amount: str = Field(..., description="保額描述")
    premium: int = Field(..., description="保費")


class PriceSummary(BaseModel):
    """價格摘要"""
    compulsory: int = Field(..., description="強制險保費")
    voluntary: int = Field(..., description="任意險保費小計")
    subtotal: int = Field(..., description="總計")
    discount: int = Field(..., description="折扣金額")
    final_amount: int = Field(..., description="應繳保費")


class AdjustableItem(BaseModel):
    """可調整險種（自訂方案用）"""
    code: str
    name: str
    current_index: int
    min: int
    max: int


class RecommendedPlan(BaseModel):
    """推薦方案 / 小資方案"""
    name: str
    insurance_code: str
    items: List[InsuranceItem]
    price_summary: PriceSummary


class CustomPlan(BaseModel):
    """自訂調整方案"""
    name: str = "自訂調整"
    base_code: str
    adjustable_items: List[AdjustableItem]


class Plans(BaseModel):
    """三種方案"""
    recommended: RecommendedPlan
    economy: RecommendedPlan
    custom: CustomPlan


class AIProposal(BaseModel):
    """AI 推薦報告"""
    commentary: str = Field(..., description="AI 推薦文案（OpenAI 生成）")
    plans: Plans


class InsuranceRecommendResponse(BaseModel):
    """保險推薦 API Response"""
    status: str = "success"
    user_id: str
    analysis_results: AnalysisResults
    compulsory_insurance: CompulsoryInsurance
    ai_proposal: AIProposal
