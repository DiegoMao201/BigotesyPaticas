"""Schemas Pydantic v2 — catalog."""
from __future__ import annotations

import uuid
from decimal import Decimal

from pydantic import BaseModel, ConfigDict, Field


class BrandOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: uuid.UUID
    name: str
    slug: str
    logo_url: str | None = None
    is_active: bool


class CategoryOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: uuid.UUID
    name: str
    slug: str
    description: str | None = None
    image_url: str | None = None
    parent_id: uuid.UUID | None = None
    sort_order: int = 0
    is_active: bool


class ProductBase(BaseModel):
    sku: str = Field(min_length=1, max_length=64)
    name: str = Field(min_length=1, max_length=255)
    short_description: str | None = None
    description: str | None = None
    brand_id: uuid.UUID | None = None
    category_id: uuid.UUID | None = None
    cost: Decimal = Decimal("0")
    price: Decimal = Decimal("0")
    compare_at_price: Decimal | None = None
    margin_pct: Decimal = Decimal("0.20")
    is_active: bool = True
    is_featured: bool = False
    is_published: bool = False
    primary_image_url: str | None = None
    images: list[str] = []
    seo_title: str | None = None
    seo_description: str | None = None
    attributes: dict = {}
    tags: list[str] = []


class ProductCreate(ProductBase):
    pass


class ProductUpdate(BaseModel):
    name: str | None = None
    short_description: str | None = None
    description: str | None = None
    brand_id: uuid.UUID | None = None
    category_id: uuid.UUID | None = None
    cost: Decimal | None = None
    price: Decimal | None = None
    compare_at_price: Decimal | None = None
    margin_pct: Decimal | None = None
    is_active: bool | None = None
    is_featured: bool | None = None
    is_published: bool | None = None
    primary_image_url: str | None = None
    images: list[str] | None = None
    attributes: dict | None = None
    tags: list[str] | None = None


class ProductOut(ProductBase):
    model_config = ConfigDict(from_attributes=True)
    id: uuid.UUID
    slug: str
    brand: BrandOut | None = None
    category: CategoryOut | None = None


class ProductListResponse(BaseModel):
    items: list[ProductOut]
    total: int
    page: int
    per_page: int
    pages: int
