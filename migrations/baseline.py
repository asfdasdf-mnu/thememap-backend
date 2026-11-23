"""Frozen 0001 metadata, used only to verify legacy adoption."""
from sqlalchemy import Boolean, CheckConstraint, ForeignKey, String, Text
from sqlalchemy.orm import Mapped, mapped_column
from sqlalchemy.orm import DeclarativeBase

class Base(DeclarativeBase):
    pass

class Theme(Base):
    __tablename__ = 'themes'
    id: Mapped[int] = mapped_column(primary_key=True)
    name: Mapped[str] = mapped_column(String(100), unique=True)
    description: Mapped[str] = mapped_column(Text)

class Stock(Base):
    __tablename__ = 'stocks'
    __table_args__ = (CheckConstraint('length(code) = 6', name='stock_code_length'),)
    code: Mapped[str] = mapped_column(String(6), primary_key=True)
    name: Mapped[str] = mapped_column(String(100))
    market: Mapped[str] = mapped_column(String(20))
    description: Mapped[str] = mapped_column(Text)

class ThemeStock(Base):
    __tablename__ = 'theme_stocks'
    theme_id: Mapped[int] = mapped_column(ForeignKey('themes.id', ondelete='CASCADE'), primary_key=True)
    stock_code: Mapped[str] = mapped_column(ForeignKey('stocks.code', ondelete='CASCADE'), primary_key=True)
    reason: Mapped[str] = mapped_column(Text)
    source_title: Mapped[str] = mapped_column(String(200))
    source_url: Mapped[str | None] = mapped_column(Text, nullable=True)
    is_sample: Mapped[bool] = mapped_column(Boolean, default=True)
