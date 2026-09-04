from pyspark.sql import DataFrame
from functools import reduce
import math
from typing import Any

def is_valid(value: Any) -> bool:
    """
    Check whether a value should be considered valid.

    A value is considered invalid when it is None or NaN.

    Args:
        value: Value to validate.

    Returns:
        bool: True if the value is valid, False otherwise.
    """

    if value is None:
        return False

    try:
        return not math.isnan(value)
    except (TypeError, ValueError):
        return True