from .sqlish import GroupedResultSet
import datetime


def render_table(results: GroupedResultSet):
    if results is None:
        return '<table></table>'

    page_content = "<table>"

    # Header is the same for each group so just take the first.
    page_content += "<thead><tr>"
    page_content += "".join([f"<th>{x.title()}</th>" for x in results.groups[0].header])
    page_content += "</tr></thead><tbody>"
    colspan = len(results.groups[0].header)

    for group in results.groups:
        if len(results.groups) > 1:
            page_content += f'<tr><td colspan="{colspan}" class="header">{group.title}</td></tr>'
        for row in group.rows:
            page_content += "<tr>"
            page_content += "".join([f"<td>{x}</td>" for x in row])
            page_content += "</tr>"
    page_content += "</tbody></table>"
    return page_content

def render_kanban(results: GroupedResultSet):
    if results is None:
        return '<div class="kanban"></div>'

    page_content = '<div class="kanban">'

    # Header is the same for each group so just take the first.
    for group in results.groups:
        page_content += f'<div class="kanban-column">'
        if group.title:
            page_content += f'<div class="title">{group.title.title()}</div>'
        else:
            page_content += f'<div class="title">Unknown</div>'
        for row in group.rows:
            page_content += f'<div class="card">'
            for x in row:
                page_content += f'<div>{x}</div>'
            page_content += "</div>"
        page_content += '</div>'
    page_content += "</div>"
    return page_content

def render_pie(results: GroupedResultSet):
    page_content = ""
    for group in results.groups:
        # chartscss instead of mermaid?
        page_content += f'<pre class="mermaid">pie title {group.title or ""}\n'
        for row in group.rows:
            page_content += f'    "{row[0]}" : {row[1]}\n'
        page_content += '</pre>'
    return page_content

def render_gantt(results: GroupedResultSet):
    page_content = f'<pre class="mermaid">gantt\n    dateFormat X\n    title Gantt\n'
    for group in results.groups:
        page_content += f'    section {group.title.title()}\n'
        # chartscss instead of mermaid?
        for row in group.rows:
            page_content += f'        {row[0]} : {row[1].strftime("%s")}, {row[2].strftime("%s")}\n'

    page_content += '</pre>'
    return page_content
