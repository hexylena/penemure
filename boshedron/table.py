from .sqlish import GroupedResultSet
from .util import *


def render_table(results: GroupedResultSet) -> str:
    if results is None:
        return '<table class="table table-striped"></table>'

    return results.render_html_table()

def render_table_editable(results: GroupedResultSet) -> str:
    if results is None:
        return '<table class="table table-striped"></table>'

    page_content = '<table class="table table-striped">'

    # Header is the same for each group so just take the first.
    page_content += "<thead><tr>"
    page_content += "".join([f"<th>{x.title()}</th>" for x in results.groups[0].header])
    page_content += "</tr></thead><tbody>"
    colspan = len(results.groups[0].header)

    for group in results.groups:
        if len(results.groups) > 1:
            page_content += f'<tr><td colspan="{colspan}" class="header">{group.title}</td></tr>'
        for row_id, row in group.enum():
            page_content += f'<tr id="{row_id}">'
            # TODO: how do we know the true internal type/value?
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

        for row_id, row in group.enum():
            page_content += f'<div class="card" id="{row_id}">'

            page_content += f'<div class="card-body">'
            page_content += f'<div class="card-title h-5">{row[0]}</div>'
            for x in row[1:]:
                page_content += f'<div>{x}</div>'
            page_content += f'</div>'

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

def render_bar(results: GroupedResultSet) -> str:
    page_content = ""
    for group in results.groups:
        # chartscss instead of mermaid?
        page_content += f'<pre class="mermaid">xychart-beta\n'
        if group.title:
            page_content += f'\ttitle "{group.title or ''}"\n'

        page_content += f'\ty-axis {group.header[1]}\n'
        xaxis = ', '.join([f'"{x[0]}"' for x in group.rows])
        yaxis = ', '.join([f'{x[1]}' for x in group.rows])
        page_content += f'\tx-axis {group.header[0]} [{xaxis}]\n'
        page_content += f'\tbar [{yaxis}]\n'

        page_content += '</pre>'
    return page_content

def get_index(group, col):
        try:
            return group.header.index(col)
        except ValueError:
            return None

def render_gantt(results: GroupedResultSet) -> str:
    page_content = f'<pre class="mermaid">gantt\n    dateFormat X\n     axisFormat %b %dm- %Hh%M\n    title Gantt\n'
    for group in results.groups:
        if group.title:
            page_content += f'    section {group.title.title()}\n'

        # TODO: are we assuming specific columns have specific values? or can we be smart?
        indexes = {
            k: get_index(group, k)
            for k in ('url', 'time_start', 'time_end', 'title')
        }
        # print(group)
        # TODO: active, done, crit, milestone are valid tags.
        for row_id, row in group.enum():
            time_start = get_time(row[indexes['time_start']])
            time_end = get_time(row[indexes['time_end']])
            title = row[indexes['title']].replace(":", " ")

            page_content += f'        {title} : {row_id}, {time_start.strftime("%s")}, {time_end.strftime("%s")}\n'

        if indexes['url']:
            for row_id, row in group.enum():
                page_content += f'    click {row_id} href "{row[indexes["url"]]}"\n'

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

        indexes = {
            k: get_index(group, k)
            for k in ('urn', 'title', 'blurb')
        }

        page_content += '<div class="cards d-flex flex-wrap">' # Cards

        for row_id, row in group.enum():
            page_content += f'<div class="card linked m-1" style="width: 18rem;" id="{row_id}"><a href="{row[indexes["urn"]]}#url">'
            page_content += f'<div class="card-body">' # Body
            page_content += f'<div class="card-title h-5">{row[indexes["title"]]}</div>'
            page_content += f'<div class="card-text">{row[indexes["blurb"]]}</div>'
            for other in row[3:]:
                if other is not None and len(other) > 0:
                    page_content += f'<span class="tag">{other}</span>'
            page_content += '</div>' # end body
            page_content += "</a></div>"
        page_content += '</div>' # Cards

        page_content += '</div>'
    return page_content
