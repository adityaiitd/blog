"""Tests for price extraction, ladder validation and the cost model."""

from __future__ import annotations

import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from forge.sourcing.cost import (  # noqa: E402
    PcbEstimate,
    build_cost_model,
    supply_risks,
)
from forge.sourcing.harvest import (  # noqa: E402
    PartQuote,
    PriceBreak,
    extract_epc,
    validate_ladder,
)

EPC_MARKUP = """
<table id="priceBreaks"><tbody><tr><th>Qty</th><th>Unit Price</th></tr>
<tr><td class="qty">1</td><td class="price">$8.81</td></tr>
<tr><td class="qty">10</td><td class="price">$6.001</td></tr>
<tr><td class="qty">3,000</td><td class="price">$3.5625</td></tr>
</tbody></table>
<p><b><span id="dkStock" productid="x">21,980</span> In Stock</b></p>
"""


class ExtractionTest(unittest.TestCase):
    def test_epc_ladder_and_stock(self):
        breaks, stock, _ = extract_epc(EPC_MARKUP)
        self.assertEqual([b.quantity for b in breaks], [1, 10, 3000])
        self.assertAlmostEqual(breaks[0].unit_price_usd, 8.81)
        self.assertAlmostEqual(breaks[-1].unit_price_usd, 3.5625)
        self.assertEqual(stock, 21980)

    def test_thousands_separator_parsed(self):
        breaks, _, _ = extract_epc(EPC_MARKUP)
        self.assertIn(3000, [b.quantity for b in breaks])


class LadderValidationTest(unittest.TestCase):
    def test_monotonic_ladder_accepted(self):
        ok, _ = validate_ladder([PriceBreak(1, 8.81), PriceBreak(100, 4.41)])
        self.assertTrue(ok)

    def test_rising_price_rejected(self):
        """The guard that caught a real bad scrape: price rising with quantity."""
        ok, reason = validate_ladder([PriceBreak(1, 1.80), PriceBreak(100, 2.74)])
        self.assertFalse(ok)
        self.assertIn("not a quantity ladder", reason)

    def test_absurd_spread_rejected(self):
        ok, _ = validate_ladder([PriceBreak(1, 500.0), PriceBreak(1000, 0.5)])
        self.assertFalse(ok)

    def test_zero_price_rejected(self):
        ok, _ = validate_ladder([PriceBreak(1, 0.0), PriceBreak(10, 0.0)])
        self.assertFalse(ok)

    def test_empty_ladder_rejected(self):
        ok, _ = validate_ladder([])
        self.assertFalse(ok)


class QuoteTest(unittest.TestCase):
    def quote(self) -> PartQuote:
        return PartQuote(
            mpn="EPC2305", manufacturer="EPC", role="switch", qty_per_cell=2,
            source="EPC", url="x",
            breaks=[PriceBreak(1, 8.81), PriceBreak(100, 4.41),
                    PriceBreak(3000, 3.5625)],
            stock=21980,
        )

    def test_price_uses_the_applicable_break(self):
        q = self.quote()
        self.assertAlmostEqual(q.price_at(1), 8.81)
        self.assertAlmostEqual(q.price_at(99), 8.81)
        self.assertAlmostEqual(q.price_at(100), 4.41)
        self.assertAlmostEqual(q.price_at(5000), 3.5625)

    def test_missing_price_returns_none(self):
        q = self.quote(); q.breaks = []
        self.assertIsNone(q.price_at(100))


class CostModelTest(unittest.TestCase):
    def quotes(self):
        priced = PartQuote(
            mpn="EPC2305", manufacturer="EPC", role="switch", qty_per_cell=2,
            source="EPC", url="x", breaks=[PriceBreak(1, 8.0), PriceBreak(100, 4.0)],
            stock=20000, status="quoted",
        )
        missing = PartQuote(
            mpn="LMG1020", manufacturer="TI", role="driver", qty_per_cell=2,
            source="TI", url="y", breaks=[], status="unavailable",
        )
        return [priced, missing]

    def test_coverage_is_reported_not_hidden(self):
        model = build_cost_model(self.quotes(), volume=1000)
        summary = model.summary()
        self.assertAlmostEqual(summary["coverage"], 0.5)
        self.assertTrue(summary["is_partial"])
        self.assertIn("LMG1020", summary["unpriced"])
        self.assertIn("floor, not an estimate", summary["caveat"])

    def test_unpriced_lines_do_not_silently_become_zero(self):
        model = build_cost_model(self.quotes(), volume=1000)
        self.assertEqual(len(model.unpriced_lines), 1)
        self.assertIsNone(model.unpriced_lines[0].extended_usd)

    def test_shared_parts_counted_once_per_converter(self):
        quotes = self.quotes()
        quotes[0].mpn = "ISO7740"
        model = build_cost_model(quotes, volume=1000,
                                 shared_per_converter={"ISO7740": 2})
        line = next(l for l in model.lines if l.mpn == "ISO7740")
        self.assertEqual(line.qty_per_converter, 2)

    def test_low_stock_raises_a_risk(self):
        quotes = self.quotes()
        quotes[0].stock = 500
        risks = supply_risks(quotes)
        self.assertTrue(any(r.severity == "high" for r in risks))


class PcbEstimateTest(unittest.TestCase):
    def test_small_multilayer_board_is_not_pennies(self):
        """Area scaling alone priced a 12-layer board at 25 cents."""
        pcb = PcbEstimate(layers=12, copper_oz=2.0, area_mm2=530.0)
        self.assertGreater(pcb.unit_cost_usd(1000), 2.0)

    def test_more_layers_cost_more(self):
        small = PcbEstimate(layers=4, copper_oz=1.0, area_mm2=530.0)
        big = PcbEstimate(layers=14, copper_oz=1.0, area_mm2=530.0)
        self.assertGreater(big.unit_cost_usd(1000), small.unit_cost_usd(1000))

    def test_heavy_copper_costs_more(self):
        light = PcbEstimate(layers=12, copper_oz=1.0, area_mm2=530.0)
        heavy = PcbEstimate(layers=12, copper_oz=4.0, area_mm2=530.0)
        self.assertGreater(heavy.unit_cost_usd(1000), light.unit_cost_usd(1000))

    def test_volume_reduces_unit_cost(self):
        pcb = PcbEstimate(layers=12, copper_oz=2.0, area_mm2=530.0)
        self.assertLess(pcb.unit_cost_usd(10000), pcb.unit_cost_usd(10))


if __name__ == "__main__":
    unittest.main()
