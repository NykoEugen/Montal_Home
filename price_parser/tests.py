"""Tests for price_parser — SupplierFeedPriceUpdater (sofa/yml7 feed)."""
from decimal import Decimal
from unittest.mock import MagicMock, patch

from django.test import TestCase

from price_parser.services import SupplierFeedPriceUpdater, SupplierOffer


# ---------------------------------------------------------------------------
# Minimal YML XML fixture that mimics the matroluxe.ua/yml7 structure
# ---------------------------------------------------------------------------

SOFA_YML_FIXTURE = """<?xml version="1.0" encoding="UTF-8"?>
<yml_catalog date="2024-01-01 12:00">
  <shop>
    <categories>
      <category id="99883326">Дивани</category>
      <category id="99883327">Ліжка</category>
    </categories>
    <offers>
      <offer id="631" available="true">
        <name>Диван кутовий Baltika</name>
        <vendorCode>43271</vendorCode>
        <price>25770</price>
        <oldprice>27832</oldprice>
        <categoryId>99883326</categoryId>
      </offer>
      <offer id="633" available="true">
        <name>Диван Vesta двійка</name>
        <vendorCode>88776</vendorCode>
        <price>18606</price>
        <oldprice>19722</oldprice>
        <categoryId>99883326</categoryId>
      </offer>
      <offer id="708" available="true">
        <name>Диван Magnolia</name>
        <vendorCode>1-1-1-1</vendorCode>
        <price>17547</price>
        <categoryId>99883326</categoryId>
      </offer>
      <offer id="1052" available="true">
        <name>Ліжко Beverly</name>
        <vendorCode>57550</vendorCode>
        <price>15470</price>
        <categoryId>99883327</categoryId>
        <param name="Бренд">Matro</param>
        <param name="Гарантія">24 місяці</param>
      </offer>
      <offer id="9999" available="true">
        <name>Товар без ціни</name>
        <vendorCode>00000</vendorCode>
        <categoryId>99883326</categoryId>
      </offer>
    </offers>
  </shop>
</yml_catalog>
"""


def _make_config(
    article_tag_name="vendorCode",
    article_prefix_parts=0,
    update_size_variants=False,
    size_param_name="",
    price_multiplier=Decimal("1"),
    match_by_article=True,
    match_by_name=True,
):
    """Return a mock SupplierFeedConfig."""
    cfg = MagicMock()
    cfg.feed_url = "https://matroluxe.ua/index.php?route=extension/feed/yandex_yml7"
    cfg.article_tag_name = article_tag_name
    cfg.article_prefix_parts = article_prefix_parts
    cfg.update_size_variants = update_size_variants
    cfg.size_param_name = size_param_name
    cfg.price_multiplier = price_multiplier
    cfg.match_by_article = match_by_article
    cfg.match_by_name = match_by_name
    cfg.is_active = True
    cfg.name = "Matroluxe — дивани"
    return cfg


class TestSupplierFeedFetchOffers(TestCase):
    """Unit tests for _fetch_offers using a mocked HTTP response."""

    def _make_updater(self, **kwargs):
        cfg = _make_config(**kwargs)
        updater = SupplierFeedPriceUpdater(cfg)
        return updater

    @patch("price_parser.services.requests.get")
    def test_parses_offers_from_yml7_feed(self, mock_get):
        mock_get.return_value.content = SOFA_YML_FIXTURE.encode("utf-8")
        mock_get.return_value.raise_for_status = MagicMock()

        updater = self._make_updater()
        offers = updater._fetch_offers()

        # Offer without <price> must be skipped → 4 valid offers
        self.assertEqual(len(offers), 4)

    @patch("price_parser.services.requests.get")
    def test_vendor_code_read_correctly(self, mock_get):
        mock_get.return_value.content = SOFA_YML_FIXTURE.encode("utf-8")
        mock_get.return_value.raise_for_status = MagicMock()

        updater = self._make_updater()
        offers = updater._fetch_offers()

        codes = [o.model for o in offers]
        self.assertIn("43271", codes)
        self.assertIn("88776", codes)
        self.assertIn("1-1-1-1", codes)
        self.assertIn("57550", codes)

    @patch("price_parser.services.requests.get")
    def test_price_and_oldprice_parsed(self, mock_get):
        mock_get.return_value.content = SOFA_YML_FIXTURE.encode("utf-8")
        mock_get.return_value.raise_for_status = MagicMock()

        updater = self._make_updater()
        offers = updater._fetch_offers()

        baltika = next(o for o in offers if o.model == "43271")
        self.assertEqual(baltika.price, Decimal("25770"))
        self.assertEqual(baltika.old_price, Decimal("27832"))

    @patch("price_parser.services.requests.get")
    def test_offer_without_oldprice_has_none(self, mock_get):
        mock_get.return_value.content = SOFA_YML_FIXTURE.encode("utf-8")
        mock_get.return_value.raise_for_status = MagicMock()

        updater = self._make_updater()
        offers = updater._fetch_offers()

        magnolia = next(o for o in offers if o.model == "1-1-1-1")
        self.assertIsNone(magnolia.old_price)

    @patch("price_parser.services.requests.get")
    def test_no_size_variants_parsed_for_sofa_feed(self, mock_get):
        mock_get.return_value.content = SOFA_YML_FIXTURE.encode("utf-8")
        mock_get.return_value.raise_for_status = MagicMock()

        updater = self._make_updater(update_size_variants=False, size_param_name="")
        offers = updater._fetch_offers()

        for offer in offers:
            self.assertIsNone(offer.size_width)
            self.assertIsNone(offer.size_length)


class TestSupplierFeedResolvePrices(TestCase):
    """Unit tests for _resolve_prices logic (old_price → base, price → promo)."""

    def _updater(self):
        return SupplierFeedPriceUpdater(_make_config())

    def test_oldprice_becomes_base_price(self):
        offer = SupplierOffer(
            offer_id="631",
            name="Диван Baltika",
            model="43271",
            price=Decimal("25770"),
            old_price=Decimal("27832"),
        )
        updater = self._updater()
        base, promo = updater._resolve_prices(offer)
        self.assertEqual(base, Decimal("27832.00"))
        self.assertEqual(promo, Decimal("25770.00"))

    def test_no_oldprice_price_is_base(self):
        offer = SupplierOffer(
            offer_id="708",
            name="Диван Magnolia",
            model="1-1-1-1",
            price=Decimal("17547"),
            old_price=None,
        )
        updater = self._updater()
        base, promo = updater._resolve_prices(offer)
        self.assertEqual(base, Decimal("17547.00"))
        self.assertIsNone(promo)

    def test_multiplier_applied(self):
        cfg = _make_config(price_multiplier=Decimal("1.1"))
        offer = SupplierOffer(
            offer_id="1",
            name="Test",
            model="X",
            price=Decimal("10000"),
            old_price=None,
        )
        updater = SupplierFeedPriceUpdater(cfg)
        base, promo = updater._resolve_prices(offer)
        self.assertEqual(base, Decimal("11000.00"))


class TestSupplierFeedMatchOffer(TestCase):
    """Tests for _match_offer_to_furniture using an in-memory furniture index."""

    def _make_furniture(self, pk, name, article_code):
        f = MagicMock()
        f.pk = pk
        f.id = pk
        f.name = name
        f.article_code = article_code
        f.price = Decimal("1000")
        f.promotional_price = None
        f.is_promotional = False
        return f

    def _updater_with_index(self, furnitures):
        updater = SupplierFeedPriceUpdater(_make_config())
        # Build index manually instead of hitting the DB
        article_index = {}
        name_index = {}
        for furn in furnitures:
            if furn.article_code:
                key = updater._normalize_article(furn.article_code)
                article_index[key] = furn
            for variant in updater._generate_name_variants(furn.name):
                if variant:
                    name_index.setdefault(variant, []).append(furn)
        updater._furniture_index = {"article": article_index, "names": name_index}
        return updater

    def test_matches_by_vendor_code(self):
        sofa = self._make_furniture(1, "Диван кутовий Baltika", "43271")
        updater = self._updater_with_index([sofa])

        offer = SupplierOffer(
            offer_id="631",
            name="Диван кутовий Baltika",
            model="43271",
            price=Decimal("25770"),
            old_price=Decimal("27832"),
        )
        result = updater._match_offer_to_furniture(offer)
        self.assertIsNotNone(result)
        self.assertEqual(result.pk, 1)

    def test_matches_by_name_fallback(self):
        sofa = self._make_furniture(2, "Диван Magnolia", None)
        updater = self._updater_with_index([sofa])

        offer = SupplierOffer(
            offer_id="708",
            name="Диван Magnolia",
            model=None,
            price=Decimal("17547"),
            old_price=None,
        )
        result = updater._match_offer_to_furniture(offer)
        self.assertIsNotNone(result)
        self.assertEqual(result.pk, 2)

    def test_no_match_returns_none(self):
        sofa = self._make_furniture(3, "Диван Jersey", "47931")
        updater = self._updater_with_index([sofa])

        offer = SupplierOffer(
            offer_id="999",
            name="Диван Невідомий",
            model="99999",
            price=Decimal("5000"),
            old_price=None,
        )
        result = updater._match_offer_to_furniture(offer)
        self.assertIsNone(result)

    def test_article_code_with_dashes_matches(self):
        sofa = self._make_furniture(4, "Диван Chelsi", "6508-21")
        updater = self._updater_with_index([sofa])

        offer = SupplierOffer(
            offer_id="1561",
            name="Диван Chelsi",
            model="6508-21",
            price=Decimal("26054"),
            old_price=None,
        )
        result = updater._match_offer_to_furniture(offer)
        self.assertIsNotNone(result)
        self.assertEqual(result.pk, 4)


class TestSupplierFeedApplyPrices(TestCase):
    """Tests for _apply_offer_prices — verifies DB save calls and field changes."""

    def _make_furniture(self, price=Decimal("20000"), promo=None, is_promo=False):
        f = MagicMock()
        f.pk = 1
        f.price = price
        f.promotional_price = promo
        f.is_promotional = is_promo
        return f

    def _updater(self):
        return SupplierFeedPriceUpdater(_make_config())

    def test_updates_base_price(self):
        furniture = self._make_furniture(price=Decimal("20000"))
        offer = SupplierOffer(
            offer_id="1",
            name="Test",
            model="X",
            price=Decimal("18000"),
            old_price=None,
        )
        updater = self._updater()
        changed = updater._apply_offer_prices(furniture, offer)
        self.assertTrue(changed)
        self.assertEqual(furniture.price, Decimal("18000.00"))
        furniture.save.assert_called_once()

    def test_sets_promotional_price_when_oldprice_present(self):
        furniture = self._make_furniture(price=Decimal("27832"))
        offer = SupplierOffer(
            offer_id="631",
            name="Диван Baltika",
            model="43271",
            price=Decimal("25770"),
            old_price=Decimal("27832"),
        )
        updater = self._updater()
        changed = updater._apply_offer_prices(furniture, offer)
        self.assertTrue(changed)
        self.assertEqual(furniture.promotional_price, Decimal("25770.00"))
        self.assertTrue(furniture.is_promotional)

    def test_clears_promo_when_no_oldprice(self):
        furniture = self._make_furniture(
            price=Decimal("17547"),
            promo=Decimal("15000"),
            is_promo=True,
        )
        offer = SupplierOffer(
            offer_id="708",
            name="Диван Magnolia",
            model="1-1-1-1",
            price=Decimal("17547"),
            old_price=None,
        )
        updater = self._updater()
        # price unchanged but promo must be cleared
        furniture.price = Decimal("17547.00")  # already set to match
        changed = updater._apply_offer_prices(furniture, offer)
        self.assertTrue(changed)
        self.assertFalse(furniture.is_promotional)
        self.assertIsNone(furniture.promotional_price)

    def test_no_change_when_prices_equal(self):
        furniture = self._make_furniture(price=Decimal("17547.00"))
        offer = SupplierOffer(
            offer_id="708",
            name="Диван Magnolia",
            model="1-1-1-1",
            price=Decimal("17547"),
            old_price=None,
        )
        updater = self._updater()
        changed = updater._apply_offer_prices(furniture, offer)
        self.assertFalse(changed)
        furniture.save.assert_not_called()


# ---------------------------------------------------------------------------
# Vendor-code index: size variant direct matching (beds yml7)
# ---------------------------------------------------------------------------

BED_YML_FIXTURE = """<?xml version="1.0" encoding="UTF-8"?>
<yml_catalog date="2024-01-01 12:00">
  <shop>
    <categories>
      <category id="99883327">Ліжка</category>
    </categories>
    <offers>
      <offer id="34648" available="true">
        <name>Ліжко кутове Midas/Мідас (800х2000)</name>
        <vendorCode>1636</vendorCode>
        <price>18537</price>
        <categoryId>99883327</categoryId>
      </offer>
      <offer id="34786" available="true">
        <name>Ліжко кутове Brimo/Брімо (80х200)</name>
        <vendorCode>1638</vendorCode>
        <price>19069</price>
        <categoryId>99883327</categoryId>
      </offer>
      <offer id="34787" available="true">
        <name>Ліжко кутове Percy/Персі (800х2000)</name>
        <vendorCode>1639</vendorCode>
        <price>15137</price>
        <oldprice>16650</oldprice>
        <categoryId>99883327</categoryId>
      </offer>
    </offers>
  </shop>
</yml_catalog>
"""


class TestVariantVendorIndex(TestCase):
    """Tests for _get_variant_vendor_index and the two-step matching in update loop."""

    def _updater(self):
        return SupplierFeedPriceUpdater(_make_config())

    def _make_variant(self, pk, vendor_code, price=Decimal("18000")):
        variant = MagicMock()
        variant.pk = pk
        variant.vendor_code = vendor_code
        variant.price = price
        variant.promotional_price = None
        variant.is_promotional = False
        furn = MagicMock()
        furn.pk = 100 + pk
        variant.furniture = furn
        return variant

    def test_variant_found_by_vendor_code(self):
        updater = self._updater()
        v1 = self._make_variant(1, "1636")
        v2 = self._make_variant(2, "1638")
        updater._variant_vendor_index = {
            updater._normalize_article("1636"): v1,
            updater._normalize_article("1638"): v2,
        }

        idx = updater._get_variant_vendor_index()
        self.assertIn("1636", idx)
        self.assertIs(idx["1636"], v1)
        self.assertIn("1638", idx)

    def test_normalize_article_used_for_lookup(self):
        updater = self._updater()
        # Vendor codes with slashes/spaces should normalize the same way
        updater._variant_vendor_index = {
            updater._normalize_article("6508-21"): self._make_variant(3, "6508-21"),
        }
        key = updater._normalize_article("6508-21")
        self.assertIn(key, updater._get_variant_vendor_index())

    @patch("price_parser.services.requests.get")
    def test_bed_offers_parsed_from_yml_fixture(self, mock_get):
        mock_get.return_value.content = BED_YML_FIXTURE.encode("utf-8")
        mock_get.return_value.raise_for_status = MagicMock()

        updater = self._updater()
        offers = updater._fetch_offers()

        self.assertEqual(len(offers), 3)
        codes = [o.model for o in offers]
        self.assertIn("1636", codes)
        self.assertIn("1638", codes)
        self.assertIn("1639", codes)

    def test_apply_prices_on_variant_updates_variant_not_furniture(self):
        """When size_variant is passed, furniture fields must NOT change."""
        updater = self._updater()
        furniture = MagicMock()
        furniture.price = Decimal("20000")
        furniture.promotional_price = None
        furniture.is_promotional = False

        variant = MagicMock()
        variant.price = Decimal("10000")
        variant.promotional_price = None
        variant.is_promotional = False

        offer = SupplierOffer(
            offer_id="34648",
            name="Ліжко кутове Midas",
            model="1636",
            price=Decimal("18537"),
            old_price=None,
        )
        changed = updater._apply_offer_prices(furniture, offer, size_variant=variant)
        self.assertTrue(changed)
        self.assertEqual(variant.price, Decimal("18537.00"))
        # furniture.save must NOT be called — only variant.save
        furniture.save.assert_not_called()
        variant.save.assert_called_once()
