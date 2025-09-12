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
    
    # Ensure page_number is a clean integer/string
    try:
        # Handle case where page_number might be a list or other type
        if isinstance(page_number, list):
            page_number = page_number[0] if page_number else 1
        page_number = str(int(page_number))
    except (ValueError, TypeError):
        page_number = '1'
    
    # Add new page number
    params['page'] = page_number
    
    # Generate clean URL
    query_string = params.urlencode()
    if query_string:
        return f"?{query_string}"
    return f"?page={page_number}"

@register.simple_tag(takes_context=True)
def clean_pagination_url(context, page_number):
    """Generate completely clean pagination URL with current parameters and new page number."""
    request = context['request']
    
    # Create a new clean QueryDict
    clean_params = {}
    
    # Copy only the parameters we want to keep
    for key, value in request.GET.items():
        # Skip page parameter
        if key == 'page':
            continue
        
        # Handle single values (not lists)
        if isinstance(value, list):
            if value:  # Only add if list is not empty
                clean_params[key] = value[0]  # Take first value
        else:
            clean_params[key] = value
    
    # Add new page number
    clean_params['page'] = str(page_number)
    
    # Generate clean URL
    from urllib.parse import urlencode
    query_string = urlencode(clean_params)
    return f"?{query_string}" if query_string else f"?page={page_number}"
