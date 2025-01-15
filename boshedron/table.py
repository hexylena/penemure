from .sqlish import GroupedResultSet


def render_table(results: GroupedResultSet):
    page_content = "<table>"

    # Header is the same for each group so just take the first.
    page_content += "<thead><tr>"
    page_content += "".join([f"<th>{x.title()}</th>" for x in results.groups[0].header])
    page_content += "</tr></thead><tbody>"
    colspan = len(results.groups[0].header)

    for group in results.groups:
        page_content += f'<td colspan="{colspan}" class="header">{group.title}</td>'
        for row in group.rows:
            page_content += "<tr>"
            page_content += "".join([f"<td>{x}</td>" for x in row])
            page_content += "</tr>"
    page_content += "</tbody></table>"
    return page_content

def render_kanban(results: GroupedResultSet):
    page_content = '<div class="kanban">'

    # Header is the same for each group so just take the first.
    for group in results.groups:
        page_content += f'<div class="kanban-column">'
        if group.title:
            page_content += f'<div class="title">{group.title.title()}</div>'
        for row in group.rows:
            page_content += f'<div class="card">'
            for x in row:
                page_content += f'<div>{x}</div>'
            page_content += "</div>"
        page_content += '</div>'
    page_content += "</div>"
    return page_content
