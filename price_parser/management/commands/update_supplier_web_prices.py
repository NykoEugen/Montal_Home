from django.core.management.base import BaseCommand, CommandError

from price_parser.models import SupplierWebConfig
from price_parser.services import SupplierWebPriceUpdater


class Command(BaseCommand):
    help = "Update furniture prices from supplier website pages"

    def add_arguments(self, parser):
        parser.add_argument(
            "--config-id",
            type=int,
            help="ID of a specific SupplierWebConfig to run",
        )
        parser.add_argument(
            "--config-name",
            type=str,
            help="Name of a specific SupplierWebConfig to run",
        )
        parser.add_argument(
            "--all",
            action="store_true",
            help="Run all active supplier web configurations",
        )
        parser.add_argument(
            "--test",
            action="store_true",
            help="Run in test mode without DB updates",
        )

    def handle(self, *args, **options):
        configs = []

        if options["config_id"]:
            try:
                configs.append(SupplierWebConfig.objects.get(id=options["config_id"]))
            except SupplierWebConfig.DoesNotExist as exc:
                raise CommandError(f'Configuration with ID {options["config_id"]} not found') from exc
        elif options["config_name"]:
            try:
                configs.append(SupplierWebConfig.objects.get(name=options["config_name"]))
            except SupplierWebConfig.DoesNotExist as exc:
                raise CommandError(f'Configuration with name "{options["config_name"]}" not found') from exc
        elif options["all"]:
            configs = list(SupplierWebConfig.objects.filter(is_active=True))
            if not configs:
                self.stdout.write(self.style.WARNING("No active web configurations found"))
                return
        else:
            raise CommandError("Please specify --config-id, --config-name, or --all")

        total_processed = 0
        total_matched = 0
        total_updated = 0

        for config in configs:
            self.stdout.write(f"Processing web configuration: {config.name}")
            try:
                updater = SupplierWebPriceUpdater(config)
                if options["test"]:
                    result = updater.test_parse()
                    if result.get("success"):
                        self.stdout.write(
                            self.style.SUCCESS(
                                f"Test successful: collected {result.get('urls_total', 0)} URLs"
                            )
                        )
                    else:
                        self.stdout.write(self.style.ERROR(f"Test failed: {result.get('error')}"))
                    continue

                result = updater.update_prices()
                if result.get("success"):
                    processed = int(result.get("items_processed", 0))
                    matched = int(result.get("items_matched", 0))
                    updated = int(result.get("items_updated", 0))
                    total_processed += processed
                    total_matched += matched
                    total_updated += updated
                    self.stdout.write(
                        self.style.SUCCESS(
                            f"Updated {updated} items (matched {matched}, processed {processed})"
                        )
                    )
                else:
                    self.stdout.write(self.style.ERROR(f"Update failed: {result.get('error')}"))
            except Exception as exc:
                self.stdout.write(self.style.ERROR(f"Error processing {config.name}: {exc}"))

        if not options["test"] and configs:
            self.stdout.write(
                self.style.SUCCESS(
                    f"\nTotal: updated {total_updated}, matched {total_matched}, processed {total_processed}"
                )
            )
