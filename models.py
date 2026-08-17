from dataclasses import dataclass, field
from datetime import datetime


@dataclass
class Report:
    url: str
    title: str
    pub_date: datetime
    category: str
    raw_text: str


@dataclass
class Indicator:
    report_url: str
    name: str
    value: float
    unit: str
    mom_change: float | None = None
    yoy_change: float | None = None


@dataclass
class Analysis:
    report_url: str
    kind: str  # "single" or "cross"
    content_json: str
    created_at: datetime = field(default_factory=lambda: datetime.now())
