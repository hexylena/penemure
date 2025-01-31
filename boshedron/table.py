from .sqlish import GroupedResultSet
import datetime


def render_table(results: GroupedResultSet) -> str:
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

def render_kanban(results: GroupedResultSet) -> str:
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

def render_pie(results: GroupedResultSet) -> str:
    page_content = ""
    for group in results.groups:
        # chartscss instead of mermaid?
        page_content += f'<pre class="mermaid">pie title {group.title or ""}\n'
        for row in group.rows:
            page_content += f'    "{row[0]}" : {row[1]}\n'
        page_content += '</pre>'
    return page_content

def render_gantt(results: GroupedResultSet) -> str:
    page_content = f'<pre class="mermaid">gantt\n    dateFormat X\n     axisFormat %b %d %Hh%M\n    title Gantt\n'
    for group in results.groups:
        if group.title:
            page_content += f'    section {group.title.title()}\n'

        # TODO: are we assuming specific columns have specific values? or can we be smart?
        try:
            url_idx = group.header.index('url')
        except ValueError:
            url_idx = None

        try:
            id_idx = group.header.index('id')
        except ValueError:
            id_idx = None

        # TODO: active, done, crit, milestone are valid tags.
        for row in group.rows:
            if id_idx:
                page_content += f'        {row[0].replace(":", " ")} : {row[id_idx]}, {row[1].strftime("%s")}, {row[2].strftime("%s")}\n'
            else:
                page_content += f'        {row[0].replace(":", " ")} : {row[1].strftime("%s")}, {row[2].strftime("%s")}\n'

        if url_idx and id_idx:
            for row in group.rows:
                page_content += f'    click {row[id_idx]} href "{row[url_idx]}"'

    page_content += '</pre>'
    return page_content

def render_cards(results: GroupedResultSet) -> str:
    if results is None:
        return '<div class="kanban"></div>'

    page_content = ''
    # Header is the same for each group so just take the first.
    for group in results.groups:
        page_content += f'<div class="card-group">'
        if len(results.groups) > 1:
            if group.title:
                page_content += f'<div class="title">{group.title.title()}</div>'
            else:
                page_content += f'<div class="title">Unknown</div>'

        page_content += '<div class="cards">' # Cards
        for row in group.rows:
            page_content += f'<div class="card linked">'
            (urn, title, blurb) = row[0:3]
            page_content += f'<a href="{urn}#url">'
            page_content += f'<div><b>{title}</b></div>'
            page_content += f'<div>{blurb}</div>'
            for other in row[3:]:
                page_content += f'<div>{other}</div>'
            page_content += f'</a>'

            page_content += "</div>"
        page_content += '</div>' # Cards

        page_content += '</div>'
    return page_content
