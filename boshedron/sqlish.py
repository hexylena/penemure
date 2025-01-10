from pydantic import BaseModel
from typing import Optional
from sqlglot import parse_one


class ResultSet(BaseModel):
    title: str
    data: list[list[str]]


class GroupedResultSet(BaseModel):
    header: list[str]
    rows: list[ResultSet]


