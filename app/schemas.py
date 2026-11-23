from typing import Annotated
from pydantic import BaseModel, ConfigDict, Field, HttpUrl, StringConstraints, model_validator

Name = Annotated[str, StringConstraints(strip_whitespace=True, min_length=1, max_length=100)]
Content = Annotated[str, StringConstraints(strip_whitespace=True, min_length=1, max_length=10000)]

class AdminInput(BaseModel):
    model_config = ConfigDict(extra='forbid')

class ThemeWrite(AdminInput):
    name: Name
    description: Annotated[str, StringConstraints(max_length=10000)] = ''

class StockWrite(ThemeWrite):
    market: Annotated[str, StringConstraints(strip_whitespace=True, min_length=1, max_length=20)]

class StockCreate(StockWrite):
    code: str = Field(pattern=r'^[0-9A-Z]{6}$')

class EvidenceWrite(AdminInput):
    reason: Content
    source_title: Annotated[str, StringConstraints(strip_whitespace=True, min_length=1, max_length=200)]
    source_url: HttpUrl | None = None
    is_sample: bool = True

    @model_validator(mode='after')
    def require_source(self):
        if not self.is_sample and self.source_url is None:
            raise ValueError('실데이터 근거에는 출처 URL이 필요합니다.')
        return self

class ThemeOut(BaseModel):
    id: int
    name: str
    description: str
    stock_count: int

class ThemeList(BaseModel):
    items: list[ThemeOut]
    total: int
    limit: int
    offset: int

class Evidence(BaseModel):
    reason: str
    source_title: str
    source_url: str | None
    is_sample: bool

class StockOut(BaseModel):
    code: str
    name: str
    market: str
    description: str

class RelatedStock(StockOut, Evidence):
    pass

class RelatedTheme(Evidence):
    id: int
    name: str

class ThemeStocks(BaseModel):
    theme: ThemeOut
    items: list[RelatedStock]

class StockDetail(StockOut):
    themes: list[RelatedTheme]
