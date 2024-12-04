
from ib_instance import ib
from ib_insync import FuturesOption

def fetch_option_chains(und_contract, expiry, current_price):
    """
    Fetches option chains for the given underlying contract and filters strikes below the current price.
    """
    try:
        chains = ib.reqSecDefOptParams(
            und_contract.symbol, und_contract.exchange, und_contract.secType, und_contract.conId
        )
        #print(f"Info: Option chains retrieved successfully.")
    except Exception as e:
        print(f"Error: Failed to retrieve option chains: {e}")
        return None, None

    all_strikes = set()
    trading_classes = set()
    for chain in chains:
        if expiry in chain.expirations:
            strikes_below_price = [strike for strike in chain.strikes if strike < current_price]
            if not strikes_below_price:
                print(f"Warning: No strikes below current price {current_price} for trading class {chain.tradingClass}.")
            all_strikes.update(strikes_below_price)
            trading_classes.add(chain.tradingClass)

    if not all_strikes:
        print(f"Warning: No valid strikes found for expiry {expiry} and current price {current_price}.")
        return None, None

    return sorted(all_strikes), trading_classes


def create_option_contracts(und_contract, strikes, trading_classes, expiry, target_width, opt_exchange):
    """
    Creates option contracts for given strikes and trading classes.
    """
    contracts = []
    for lower_strike in strikes:
        upper_strike = lower_strike + target_width
        if upper_strike in strikes:
            for trading_class in trading_classes:
                try:
                    lower_option = FuturesOption(
                        symbol=und_contract.symbol,
                        lastTradeDateOrContractMonth=expiry,
                        strike=lower_strike,
                        right='P',
                        exchange=opt_exchange,
                        currency=und_contract.currency,
                        tradingClass=trading_class
                    )
                    upper_option = FuturesOption(
                        symbol=und_contract.symbol,
                        lastTradeDateOrContractMonth=expiry,
                        strike=upper_strike,
                        right='P',
                        exchange=opt_exchange,
                        currency=und_contract.currency,
                        tradingClass=trading_class
                    )
                    contracts.extend([lower_option, upper_option])
                except Exception as e:
                    print(f"Error: Failed to create option contracts: {e}")
                    continue
    #print(f"Info: Created {len(contracts)} option contracts for potential spreads.")
    return contracts


def qualify_option_contracts(contracts):
    """
    Qualifies option contracts using the IB API.
    """
    try:
        qualified_contracts = ib.qualifyContracts(*contracts)
        print(f"Info: Qualified {len(qualified_contracts)} contracts.")
        return qualified_contracts
    except Exception as e:
        print(f"Error: Failed to qualify contracts: {e}")
        return []


def fetch_ticker_data(qualified_contracts):
    """
    Fetches ticker data for qualified contracts.
    """
    try:
        tickers = ib.reqTickers(*qualified_contracts)
        ib.sleep(2)  # Ensure data is populated
        return {ticker.contract.conId: ticker for ticker in tickers}
    except Exception as e:
        print(f"Error: Failed to request tickers: {e}")
        return {}


def evaluate_spreads(strikes, ticker_map, qualified_contracts, target_mid_price, target_width):
    """
    Evaluates potential spreads and returns the first one meeting the criteria.
    """
    for lower_strike in strikes:
        upper_strike = lower_strike + target_width
        if upper_strike not in strikes:
            continue

        lower_ticker = ticker_map.get(next((c.conId for c in qualified_contracts if c.strike == lower_strike), None))
        upper_ticker = ticker_map.get(next((c.conId for c in qualified_contracts if c.strike == upper_strike), None))

        if not lower_ticker or not upper_ticker:
            print(f"Warning: Missing tickers for Short={lower_strike}, Long={upper_strike}.")
            continue

        # Discard options with bid or ask < 0
        if (lower_ticker.bid is None or lower_ticker.bid < 0 or
            lower_ticker.ask is None or lower_ticker.ask < 0 or
            upper_ticker.bid is None or upper_ticker.bid < 0 or
            upper_ticker.ask is None or upper_ticker.ask < 0):
            #print(f"Warning: Negative bid/ask for Short={lower_strike}, Long={upper_strike}.")
            continue

        # Calculate mid-price of the spread
        mid_price = abs((lower_ticker.bid + lower_ticker.ask) / 2 - (upper_ticker.bid + upper_ticker.ask) / 2)
        #print(f"Evaluating spread: Short={lower_strike}, Long={upper_strike}, Mid-Price={mid_price}")

        if mid_price >= target_mid_price:
            #print(f"Found suitable spread: Short={lower_strike}, Long={upper_strike}, Mid-Price={mid_price}")
            return {
                'short_strike': lower_strike,
                'long_strike': upper_strike,
                'mid_price': mid_price,
                'width': target_width,
                'short_conId': lower_ticker.contract.conId,
                'long_conId': upper_ticker.contract.conId,
                'short_bid': lower_ticker.bid,
                'short_ask': lower_ticker.ask,
                'short_expiry': lower_ticker.contract.lastTradeDateOrContractMonth,
                'long_bid': upper_ticker.bid,
                'long_ask': upper_ticker.ask,
                'long_expiry': upper_ticker.contract.lastTradeDateOrContractMonth
            }

    print("No suitable spread found.")
    return None


def find_put_spread(und_contract, expiry, opt_exchange, current_price, target_mid_price, target_width):
    """
    Orchestrates the process to find a suitable put spread.
    """
    strikes, trading_classes = fetch_option_chains(und_contract, expiry, current_price)
    if not strikes or not trading_classes:
        return None

    contracts = create_option_contracts(und_contract, strikes, trading_classes, expiry, target_width, opt_exchange)
    qualified_contracts = qualify_option_contracts(contracts)
    if not qualified_contracts:
        return None

    ticker_map = fetch_ticker_data(qualified_contracts)
    if not ticker_map:
        return None

    return evaluate_spreads(strikes, ticker_map, qualified_contracts, target_mid_price, target_width)