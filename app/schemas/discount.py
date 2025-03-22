from enum import Enum
from typing import Optional

from pydantic import BaseModel


class DiscountType(str, Enum):
    percentage = "percentage"
    fixed = "fixed"


class DiscountBase(BaseModel):
    name: str
    description: Optional[str] = None
    discount_type: DiscountType  # Now constrained to the enum values
    value: float
    min_purchase: Optional[float] = None


class DiscountCreate(DiscountBase):
    active: bool = True


class DiscountUpdate(BaseModel):
    name: Optional[str]
    description: Optional[str]
    discount_type: Optional[DiscountType]
    value: Optional[float]
    min_purchase: Optional[float]
    active: Optional[bool]


class DiscountResponse(DiscountBase):
    id: int
    active: bool

    class Config:
        orm_mode = True
