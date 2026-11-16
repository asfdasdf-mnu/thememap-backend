from pydantic import BaseModel

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
