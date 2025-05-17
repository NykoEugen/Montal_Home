from django.http import HttpRequest


def cart_count(request: HttpRequest) -> dict:
    cart = request.session.get("cart", {})
    return {"cart_count": sum(cart.values())}
