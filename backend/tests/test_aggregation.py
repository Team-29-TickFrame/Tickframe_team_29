import unittest
from decimal import Decimal

from hypothesis import given, strategies as st

from backend.app.aggregation import CandleAggregator
from backend.app.models import Trade


def trade(
    trade_id: str,
    timestamp_ms: int,
    price: str,
    quantity: str = "1",
) -> Trade:
    return Trade(
        exchange="binance",
        market_type="spot",
        instrument_id="BTC-USDT",
        exchange_symbol="BTCUSDT",
        trade_id=trade_id,
        exchange_timestamp_ms=timestamp_ms,
        received_timestamp_ms=timestamp_ms + 20,
        price=Decimal(price),
        base_quantity=Decimal(quantity),
        side="buy",
    )


STREAM = ("binance", "spot", "BTC-USDT")


class CandleAggregatorTests(unittest.TestCase):
    def test_out_of_order_trades_keep_event_time_ohlc(self) -> None:
        aggregator = CandleAggregator()
        aggregator.add_trade(trade("2", 1_200, "100", "2"), 1_220)
        aggregator.add_trade(trade("1", 1_100, "90", "1"), 1_230)
        aggregator.add_trade(trade("3", 1_800, "105", "3"), 1_830)

        candles = aggregator.finalize_due(4_000, [STREAM])

        self.assertEqual(len(candles), 1)
        candle = candles[0]
        self.assertEqual(candle.open, Decimal("90"))
        self.assertEqual(candle.high, Decimal("105"))
        self.assertEqual(candle.low, Decimal("90"))
        self.assertEqual(candle.close, Decimal("105"))
        self.assertEqual(candle.base_volume, Decimal("6"))
        self.assertEqual(candle.quote_volume, Decimal("605"))
        self.assertEqual(candle.trade_count, 3)
        self.assertEqual(candle.status, "complete")

    def test_duplicate_trade_does_not_double_volume(self) -> None:
        aggregator = CandleAggregator()
        value = trade("7", 1_100, "10", "2")

        aggregator.add_trade(value, 1_120)
        aggregator.add_trade(value, 1_130)
        candle = aggregator.finalize_due(4_000, [STREAM])[0]

        self.assertEqual(candle.trade_count, 1)
        self.assertEqual(candle.base_volume, Decimal("2"))

    def test_connected_stream_creates_complete_empty_candle(self) -> None:
        aggregator = CandleAggregator()
        aggregator.add_trade(trade("1", 1_100, "10"), 1_120)
        first = aggregator.finalize_due(4_000, [STREAM])
        second = aggregator.finalize_due(5_000, [STREAM])

        self.assertEqual(first[0].open_time_ms, 1_000)
        self.assertEqual(second[0].open_time_ms, 2_000)
        self.assertEqual(second[0].status, "complete_empty")
        self.assertEqual(second[0].open, Decimal("10"))
        self.assertEqual(second[0].base_volume, Decimal("0"))

    def test_late_trade_creates_new_revision(self) -> None:
        aggregator = CandleAggregator()
        aggregator.add_trade(trade("1", 1_100, "10"), 1_120)
        original = aggregator.finalize_due(4_000, [STREAM])[0]

        revised = aggregator.add_trade(trade("2", 1_900, "12"), 4_100)

        self.assertIsNotNone(revised)
        assert revised is not None
        self.assertEqual(original.revision, 1)
        self.assertEqual(revised.revision, 2)
        self.assertEqual(revised.status, "recovered")
        self.assertEqual(revised.close, Decimal("12"))
        self.assertEqual(revised.trade_count, 2)

    def test_disconnect_gap_is_not_filled_with_previous_price(self) -> None:
        aggregator = CandleAggregator()
        aggregator.add_trade(trade("1", 1_100, "10"), 1_120)
        aggregator.finalize_due(4_000, [STREAM])
        aggregator.mark_gap(STREAM, 2_000, 4_000)

        candles = aggregator.finalize_due(6_000, [STREAM])

        self.assertEqual([candle.open_time_ms for candle in candles], [2_000, 3_000])
        for candle in candles:
            self.assertEqual(candle.status, "incomplete")
            self.assertIsNone(candle.open)
            self.assertIsNone(candle.high)
            self.assertIsNone(candle.low)
            self.assertIsNone(candle.close)
            self.assertEqual(candle.trade_count, 0)

    def test_recovered_trade_revises_an_incomplete_gap_candle(self) -> None:
        aggregator = CandleAggregator()
        aggregator.add_trade(trade("1", 1_100, "10"), 1_120)
        aggregator.finalize_due(4_000, [STREAM])
        aggregator.mark_gap(STREAM, 2_000, 3_000)
        aggregator.finalize_due(5_000, [STREAM])

        recovered = aggregator.add_trade(trade("2", 2_500, "11"), 5_100)

        self.assertIsNotNone(recovered)
        assert recovered is not None
        self.assertEqual(recovered.open_time_ms, 2_000)
        self.assertEqual(recovered.status, "recovered")
        self.assertEqual(recovered.revision, 2)
        self.assertEqual(recovered.open, Decimal("11"))

    def test_numeric_trade_ids_are_sorted_numerically(self) -> None:
        aggregator = CandleAggregator()
        aggregator.add_trade(trade("10", 1_500, "10"), 1_520)
        aggregator.add_trade(trade("2", 1_500, "2"), 1_530)

        candle = aggregator.finalize_due(4_000, [STREAM])[0]

        self.assertEqual(candle.open, Decimal("2"))
        self.assertEqual(candle.close, Decimal("10"))

    @given(
        prices=st.lists(
            st.integers(min_value=1, max_value=1_000_000),
            min_size=1,
            max_size=50,
        )
    )
    def test_ohlc_invariants_hold_for_any_positive_prices(self, prices: list) -> None:
        aggregator = CandleAggregator()
        for index, price_value in enumerate(prices):
            aggregator.add_trade(
                trade(
                    str(index),
                    1_000 + index % 999,
                    str(price_value),
                ),
                2_100 + index,
            )

        candle = aggregator.finalize_due(4_000, [STREAM])[0]

        self.assertGreaterEqual(candle.high, candle.open)
        self.assertGreaterEqual(candle.high, candle.close)
        self.assertLessEqual(candle.low, candle.open)
        self.assertLessEqual(candle.low, candle.close)
        self.assertGreaterEqual(candle.high, candle.low)


if __name__ == "__main__":
    unittest.main()
