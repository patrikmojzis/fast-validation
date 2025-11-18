from __future__ import annotations

from typing import get_args

from pydantic import Field

from fast_validation import Schema, from_schema


class BaseProductSchema(Schema):
    name: str = Field(..., description="Product name.")
    price: int = Field(..., description="Price in cents.")
    quantity: int = Field(1, description="Available quantity.")

    class Meta:
        rules = [Schema.Rule("$.name", [])]
        tag = "base"


@from_schema(BaseProductSchema)
class ProductStoreSchema:
    pass


@from_schema(BaseProductSchema, partial=True)
class ProductUpdateSchema:
    pass


@from_schema(BaseProductSchema, partial=True)
class ProductUpdateWithOverride:
    price: int = Field(..., description="Price override.")


@from_schema(BaseProductSchema)
class ProductWithExtraField:
    sku: str


@from_schema(BaseProductSchema)
class ProductCustomRules:
    class Meta:
        rules = [Schema.Rule("$.price", [])]


def test_from_schema_inherits_fields_and_meta():
    name_field = ProductStoreSchema.model_fields["name"]
    assert name_field.description == "Product name."
    assert ProductStoreSchema.Meta.rules[0].path == "$.name"
    assert getattr(ProductStoreSchema.Meta, "tag") == "base"


def test_from_schema_partial_makes_fields_optional():
    name_field = ProductUpdateSchema.model_fields["name"]
    assert name_field.default is None
    assert name_field.is_required() is False
    assert type(None) in get_args(name_field.annotation)


def test_partial_schema_respects_field_overrides():
    price_field = ProductUpdateWithOverride.model_fields["price"]
    assert price_field.description == "Price override."
    assert price_field.is_required() is True


def test_extra_fields_can_be_added():
    assert "sku" in ProductWithExtraField.model_fields


def test_meta_rules_can_be_overridden():
    assert ProductCustomRules.Meta.rules[0].path == "$.price"
