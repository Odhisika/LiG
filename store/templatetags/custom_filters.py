from django import template

register = template.Library()

@register.filter
def sub(value, arg):
    try:
        return float(value) - float(arg)
    except (ValueError, TypeError):
        return ''

@register.filter
def split(value, delimiter=','):
    if value:
        return value.split(delimiter)
    return []

@register.filter
def trim(value):
    if isinstance(value, str):
        return value.strip()
    return value

@register.simple_tag
def get_elided_page_range(paginator, number, on_each_side=1, on_ends=1):
    return paginator.get_elided_page_range(number, on_each_side=on_each_side, on_ends=on_ends)
