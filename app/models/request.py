from pydantic import BaseModel, Field


class CarDetails(BaseModel):
    """車籍詳細資料"""
    vehicle_type: str = Field(..., description="車輛型式")
    color: str = Field(..., description="顏色")
    car_year: int = Field(..., description="出廠年份")
    compulsory_expiry: str = Field(..., description="強制險到期日")
    voluntary_expiry: str = Field(..., description="任意險到期日")
    engine_number: str = Field(..., description="引擎序號")
    displacement: int = Field(..., description="排氣量")


class Profile(BaseModel):
    """用戶基本資料"""
    id_number: str = Field(..., description="身分證字號")
    name: str = Field(..., description="姓名")
    license_plate: str = Field(..., description="車牌號碼")
    birth_date: str = Field(..., description="西元出生年月日")
    car_details: CarDetails


class AnalysisQA(BaseModel):
    """畫像問卷"""
    parking: str = Field(..., description="停車環境: indoor/outdoor")
    passenger: str = Field(..., description="載客頻率: high/low/none")
    usage: str = Field(..., description="用途: daily/holiday")


class InsuranceRecommendRequest(BaseModel):
    """保險推薦 API Request"""
    profile: Profile
    analysis_qa: AnalysisQA
