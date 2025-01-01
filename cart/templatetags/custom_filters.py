# cart/templatetags/custom_filters.py

from django import template

register = template.Library()

@register.filter(name='get_item')
def get_item(dictionary, key):
    """
    Template filter to get an item from a dictionary using a variable key
    Usage: {{ dictionary|get_item:key }}
    """
    return dictionary.get(str(key))