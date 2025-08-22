from django.core.management.base import BaseCommand
from django.core.management import call_command


class Command(BaseCommand):
    help = 'Clean up all expired promotions (furniture and size variants)'

    def add_arguments(self, parser):
        parser.add_argument(
            '--dry-run',
            action='store_true',
            help='Show what would be changed without making changes',
        )
        parser.add_argument(
            '--verbose',
            action='store_true',
            help='Show detailed information about each item',
        )

    def handle(self, *args, **options):
        dry_run = options['dry_run']
        verbose = options['verbose']
        
        self.stdout.write(
            self.style.SUCCESS('Starting cleanup of expired promotions...')
        )
        self.stdout.write('')
        
        # Clean up expired furniture promotions
        self.stdout.write(
            self.style.WARNING('=== Cleaning up expired furniture promotions ===')
        )
        call_command(
            'cleanup_expired_promotions',
            dry_run=dry_run,
            verbose=verbose
        )
        
        self.stdout.write('')
        
        # Clean up expired size variant promotions
        self.stdout.write(
            self.style.WARNING('=== Cleaning up expired size variant promotions ===')
        )
        call_command(
            'cleanup_expired_size_variant_promotions',
            dry_run=dry_run,
            verbose=verbose
        )
        
        self.stdout.write('')
        self.stdout.write(
            self.style.SUCCESS('Cleanup completed!')
        )
