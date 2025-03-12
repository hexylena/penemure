---
urn: "{{ note.thing.urn.urn }}"
backend: "{{ note.backend.name }}"
ancestors:
{%- for chain in oe.get_lineage(note) %}
{% if chain %}- {% for p in chain %}{% if loop.index > 1 %}→{% endif %} {{ p.urn }}#title{% endfor %}{% endif %}
{%- endfor %}
created: {{ note.thing.data.created }}
updated: {{ note.thing.data.updated }}
{% if note.get_template(oe) -%}
template: {{ note.get_template(oe).thing.data.title }} ({{ note.get_template(oe).thing.urn.urn }}){% endif %}
tags:
{%- for tag in note.thing.data.tags %}
    {{ tag.render_key(note.get_template(oe)) }}: "{{ tag.val }}"
{%- endfor %}
---

# {{ note.thing.data.icon }} {{ note.thing.data.title }}

{% if note.thing.data.contents %}
{% for b in note.thing.data.contents %}
{{ b.render(oe, Config.ExportPrefix, note.thing, penemure, format="md") }}
{% endfor %}
{% endif %}

{% if note.thing.data.attachments %}
### Attachments
{% for att in note.thing.data.attachments %}
{{ att }}
{% endfor %}
{% endif %}
