from typing import Optional
from pydantic import BaseModel, Field


class CarDetails(BaseModel):
    """車籍詳細資料"""
    vehicle_type: str = Field(..., description="車輛型式")
    color: str = Field(..., description="顏色")
    registration_year: int = Field(..., description="領牌年份")
    compulsory_expiry: str = Field(..., description="強制險到期日")
    voluntary_expiry: str = Field(..., description="任意險到期日")
    engine_number: str = Field(..., description="引擎序號")
    displacement: int = Field(..., description="排氣量 (cc)")


class Profile(BaseModel):
    """用戶基本資料"""
    id_number: str = Field(..., description="身分證字號")
    name: str = Field(..., description="姓名")
    license_plate: str = Field(..., description="車牌號碼")
    birth_date: str = Field(..., description="西元出生年月日")
    car_details: CarDetails


class AnalysisQA(BaseModel):
    """五大維度生活化問卷（每類單選，皆為 Optional）"""
    passenger_preference: Optional[str] = Field(
        None, description="車內人安全感: high_passenger_medical|high_driver_disability|basic_passenger|high_driver_medical"
    )
    vehicle_protection: Optional[str] = Field(
        None, description="本車愛護程度: repair_perfectionist|waive_subrogation|theft_protection|basic_repair"
    )
    liability_concern: Optional[str] = Field(
        None, description="車外人責任心: high_excess_liability|high_bodily_injury|statutory_minimum|high_property_damage"
    )
    service_needs: Optional[str] = Field(
        None, description="費用服務應援: roadside_assistance_100km|legal_expense|consolation_money|basic_roadside"
    )
    budget_profile: Optional[str] = Field(
        None, description="預算與性格: safety_first|best_value|budget_saver|ai_balanced"
    )


class InsuranceRecommendRequest(BaseModel):
    """保險推薦 API Request"""
    profile: Profile
    analysis_qa: Optional[AnalysisQA] = Field(None, description="問卷結果（可選，未傳時回傳 Default 定錨）")
    target_amount: Optional[int] = Field(None, description="預算滑桿目標金額（可選，觸發減分優先序號）")