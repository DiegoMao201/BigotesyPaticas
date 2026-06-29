"""Schemas Pydantic v2 — catalog."""
from __future__ import annotations

import uuid
from datetime import datetime
from decimal import Decimal

from pydantic import BaseModel, ConfigDict, Field, model_validator


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
    # Filtros de catálogo (columnas directas, no JSONB)
    life_stage: str | None = None
    size_range: str | None = None
    pet_type: str | None = None
    brand_normalized: str | None = None
    health_concerns: list[str] | None = None


class ProductCreate(ProductBase):
    supplier_id: uuid.UUID | None = None


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
    supplier_id: uuid.UUID | None = None
    # Filtros de catálogo
    life_stage: str | None = None
    size_range: str | None = None
    pet_type: str | None = None
    brand_normalized: str | None = None
    health_concerns: list[str] | None = None


class RecentReviewOut(BaseModel):
    id: uuid.UUID
    rating: int
    title: str | None
    comment: str | None
    reviewer_name: str
    photo_urls: list[str]
    helpful_count: int
    created_at: datetime


class ProductOut(ProductBase):
    model_config = ConfigDict(from_attributes=True)
    id: uuid.UUID
    slug: str
    brand: BrandOut | None = None
    category: CategoryOut | None = None
    supplier_id: uuid.UUID | None = None
    supplier_name: str | None = None
    stock_qty: int = 0
    in_stock: bool = True
    image_url: str | None = None  # alias de primary_image_url para portal/store
    enriched_content: dict | None = None
    enriched_at: datetime | None = None
    enriched_model: str | None = None
    rating_avg: float | None = None
    rating_count: int = 0
    rating_distribution: dict | None = None
    recent_reviews: list[RecentReviewOut] = []

    @model_validator(mode="after")
    def _sync_image_url(self) -> "ProductOut":
        if self.image_url is None:
            self.image_url = self.primary_image_url
        return self


class ProductListResponse(BaseModel):
    items: list[ProductOut]
    total: int
    page: int
    per_page: int
    pages: int
