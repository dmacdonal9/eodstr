from market_data import get_current_mid_price
from ib_instance import ib
from math import isnan
from qualify import qualify_contract
from itertools import combinations
from options import get_option_chain, get_today_expiry

def find_put_spread(option_chain, current_price, target_mid_price, target_width, batch_size=50):
    """
    Finds the first put spread with a mid-price greater than or equal to the target price and a specified width.

    Args:
        option_chain (list): List of Option contracts.
        current_price (float): Current market price of the underlying.
        target_mid_price (float): Minimum desired mid-price of the spread.
        target_width (int): Desired width of the spread (e.g., 500 strikes).
        batch_size (int): Maximum number of market data requests per batch.

    Returns:
        dict: A dictionary with details of the spread, or None if no spread is found.
    """
    print("Filtering for puts below current market price...")
    puts = [opt for opt in option_chain if opt.right == 'P' and opt.strike < current_price]
    print(f"Filtered {len(puts)} put options below market price ({current_price}).")

    # Sort puts by strike price for combination logic
    puts = sorted(puts, key=lambda x: x.strike)

    # Search for put pairs with the correct width
    potential_spreads = [
        (lower, upper)
        for lower, upper in combinations(puts, 2)
        if upper.strike - lower.strike == target_width
    ]

    if not potential_spreads:
        print("No spreads with the desired width found.")
        return None
    else:
        print(f"Found {len(potential_spreads)} potential spreads matching the width.")

    # Batch processing of market data requests
    print("Requesting market data in batches...")
    for batch_start in range(0, len(potential_spreads), batch_size):
        batch = potential_spreads[batch_start:batch_start + batch_size]
        market_data = {}
        active_tickers = []

        # Request market data for the current batch
        for lower, upper in batch:
            if lower.conId not in market_data:
                lower_ticker = ib.reqMktData(lower)
                market_data[lower.conId] = lower_ticker
                active_tickers.append(lower_ticker)
            if upper.conId not in market_data:
                upper_ticker = ib.reqMktData(upper)
                market_data[upper.conId] = upper_ticker
                active_tickers.append(upper_ticker)

        # Allow time for market data to populate
        print(f"Processing batch {batch_start // batch_size + 1}...")
        ib.sleep(2)

        # Evaluate spreads in the current batch
        for lower, upper in batch:
            lower_ticker = market_data.get(lower.conId)
            upper_ticker = market_data.get(upper.conId)

            # Skip if bid/ask data is missing
            if not (lower_ticker and upper_ticker and
                    lower_ticker.bid is not None and lower_ticker.ask is not None and
                    upper_ticker.bid is not None and upper_ticker.ask is not None):
                print(f"Skipping spread: Short={lower.strike}, Long={upper.strike} due to missing bid/ask.")
                continue

            # Calculate mid-price
            mid_price = abs((lower_ticker.bid + lower_ticker.ask) / 2 - (upper_ticker.bid + upper_ticker.ask) / 2)

            if not isnan(mid_price) and mid_price > 0:
                print(f"Evaluating spread: Short={lower.strike}, Long={upper.strike}, Width={target_width}, Mid-Price={mid_price}")
                if mid_price >= target_mid_price:
                    print(f"Found suitable spread: Short={lower.strike}, Long={upper.strike}, Mid-Price={mid_price}")

                    # Cancel market data before returning
                    for ticker in active_tickers:
                        ib.cancelMktData(ticker.contract)

                    return {
                        'short_strike': lower.strike,
                        'long_strike': upper.strike,
                        'mid_price': mid_price,
                        'width': target_width,
                        'short_conId': lower.conId,
                        'long_conId': upper.conId
                    }

        # Cancel market data for the current batch
        print(f"Cancelling market data for batch {batch_start // batch_size + 1}...")
        for ticker in active_tickers:
            ib.cancelMktData(ticker.contract)

    print("No suitable spread found.")
    return None


if __name__ == "__main__":
    # Parameters
    symbol = 'ES'
    sec_type = 'FUT'
    exchange = 'CBOE'
    expiry = get_today_expiry()
    target_mid_price = 0.5
    target_width = 200

    print(f"Processing symbol: {symbol}")

    # Qualify the underlying contract
    print("Qualifying underlying contract...")
    und_contract = qualify_contract(
        symbol=symbol, secType=sec_type, exchange=exchange, currency='USD'
    )
    print(f"Qualified underlying contract: {und_contract}")

    # Get the current price of the underlying
    current_price = get_current_mid_price(und_contract)
    print(f"Current price: {current_price}")

    # Retrieve option chain
    option_chain = get_option_chain(symbol, expiry, exchange)

    # Find the put spread
    result = find_put_spread(option_chain, current_price, target_mid_price, target_width, batch_size=10)
    if result:
        print(f"Spread Found: {result}")
    else:
        print("No suitable spread found.")