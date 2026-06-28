import operator
from typing import Annotated, Any

def merge_dicts(a: dict, b: dict) -> dict:
    """
    Merge two dictionaries. 
    Useful for state keys like `branch_status` where different branches might update different keys.
    """
    res = a.copy()
    res.update(b)
    return res

def append_list(a: list, b: list) -> list:
    """
    Append elements to a list.
    Useful for `workflow_logs` or `errors` where parallel branches might append simultaneously.
    """
    if a is None:
        a = []
    if b is None:
        b = []
    return a + b
