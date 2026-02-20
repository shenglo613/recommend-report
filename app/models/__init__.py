from app.models.request import (
    CarDetails,
    Profile,
    AnalysisQA,
    InsuranceRecommendRequest,
)
from app.models.response import (
    RadarData,
    AnalysisResults,
    CompulsoryInsurance,
    InsuranceItem,
    PriceSummary,
    AdjustableItem,
    RecommendedPlan,
    CustomPlan,
    Plans,
    AIProposal,
    InsuranceRecommendResponse,
)
from app.models.error import (
    ErrorDetail,
    ErrorInfo,
    ErrorResponse,
)

__all__ = [
    # Request
    "CarDetails",
    "Profile",
    "AnalysisQA",
    "InsuranceRecommendRequest",
    # Response
    "RadarData",
    "AnalysisResults",
    "CompulsoryInsurance",
    "InsuranceItem",
    "PriceSummary",
    "AdjustableItem",
    "RecommendedPlan",
    "CustomPlan",
    "Plans",
    "AIProposal",
    "InsuranceRecommendResponse",
    # Error
    "ErrorDetail",
    "ErrorInfo",
    "ErrorResponse",
]
