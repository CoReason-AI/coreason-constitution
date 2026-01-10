from enum import Enum
from typing import List, Optional

from pydantic import BaseModel, Field


class LawCategory(str, Enum):
    UNIVERSAL = "Universal"
    DOMAIN = "Domain"
    TENANT = "Tenant"


class LawSeverity(str, Enum):
    LOW = "Low"
    MEDIUM = "Medium"
    HIGH = "High"
    CRITICAL = "Critical"


class Law(BaseModel):
    id: str = Field(..., min_length=1, description="Unique identifier for the law (e.g., 'GCP.1')")
    category: LawCategory = Field(..., description="Category of the law")
    text: str = Field(..., min_length=1, description="The actual text of the law/principle")
    severity: LawSeverity = Field(default=LawSeverity.MEDIUM, description="Severity of violation")
    tags: List[str] = Field(default_factory=list, description="Tags for classification")
    source: Optional[str] = Field(default=None, description="Source reference (e.g., 'FDA 21 CFR')")


class Constitution(BaseModel):
    version: str = Field(..., description="Version of this constitution set")
    laws: List[Law] = Field(default_factory=list, description="List of laws")
