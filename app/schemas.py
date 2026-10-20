from datetime import UTC, datetime, timedelta

from pydantic import BaseModel, ConfigDict, Field, model_validator

from app.db import utc_iso
from app.errors import DomainError
from app.services.aggregations import GroupBy

DEFAULT_RANGE_DAYS = 30


class ReportQuery(BaseModel):
    model_config = ConfigDict(populate_by_name=True)

    from_: datetime | None = Field(default=None, alias='from')
    to: datetime | None = None
    seller_id: str | None = Field(default=None, alias='sellerId', min_length=1)

    @model_validator(mode='after')
    def fill_range(self) -> 'ReportQuery':
        # Sem datas: últimos 30 dias até agora. Datas sem fuso são tratadas como UTC
        self.to = _as_utc(self.to) or datetime.now(UTC)
        self.from_ = _as_utc(self.from_) or self.to - timedelta(days=DEFAULT_RANGE_DAYS)
        if self.from_ >= self.to:
            raise DomainError('report.invalid_range', 422)
        return self

    @property
    def range_iso(self) -> tuple[str, str]:
        return utc_iso(self.from_), utc_iso(self.to)


class SalesQuery(ReportQuery):
    group_by: GroupBy = Field(default='day', alias='groupBy')


class TopProductsQuery(ReportQuery):
    limit: int = Field(default=10, ge=1, le=100)


def _as_utc(value: datetime | None) -> datetime | None:
    if value is None:
        return None
    return value.replace(tzinfo=UTC) if value.tzinfo is None else value.astimezone(UTC)
