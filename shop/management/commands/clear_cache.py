from django.core.cache import cache
from django.core.management.base import BaseCommand
import os
import shutil

class Command(BaseCommand):
    help = 'Clear Django cache (Redis/LocMem) and bytecode files'

    def handle(self, *args, **options):
        from django.conf import settings

        self.stdout.write('Clearing cache...')

        # Clear Django cache (Redis or LocMem)
        try:
            cache.clear()
            self.stdout.write(self.style.SUCCESS('Django cache cleared'))
        except Exception as e:
            self.stdout.write(self.style.WARNING(f'Django cache clear failed: {e}'))
        
        # Clear __pycache__ directories
        base_dir = settings.BASE_DIR
        pycache_count = 0
        pyc_count = 0
        
        # Find and remove __pycache__ directories
        for root, dirs, files in os.walk(base_dir):
            for dir_name in dirs:
                if dir_name == '__pycache__':
                    pycache_path = os.path.join(root, dir_name)
                    try:
                        shutil.rmtree(pycache_path)
                        pycache_count += 1
                        self.stdout.write(f'🗑️  Removed: {pycache_path}')
                    except OSError as e:
                        self.stdout.write(f'⚠️  Could not remove {pycache_path}: {e}')
        
        # Remove .pyc files
        for root, dirs, files in os.walk(base_dir):
            for file in files:
                if file.endswith('.pyc'):
                    pyc_path = os.path.join(root, file)
                    try:
                        os.remove(pyc_path)
                        pyc_count += 1
                        self.stdout.write(f'🗑️  Removed: {pyc_path}')
                    except OSError as e:
                        self.stdout.write(f'⚠️  Could not remove {pyc_path}: {e}')
        
        # Touch static files
        static_dirs = getattr(settings, 'STATICFILES_DIRS', [])
        touched_count = 0
        
        for static_dir in static_dirs:
            if os.path.exists(static_dir):
                for root, dirs, files in os.walk(static_dir):
                    for file in files:
                        if file.endswith(('.css', '.js', '.png', '.jpg', '.jpeg', '.gif', '.svg', '.ico')):
                            file_path = os.path.join(root, file)
                            try:
                                os.utime(file_path, None)
                                touched_count += 1
                                self.stdout.write(f'📝 Touched: {file_path}')
                            except OSError as e:
                                self.stdout.write(f'⚠️  Could not touch {file_path}: {e}')
        
        self.stdout.write(
            self.style.SUCCESS(f'✅ Cache cleared successfully!')
        )
        self.stdout.write(f'📊 Summary: {pycache_count} __pycache__ dirs, {pyc_count} .pyc files, {touched_count} static files touched')
        self.stdout.write(
            self.style.WARNING('💡 Tip: Hard refresh your browser (Ctrl+F5 or Cmd+Shift+R) to see changes')
        )

