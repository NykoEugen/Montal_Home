# Promotion Cleanup System

This system automatically removes promotional status from furniture items and size variants when their sale timers expire.

## Commands Available

### 1. `cleanup_expired_promotions`
Cleans up expired furniture promotions only.

```bash
# Dry run (show what would be changed)
python manage.py cleanup_expired_promotions --dry-run --verbose

# Actually perform cleanup
python manage.py cleanup_expired_promotions
```

### 2. `cleanup_expired_size_variant_promotions`
Cleans up expired size variant promotions only.

```bash
# Dry run (show what would be changed)
python manage.py cleanup_expired_size_variant_promotions --dry-run --verbose

# Actually perform cleanup
python manage.py cleanup_expired_size_variant_promotions
```

### 3. `cleanup_all_expired_promotions`
Cleans up both furniture and size variant promotions (recommended).

```bash
# Dry run (show what would be changed)
python manage.py cleanup_all_expired_promotions --dry-run --verbose

# Actually perform cleanup
python manage.py cleanup_all_expired_promotions
```

### 4. `scheduled_cleanup_promotions`
Simple command for cron jobs and scheduled tasks.

```bash
# Basic cleanup
python manage.py scheduled_cleanup_promotions

# With logging
python manage.py scheduled_cleanup_promotions --log
```

## Automatic Cleanup Methods

### 1. Server Startup Cleanup
The system automatically runs cleanup when the Django server starts (in production mode).

### 2. Admin Panel Action
In the Django admin panel, you can manually trigger cleanup:
1. Go to Furniture admin
2. Select items (or none for all)
3. Choose "Очистити закінчені акції" from the actions dropdown

### 3. Cron Job Setup
Set up a cron job to run cleanup automatically:

```bash
# Edit crontab
crontab -e

# Add one of these lines:

# Run every hour
0 * * * * cd /path/to/your/project && python manage.py scheduled_cleanup_promotions --log

# Run daily at 2 AM
0 2 * * * cd /path/to/your/project && python manage.py scheduled_cleanup_promotions --log

# Run every 6 hours
0 */6 * * * cd /path/to/your/project && python manage.py scheduled_cleanup_promotions --log
```

## What Gets Cleaned Up

### Furniture Items
- Removes `is_promotional = True` → `False`
- Clears `promotional_price` → `None`
- Clears `sale_end_date` → `None`

### Size Variants
- Clears `promotional_price` → `None`
- Keeps other fields unchanged

## Example Output

```
Starting cleanup of expired promotions...

=== Cleaning up expired furniture promotions ===
Found 1 promotional items with expired sale timers:
  - Boston A (ID: 4)
    Sale ended: 2025-08-22 17:00:00
    Original price: 9990.0 грн
    Promotional price: 8880.0 грн
    Savings: 1110.0 грн

✓ Removed promotional status from: Boston A

Successfully removed promotional status from 1 items
Total savings lost: 1110.0 грн

=== Cleaning up expired size variant promotions ===
No size variants with expired promotional prices found.

Cleanup completed!
```

## Configuration

### Enable Startup Cleanup
Add to your Django settings:

```python
# settings.py
CLEANUP_PROMOTIONS_ON_STARTUP = True  # Enable cleanup on server startup
```

### Logging
The system uses Django's logging system. Configure in settings:

```python
# settings.py
LOGGING = {
    'version': 1,
    'disable_existing_loggers': False,
    'handlers': {
        'file': {
            'level': 'INFO',
            'class': 'logging.FileHandler',
            'filename': 'promotion_cleanup.log',
        },
    },
    'loggers': {
        'furniture.management.commands': {
            'handlers': ['file'],
            'level': 'INFO',
            'propagate': True,
        },
    },
}
```

## Troubleshooting

### Check for Expired Items
```bash
python manage.py shell
```

```python
from django.utils import timezone
from furniture.models import Furniture, FurnitureSizeVariant

# Check expired furniture
expired_furniture = Furniture.objects.filter(
    is_promotional=True,
    sale_end_date__isnull=False,
    sale_end_date__lt=timezone.now()
)
print(f"Expired furniture: {expired_furniture.count()}")

# Check expired size variants
expired_variants = FurnitureSizeVariant.objects.filter(
    promotional_price__isnull=False,
    furniture__is_promotional=True,
    furniture__sale_end_date__isnull=False,
    furniture__sale_end_date__lt=timezone.now()
)
print(f"Expired variants: {expired_variants.count()}")
```

### Manual Cleanup
If automatic cleanup fails, you can manually run:

```bash
python manage.py cleanup_all_expired_promotions --verbose
```

This will show you exactly what's being cleaned up and any errors that occur.
