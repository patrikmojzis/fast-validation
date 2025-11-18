from __future__ import annotations

from copy import copy
from typing import Any, Callable, Dict, Optional, Type, TypeVar, get_args, get_origin

from pydantic.fields import FieldInfo

from .schema import Schema

SchemaType = TypeVar("SchemaType", bound="Schema")
_MISSING = object()


def from_schema(
    base_schema: Type[SchemaType],
    *,
    partial: bool = False,
) -> Callable[[Type[Any]], Type[SchemaType]]:
    """
    Decorate a class to derive a new schema from an existing base schema.

    The decorated class can override fields or metadata while inheriting
    everything else from ``base_schema``. When ``partial`` is True,
    any field not explicitly overridden becomes optional.
    """

    if not isinstance(base_schema, type) or not issubclass(base_schema, Schema):
        raise TypeError("from_schema() base must be a Schema subclass")

    def decorator(target_cls: Type[Any]) -> Type[SchemaType]:
        if not isinstance(target_cls, type):
            raise TypeError("@from_schema can only decorate classes")

        return _build_schema_from_base(
            base_schema=base_schema,
            target_cls=target_cls,
            make_partial=partial,
        )

    return decorator


def _build_schema_from_base(
    *,
    base_schema: Type[SchemaType],
    target_cls: Type[Any],
    make_partial: bool,
) -> Type[SchemaType]:
    base_fields = getattr(base_schema, "model_fields", {}) or {}
    target_annotations: Dict[str, Any] = dict(getattr(target_cls, "__annotations__", {}))
    namespace: Dict[str, Any] = {
        "__module__": target_cls.__module__,
        "__doc__": target_cls.__doc__,
    }

    for key, value in target_cls.__dict__.items():
        if key in {
            "__dict__",
            "__weakref__",
            "__annotations__",
            "__module__",
            "__doc__",
            "Meta",
        }:
            continue
        namespace[key] = value

    combined_annotations: Dict[str, Any] = dict(target_annotations)

    for field_name, field_info in base_fields.items():
        if field_name in target_annotations:
            continue

        annotation = field_info.annotation or Any
        should_optionalize = make_partial and field_info.is_required()
        if should_optionalize:
            annotation = _optionalize(annotation)

        combined_annotations[field_name] = annotation
        namespace[field_name] = _copy_field_info(
            field_info=field_info,
            force_optional=should_optionalize,
        )

    for field_name, annotation in target_annotations.items():
        combined_annotations[field_name] = annotation
        attr_value = target_cls.__dict__.get(field_name, _MISSING)
        if attr_value is not _MISSING:
            namespace[field_name] = attr_value

    namespace["__annotations__"] = combined_annotations
    meta = _compose_meta(
        target_meta=target_cls.__dict__.get("Meta"),
        base_meta=getattr(base_schema, "Meta", None),
    )

    extra_bases = tuple(
        base
        for base in target_cls.__bases__
        if base not in (object, base_schema)
    )
    bases = (base_schema,) + extra_bases
    derived = type(target_cls.__name__, bases, namespace)
    derived.Meta = meta
    derived.__from_schema_base__ = base_schema
    derived.__from_schema_partial__ = make_partial
    return derived


def _compose_meta(target_meta: Optional[type], base_meta: Optional[type]) -> type:
    if target_meta and base_meta and base_meta not in target_meta.__mro__:
        return type("Meta", (target_meta, base_meta), {})
    return target_meta or base_meta or type("Meta", (), {})  # type: ignore[return-value]


def _optionalize(annotation: Any) -> Any:
    if annotation is Any:
        return Optional[Any]

    origin = get_origin(annotation)
    if origin is None:
        return Optional[annotation]

    args = get_args(annotation)
    if args and type(None) in args:
        return annotation

    return Optional[annotation]


def _copy_field_info(*, field_info: FieldInfo, force_optional: bool) -> FieldInfo:
    clone = copy(field_info)
    if force_optional and clone.is_required():
        clone.default = None
        clone.default_factory = None
    return clone
