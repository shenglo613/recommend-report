from typing import List
from pydantic import BaseModel, Field


class RadarData(BaseModel):
    """雷達圖數據"""
    others_liability: int = Field(..., description="他人責任權重")
    own_vehicle: int = Field(..., description="自身車體權重")
    passenger_protection: int = Field(..., description="乘客保障權重")


class AnalysisResults(BaseModel):
    """分析結果"""
    persona_tags: List[str] = Field(..., description="用戶特徵標籤")
    radar_data: RadarData


class CoverageOption(BaseModel):
    """險種選項（自訂方案用）"""
    coverage: str = Field(..., description="險種名稱")
    amount: str = Field(..., description="保額")
    premium: int = Field(..., description="保費")


class RecommendedPlan(BaseModel):
    """推薦方案"""
    name: str
    total: int
    items: List[str]


class CustomPlan(BaseModel):
    """自訂方案"""
    name: str
    options: List[CoverageOption]


class Plans(BaseModel):
    """三種方案"""
    recommended: RecommendedPlan
    economy: RecommendedPlan
    custom: CustomPlan


class PriceSummary(BaseModel):
    """價格摘要"""
    original_total: int
    discount: int
    final_amount: int


class AIProposal(BaseModel):
    """AI 推薦報告"""
    commentary: str = Field(..., description="AI 推薦文案")
    plans: Plans
    price_summary: PriceSummary


class InsuranceRecommendResponse(BaseModel):
    """保險推薦 API Response"""
    status: str
    user_id: str
    analysis_results: AnalysisResults
    ai_proposal: AIProposal
