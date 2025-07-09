import os

from django.conf import settings
from django.core.management import call_command
from django.core.management.base import BaseCommand, CommandError


class Command(BaseCommand):
    help = "Load fixtures with better error handling and validation"

    def add_arguments(self, parser):
        parser.add_argument(
            "fixture_file", type=str, help="Path to the fixture file (e.g., data.json)"
        )
        parser.add_argument(
            "--force", action="store_true", help="Force load even if errors occur"
        )

    def handle(self, *args, **options):
        fixture_file = options["fixture_file"]
        force = options["force"]

        # Check if file exists
        if not os.path.exists(fixture_file):
            raise CommandError(f"Fixture file '{fixture_file}' does not exist")

        # Check file extension
        if not fixture_file.endswith((".json", ".xml", ".yaml")):
            self.stdout.write(
                self.style.WARNING(
                    f"Warning: {fixture_file} might not be a valid fixture file"
                )
            )

        try:
            self.stdout.write(f"Loading fixture: {fixture_file}")
            call_command("loaddata", fixture_file, verbosity=1)
            self.stdout.write(
                self.style.SUCCESS(f"Successfully loaded fixture: {fixture_file}")
            )
        except Exception as e:
            error_msg = f"Error loading fixture '{fixture_file}': {str(e)}"
            if force:
                self.stdout.write(self.style.WARNING(f"Warning: {error_msg}"))
            else:
                raise CommandError(error_msg)
