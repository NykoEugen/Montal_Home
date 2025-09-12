from django import template
from django.utils.http import urlencode

register = template.Library()

@register.filter
def multiply(value, arg):
    """Multiply the value by the argument."""
    try:
        return float(value) * float(arg)
    except (ValueError, TypeError):
        return value

@register.filter
def cart_item_count(cart):
    """Return the total number of items in the cart."""
    return sum(item['quantity'] for item in cart.values())

@register.filter
def calculate_savings(price, promotional_price):
    """Calculate savings amount between regular and promotional price."""
    try:
        return float(price) - float(promotional_price)
    except (ValueError, TypeError):
        return 0

@register.filter
def get_item(dictionary, key):
    """Get an item from a dictionary by key."""
    return dictionary.get(key)

@register.filter
def replace(value, arg):
    """Replace a substring in a string."""
    try:
        old, new = arg.split(':', 1)
        return value.replace(old, new)
    except (ValueError, AttributeError):
        return value

@register.filter
def has_values(get_dict, key):
    """Check if a GET parameter has any values."""
    try:
        values = get_dict.getlist(key)
        return len(values) > 0
    except (AttributeError, TypeError):
        return False

@register.filter
def has_stock_status(get_dict):
    """Check if stock_status parameters exist."""
    try:
        values = get_dict.getlist('stock_status')
        return len(values) > 0
    except (AttributeError, TypeError):
        return False

@register.filter
def getlist(get_dict, key):
    """Get a list of values for a GET parameter."""
    try:
        return get_dict.getlist(key)
    except (AttributeError, TypeError):
        return []

@register.simple_tag(takes_context=True)
def pagination_url(context, page_number):
    """Generate clean pagination URL with current parameters and new page number."""
    request = context['request']
    params = request.GET.copy()
    
    # Remove existing page parameter to avoid duplication
    if 'page' in params:
        del params['page']
    
    # Add new page number
    params['page'] = page_number
    
    if params:
        return f"?{params.urlencode()}"
    return f"?page={page_number}"
