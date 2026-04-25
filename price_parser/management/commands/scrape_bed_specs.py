from django.core.management.base import BaseCommand, CommandError

from price_parser.services import MatroluxeSpecScraper


class Command(BaseCommand):
    help = "Scrape bed specifications from matroluxe.ua/ua/krovati using Selenium"

    def add_arguments(self, parser):
        parser.add_argument(
            "--article-code",
            type=str,
            help="Match and save specs only for this article_code",
        )
        parser.add_argument(
            "--dry-run",
            action="store_true",
            help="Print matched specs without saving to DB",
        )
        parser.add_argument(
            "--selenium-wait",
            type=int,
            default=2,
            help="Implicit Selenium wait in seconds (default: 2)",
        )

    def handle(self, *args, **options):
        scraper = MatroluxeSpecScraper(selenium_wait=options["selenium_wait"])

        result = scraper.scrape_beds(
            dry_run=options["dry_run"],
            article_code=options.get("article_code"),
        )

        if not result.get("success"):
            raise CommandError(result.get("error", "Unknown error"))

        label = "DRY RUN — " if options["dry_run"] else ""
        self.stdout.write(
            self.style.SUCCESS(
                f"{label}Done: visited={result['product_pages_visited']}, "
                f"with_article={result['pages_with_article']}, "
                f"matched={result['matched']}, updated={result['updated']}, "
                f"errors={len(result['errors'])}"
            )
        )

        for err in result["errors"]:
            self.stdout.write(self.style.WARNING(f"  [{err.get('url', '?')}] {err.get('error')}"))
