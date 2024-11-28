import time
import math
from ib_insync import Contract
from ib_instance import ib
from typing import Optional

def get_current_mid_price(my_contract: Contract, max_retries=3, retry_interval=1, refresh=False) -> Optional[float]:
    """
    Retrieve the midpoint price for a contract, falling back to the last or close price if bid/ask are unavailable.

    Args:
        my_contract: The contract to query.
        max_retries: Maximum number of retries for fetching data.
        retry_interval: Seconds to wait between retries.
        refresh: Whether to refresh market data.

    Returns:
        The midpoint price if available, or the last/close price as a fallback.
    """
    print(f"Entering function: get_current_mid_price with parameters: {locals()}")

    for attempt in range(max_retries):
        try:
            # Request market data
            ticker = ib.reqMktData(my_contract, '', refresh, False)
            ib.sleep(retry_interval)

            # Check for valid bid/ask prices
            if (
                ticker.bid is not None and ticker.ask is not None
                and not math.isnan(ticker.bid) and not math.isnan(ticker.ask)
                and ticker.bid != -1.0 and ticker.ask != -1.0
            ):
                mid_price = (ticker.bid + ticker.ask) / 2
                print(f"Info: Midpoint price retrieved: {mid_price}")
                return mid_price

            # Fall back to last or close price
            if ticker.last is not None and not math.isnan(ticker.last) and ticker.last != -1.0:
                print(f"Info: Bid/Ask unavailable. Using last price as fallback: {ticker.last}")
                return ticker.last

            if ticker.close is not None and not math.isnan(ticker.close) and ticker.close != -1.0:
                print(f"Info: Bid/Ask unavailable. Using close price as fallback: {ticker.close}")
                return ticker.close

            print(f"Warning: No valid data: Bid={ticker.bid}, Ask={ticker.ask}, Last={ticker.last}, Close={ticker.close}")

        except Exception as e:
            print(f"Error: Error retrieving price for {my_contract} on attempt {attempt + 1}: {e}")

        time.sleep(retry_interval)

    print(f"Error: Failed to retrieve price for {my_contract} after {max_retries} attempts.")
    return None

def round_to_tick(price, tick_size):
    print(f"Entering function: round_to_tick with parameters: {locals()}")
    return round(price / tick_size) * tick_size

def get_combo_prices(legs):
    """
    Function to retrieve bid, mid, and ask prices for a combo contract by summing individual leg prices.
    """
    print(f"Entering function: get_combo_prices with parameters: {locals()}")
    total_bid = 0.0
    total_ask = 0.0

    for leg_contract, action, ratio in legs:
        leg_contract = ib.qualifyContracts(leg_contract)[0]
        leg_ticker = ib.reqMktData(leg_contract, '', False, False)

        # Wait for market data to populate
        ib.sleep(1)
        print(f"Debug: LEG: {action} {leg_ticker.contract.strike}, Bid: {leg_ticker.bid}, Ask: {leg_ticker.ask}")

        bid = leg_ticker.bid if leg_ticker.bid is not None and not math.isnan(leg_ticker.bid) and leg_ticker.bid != -1.0 else 0.0
        ask = leg_ticker.ask if leg_ticker.ask is not None and not math.isnan(leg_ticker.ask) and leg_ticker.ask != -1.0 else 0.0

        if action.upper() == 'BUY':
            total_bid -= bid * ratio
            total_ask -= ask * ratio
        elif action.upper() == 'SELL':
            total_bid += bid * ratio
            total_ask += ask * ratio
        else:
            raise ValueError(f"Error: Invalid action {action} for leg {leg_contract.localSymbol}")

    mid = (total_bid + total_ask) / 2.0
    mid = round_to_tick(mid, 0.1)
    total_bid = round_to_tick(total_bid, 0.1)
    total_ask = round_to_tick(total_ask, 0.1)

    print(f"Info: get_combo_prices(): Returning prices: Bid: {total_bid}, Mid: {mid}, Ask: {total_ask}")
    return total_bid, mid, total_ask