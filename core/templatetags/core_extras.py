from django import template

register = template.Library()

@register.filter
def dict_lookup(d, key):
    """Look up a key in a dict from a template."""
    if isinstance(d, dict):
        return d.get(key, [])
    return []

@register.filter
def get_item(lst, index):
    try:
        return lst[index]
    except (IndexError, KeyError, TypeError):
        return None

@register.filter
def percentage(value, total):
    try:
        return round((int(value) / int(total)) * 100)
    except (ValueError, ZeroDivisionError):
        return 0
