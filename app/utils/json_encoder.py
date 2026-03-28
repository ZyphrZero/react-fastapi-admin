#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
JSON encoder utility module.
Provides a custom JSON encoder for serializing complex data types.
"""

import json
import decimal
from datetime import datetime
from typing import Any

from app.settings.config import settings


class ModelJSONEncoder(json.JSONEncoder):
    """
    Custom JSON encoder supporting Tortoise ORM models and complex data types.

    Supported data types:
    - datetime: converted to a formatted string
    - Decimal: converted to a string
    - BaseModel: prompts callers to use `to_json()`
    """

    def default(self, obj: Any) -> Any:
        """
        Override the default serialization method.

        Args:
            obj: Object to serialize.

        Returns:
            Any: Serialized value.

        Raises:
            TypeError: Raised when the object cannot be serialized.
        """
        # Import lazily to avoid a circular dependency.
        from app.models.base import BaseModel

        if isinstance(obj, BaseModel):
            # Tortoise ORM models should be serialized via the async `to_json()` helper.
            raise TypeError(f"对象 {obj} 不支持直接JSON序列化，请使用 await obj.to_json() 方法")
        elif isinstance(obj, datetime):
            # Format datetime values.
            return obj.strftime(settings.DATETIME_FORMAT)
        elif isinstance(obj, decimal.Decimal):
            # Convert Decimal values to strings to preserve precision.
            return str(obj)

        # Fall back to the base implementation.
        return super().default(obj)


def safe_json_dumps(obj: Any, **kwargs) -> str:
    """
    Safely serialize an object to JSON.

    Args:
        obj: Object to serialize.
        **kwargs: Extra arguments passed to `json.dumps`.

    Returns:
        str: JSON string.
    """
    kwargs.setdefault("cls", ModelJSONEncoder)
    kwargs.setdefault("ensure_ascii", False)
    kwargs.setdefault("default", str)

    return json.dumps(obj, **kwargs)


def safe_json_loads(s: str, **kwargs) -> Any:
    """
    Safely deserialize a JSON string.

    Args:
        s: JSON string.
        **kwargs: Extra arguments passed to `json.loads`.

    Returns:
        Any: Deserialized object.
    """
    return json.loads(s, **kwargs)
