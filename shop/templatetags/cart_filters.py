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
def page_url(context, page_number):
    """
    Повертає URL з поточними GET-параметрами, але з оновленим page.
    Усуває дублікати page та коректно кодує мульти-значення.
    """
    request = context["request"]
    params = request.GET.copy()     # QueryDict (mutable copy)
    # Примусово ставимо один page (не список)
    params.setlist("page", [str(int(page_number)) if str(page_number).isdigit() else "1"])
    qs = params.urlencode()         # правильне кодування для QueryDict
    return f"?{qs}" if qs else "?page=1"
