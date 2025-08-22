# Sale Countdown Timer Setup Guide

## Overview
This guide explains how to set up countdown timers for promotional sales in your furniture store, including individual size variant pricing.

## How Countdown Timers Work

### 1. **Database Structure**
- Added `sale_end_date` field to the Furniture model
- Added `promotional_price` field to FurnitureSizeVariant model
- Only promotional items with end dates show countdown timers
- Items without end dates show as permanent sales

### 2. **Automatic Filtering**
- Only active sales (end date in future) appear in carousel
- Expired sales are automatically hidden
- Items without end dates are treated as permanent promotions

### 3. **Size Variant Pricing**
- Each size variant can have its own promotional price
- If no variant-specific price is set, uses parent furniture promotional price
- Flexible pricing strategy for different sizes

## Setting Up Countdown Timers

### Option 1: Using Django Admin (Recommended)

1. **Access Django Admin**
   ```
   http://localhost:8000/admin/
   ```

2. **Navigate to Furniture**
   - Go to Furniture section
   - Find the item you want to make promotional

3. **Set Promotional Details**
   - Check "Акційний" (Promotional)
   - Set "Акційна ціна" (Promotional price)
   - Set "Дата закінчення акції" (Sale end date)
   - Save the item

4. **Set Size Variant Promotional Prices**
   - In the Furniture edit page, scroll to "Розмірні варіанти"
   - Set individual "Акційна ціна" for each size variant
   - Leave empty to use parent furniture promotional price

### Option 2: Using Management Commands

#### View Current Promotional Items
```bash
python3 manage.py setup_sale_dates
```

#### Set Sale End Date for All Items (7 days from now)
```bash
python3 manage.py setup_sale_dates --all --days 7
```

#### Set Sale End Date for Specific Item
```bash
python3 manage.py setup_sale_dates --item-id 123 --days 14
```

#### Set Promotional Prices for Size Variants
```bash
# View current promotional size variants
python3 manage.py setup_size_variant_promotions

# Set 20% discount for all variants of furniture ID 123
python3 manage.py setup_size_variant_promotions --furniture-id 123 --discount-percent 20

# Set 15% discount for specific size variant ID 456
python3 manage.py setup_size_variant_promotions --variant-id 456 --discount-percent 15

# Apply 25% discount to all size variants of promotional furniture
python3 manage.py setup_size_variant_promotions --apply-to-all --discount-percent 25

# Clear promotional prices
python3 manage.py setup_size_variant_promotions --clear --furniture-id 123
```

### Option 3: Programmatically

```python
from django.utils import timezone
from datetime import timedelta
from furniture.models import Furniture, FurnitureSizeVariant

# Set sale end date for specific item
item = Furniture.objects.get(id=123)
item.is_promotional = True
item.promotional_price = 1500.00
item.sale_end_date = timezone.now() + timedelta(days=7)
item.save()

# Set promotional prices for size variants
variants = item.size_variants.all()
for variant in variants:
    # Set 20% discount for each variant
    variant.promotional_price = variant.price * 0.8
    variant.save()

# Set different discounts for different sizes
small_variant = item.size_variants.filter(height__lt=80).first()
if small_variant:
    small_variant.promotional_price = small_variant.price * 0.75  # 25% discount
    small_variant.save()
```

## Countdown Timer Features

### Visual Elements
- **Timer Display**: Shows hours:minutes:seconds remaining
- **Color Changes**: Timer turns red when time expires
- **Position**: Top-right corner of each promotional card
- **Visibility**: Only shows for items with end dates

### JavaScript Functionality
- **Real-time Updates**: Updates every second
- **Automatic Expiry**: Changes to "00:00:00" when expired
- **Visual Feedback**: Background color changes on expiry
- **Performance**: Optimized with efficient DOM updates

## Size Variant Promotional Pricing

### Pricing Hierarchy
1. **Size Variant Promotional Price** (if set) - Highest priority
2. **Parent Furniture Promotional Price** (if furniture is promotional)
3. **Size Variant Regular Price** - Default fallback

### Admin Interface Features
- **Inline Editing**: Set promotional prices directly in furniture edit page
- **Visual Indicators**: Shows current price and discount percentage
- **Bulk Actions**: Apply promotional prices to multiple variants
- **Status Display**: Color-coded sale status for each variant

### Management Commands
- **View Current Promotions**: See all promotional size variants
- **Bulk Price Setting**: Apply discounts to multiple variants
- **Flexible Discounts**: Different percentages for different items
- **Easy Cleanup**: Clear promotional prices when needed

## Best Practices

### 1. **Setting Realistic End Dates**
- **Flash Sales**: 1-3 days
- **Weekend Sales**: 2-4 days  
- **Seasonal Sales**: 7-30 days
- **Clearance Sales**: 14-60 days

### 2. **Creating Urgency**
- Use shorter timeframes for high-value items
- Set different end dates for different categories
- Consider timezone differences for international customers

### 3. **Managing Multiple Sales**
- Stagger end dates to maintain consistent promotional content
- Use management commands for bulk operations
- Monitor active sales regularly

### 4. **Size Variant Pricing Strategy**
- **Popular Sizes**: Higher discounts to drive sales
- **Premium Sizes**: Smaller discounts to maintain margin
- **Clearance Sizes**: Deep discounts to clear inventory
- **Consistent Branding**: Maintain price relationship between sizes

## Example Scenarios

### Flash Sale (24 hours)
```bash
python3 manage.py setup_sale_dates --item-id 123 --days 1
python3 manage.py setup_size_variant_promotions --furniture-id 123 --discount-percent 30
```

### Weekend Sale (3 days)
```bash
python3 manage.py setup_sale_dates --all --days 3
python3 manage.py setup_size_variant_promotions --apply-to-all --discount-percent 20
```

### Monthly Clearance (30 days)
```bash
python3 manage.py setup_sale_dates --all --days 30
python3 manage.py setup_size_variant_promotions --apply-to-all --discount-percent 40
```

### Tiered Pricing Strategy
```python
# Different discounts for different sizes
furniture = Furniture.objects.get(id=123)
variants = furniture.size_variants.all()

for variant in variants:
    if variant.height < 80:  # Small sizes
        variant.promotional_price = variant.price * 0.7  # 30% off
    elif variant.height < 100:  # Medium sizes
        variant.promotional_price = variant.price * 0.8  # 20% off
    else:  # Large sizes
        variant.promotional_price = variant.price * 0.85  # 15% off
    variant.save()
```

## Troubleshooting

### Timer Not Showing
1. Check if item is marked as promotional
2. Verify sale_end_date is set
3. Ensure promotional_price is not null
4. Check if sale hasn't expired

### Timer Not Updating
1. Refresh the page
2. Check browser console for JavaScript errors
3. Verify countdown.js is loaded
4. Check if item has valid end date

### Expired Sales Still Showing
1. Run the view to refresh the query
2. Check if sale_end_date is in the past
3. Verify the timezone settings

### Size Variant Pricing Issues
1. Check if parent furniture is promotional
2. Verify size variant promotional price is set correctly
3. Ensure price calculations are working
4. Check admin interface for visual feedback

## Advanced Configuration

### Custom Countdown Styles
Edit `static/css/style.css`:
```css
.countdown-timer {
    font-family: 'Courier New', monospace;
    font-weight: bold;
    letter-spacing: 1px;
    /* Add custom styles here */
}
```

### Custom JavaScript Behavior
Edit `static/js/carousel.js` in the `updateCountdown` function:
```javascript
function updateCountdown(timer, endDate) {
    // Custom countdown logic here
}
```

### Custom Pricing Logic
Extend the `current_price` property in `FurnitureSizeVariant`:
```python
@property
def current_price(self):
    # Add custom pricing logic here
    if self.promotional_price is not None:
        return self.promotional_price
    # ... rest of logic
```

## Monitoring Active Sales

### Check Active Promotions
```bash
python3 manage.py shell
```

```python
from furniture.models import Furniture, FurnitureSizeVariant
from django.utils import timezone

# Get all active sales
active_sales = Furniture.objects.filter(
    is_promotional=True,
    promotional_price__isnull=False
).filter(
    models.Q(sale_end_date__isnull=True) |
    models.Q(sale_end_date__gt=timezone.now())
)

for sale in active_sales:
    print(f"{sale.name}: {sale.sale_end_date}")
    
    # Check size variants
    for variant in sale.size_variants.all():
        if variant.is_on_sale:
            print(f"  {variant.dimensions}: {variant.current_price} грн (-{variant.discount_percentage}%)")
```

This setup provides a complete countdown timer system for your promotional sales with flexible size variant pricing and easy management through Django admin or command-line tools.
