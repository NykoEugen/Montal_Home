from django.test import TestCase
from django.template import Template, Context
from .templatetags.cart_filters import multiply


class CartFiltersTestCase(TestCase):
    def test_multiply_filter(self):
        """Test the multiply template filter."""
        # Test basic multiplication
        self.assertEqual(multiply(10, 2), 20.0)
        self.assertEqual(multiply(5.5, 3), 16.5)
        
        # Test with string inputs
        self.assertEqual(multiply("10", "2"), 20.0)
        
        # Test with invalid inputs
        self.assertEqual(multiply("invalid", 2), "invalid")
        self.assertEqual(multiply(10, "invalid"), 10)
        
        # Test template usage
        template = Template("{% load cart_filters %}{{ value|multiply:2 }}")
        context = Context({"value": 15})
        self.assertEqual(template.render(context), "30.0")


class CartTestCase(TestCase):
    def test_cart_item_count(self):
        """Test the cart item count filter."""
        from .templatetags.cart_filters import cart_item_count
        
        cart = {
            '1': {'quantity': 2},
            '2': {'quantity': 1},
            '3': {'quantity': 3}
        }
        self.assertEqual(cart_item_count(cart), 6)
        
        empty_cart = {}
        self.assertEqual(cart_item_count(empty_cart), 0)
