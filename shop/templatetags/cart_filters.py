from django import template

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