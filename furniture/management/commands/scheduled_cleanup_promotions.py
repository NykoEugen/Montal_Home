#!/usr/bin/env python
"""
Scheduled cleanup command for expired promotions.
This command can be run by cron jobs to automatically clean up expired promotions.

Example cron job (runs every hour):
0 * * * * cd /path/to/project && python manage.py scheduled_cleanup_promotions

Example cron job (runs daily at 2 AM):
0 2 * * * cd /path/to/project && python manage.py scheduled_cleanup_promotions
"""

from django.core.management.base import BaseCommand
from django.core.management import call_command
from django.utils import timezone
import logging

# Set up logging
logger = logging.getLogger(__name__)


class Command(BaseCommand):
    help = 'Scheduled cleanup of expired promotions (for cron jobs)'

    def add_arguments(self, parser):
        parser.add_argument(
            '--log',
            action='store_true',
            help='Log the results to Django logs',
        )

    def handle(self, *args, **options):
        log_results = options['log']
        
        if log_results:
            logger.info("Starting scheduled cleanup of expired promotions")
        
        try:
            # Run the cleanup command
            call_command('cleanup_all_expired_promotions', verbosity=0)
            
            if log_results:
                logger.info("Scheduled cleanup of expired promotions completed successfully")
            
            # Return success exit code
            return 0
            
        except Exception as e:
            error_msg = f"Error during scheduled cleanup: {e}"
            if log_results:
                logger.error(error_msg)
            else:
                self.stdout.write(
                    self.style.ERROR(error_msg)
                )
            
            # Return error exit code
            return 1
