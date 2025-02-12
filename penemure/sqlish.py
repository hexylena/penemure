from pydantic import BaseModel, Field
from typing import Optional
import copy
from sqlglot import parse_one
from typing import Any


class ResultSet(BaseModel):
    title: Optional[str]
    header: list[str]
    rows: list[list[Any]]
    row_ids: Optional[list[str]]

    @classmethod
    def build(cls, header, rows, title=None, has_id=False):
        row_ids = None
        if has_id:
            row_ids = [x[-1] for x in rows]
            rows = [x[0:-1] for x in rows]

        rs = cls(
            title=title,
            header=header,
            rows=rows,
            row_ids=row_ids
        )
        return rs

    def is_empty(self):
        return len(self.header) == 0 or len(self.rows) == 0

    def safe_row_ids(self):
        if self.row_ids is None or len(self.row_ids) == 0:
            return [None] * len(self.rows)
        return self.row_ids

    def enum(self):
        yield from zip(self.safe_row_ids(), self.rows)


class GroupedResultSet(BaseModel):
    groups: list[ResultSet]

    def render_html_table(self):
        if len(self.groups) == 0:
            return "<table></table>"

        page_content = "<table>"
        # Header is the same for each group so just take the first.
        page_content += "<thead><tr>"
        page_content += "".join([f"<th>{x.title()}</th>" for x in self.groups[0].header])
        page_content += "</tr></thead><tbody>"
        colspan = len(self.groups[0].header)

        for group in self.groups:
            if len(self.groups) > 1:
                page_content += f'<tr><td colspan="{colspan}" class="header">{group.title}</td></tr>'
            for row_id, row in group.enum():
                page_content += f'<tr id="{row_id}">'
                page_content += "".join([
                    f"<td scope=\"row\">{x}</td>" if i == 0 else f"<td>{x}</td>"
                    for i, x in enumerate(row)
                    ])
                page_content += "</tr>"
        page_content += "</tbody></table>"
        return page_content


def select_group_key(row: list[str], columns: list[str], wanted_cols: list[str]) -> str:
    idx = []
    idxm = {c: i for i, c in enumerate(columns)}
    for w in wanted_cols:
        idx.append(idxm.get(w, None))

    indexes = [str(i) if i is None else row[i] for i in idx]
    return '|'.join(indexes)


def extract_groups(r: ResultSet, desired_groups: list) -> GroupedResultSet:
    gr = GroupedResultSet(groups=[])
    # TODO: replace with itertools.groupby

    t = {}
    for row_id, row in zip(r.safe_row_ids(), r.rows):
        sk = select_group_key(row, r.header, desired_groups)
        if sk not in t:
            t[sk] = []
        t[sk].append((row_id, row))

    for group_name, rows in t.items():
        gr.groups.append(ResultSet(title=group_name,
                                   header=r.header,
                                   row_ids=[x[0] for x in rows],
                                   rows=[x[1] for x in rows]))
    return gr
