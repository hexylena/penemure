from pydantic import BaseModel, Field
from typing import Optional
import copy
from sqlglot import parse_one
from typing import Any


class ResultSet(BaseModel):
    title: Optional[str]
    header: list[str]
    rows: list[list[Any]]


class GroupedResultSet(BaseModel):
    groups: list[ResultSet]


def select_group_key(row: list[str], columns: list[str], wanted_cols: list[str]) -> str:
    idx = []
    idxm = {c: i for i, c in enumerate(columns)}
    for w in wanted_cols:
        idx.append(idxm.get(w, None))

    indexes = [str(i) if i is None else row[i] for i in idx]
    return '|'.join(indexes)


def extract_groups(r: ResultSet, desired_groups: list) -> GroupedResultSet:
    gr = GroupedResultSet(groups=[])

    t = {}
    for row in r.rows:
        sk = select_group_key(row, r.header, desired_groups)
        if sk not in t:
            t[sk] = []
        t[sk].append(row)

    for k, v in t.items():
        gr.groups.append(ResultSet(title=k, header=r.header, rows=v))
    return gr
