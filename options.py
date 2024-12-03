from datetime import datetime
from ib_insync import Contract, Option
from ib_instance import ib
import math
import logging

logging.getLogger('ib_insync').setLevel(logging.CRITICAL)

def get_option_chain(symbol, expiry, exchange='SMART'):
    """
    Retrieve the option chain for a given symbol and expiry.

    Args:
        symbol (str): The symbol for the underlying (e.g., 'SPX').
        expiry (str): Expiration date in 'YYYYMMDD' format.
        exchange (str): Exchange for the options.

    Returns:
        list: A list of Option contracts.
    """
    print(f"Fetching option chain for {symbol} with expiry {expiry}...")
    option_details = ib.reqContractDetails(
        Contract(symbol=symbol, secType='OPT', exchange=exchange, currency='USD', lastTradeDateOrContractMonth=expiry)
    )
    options = [detail.contract for detail in option_details]
    print(f"Retrieved {len(options)} option contracts.")
    return options

def get_closest_strike(contract, right, exchange, expiry, price):
    """
    Find the closest strike price to the given target price.

    Args:
        contract: The underlying contract.
        right: 'C' for Call, 'P' for Put.
        exchange: The exchange to query.
        expiry: Expiry date in 'YYYYMMDD' format.
        price: Target price for which the closest strike is needed.

    Returns:
        Closest strike price or NaN if none found.
    """
    print(f"Entering function: get_closest_strike with parameters: {locals()}")

    try:
        # Determine the security type
        option_secType = 'FOP' if contract.secType == 'FUT' else 'OPT'

        # Define the option contract for the request
        option_contract = Contract()
        option_contract.symbol = contract.symbol
        option_contract.secType = option_secType
        option_contract.exchange = exchange
        option_contract.currency = contract.currency
        option_contract.lastTradeDateOrContractMonth = expiry
        option_contract.right = right  # 'C' for Call, 'P' for Put

        # Fetch option chain
        option_chain = ib.reqContractDetails(option_contract)
        if not option_chain:
            print(f"Warning: No options found for symbol {contract.symbol}, expiry {expiry}, right {right}, exchange {exchange}.")
            return float('nan')

        # Log available expirations and strikes
        available_expirations = set(detail.contract.lastTradeDateOrContractMonth for detail in option_chain)
        available_strikes = [detail.contract.strike for detail in option_chain]
        print(f"Info: Available expirations for {contract.symbol} on {exchange}: {sorted(available_expirations)}")
        print(f"Info: Available strikes for {contract.symbol} on {exchange}, expiry {expiry}: {sorted(available_strikes)}")

        # Fetch tickers for all option contracts
        option_contracts = [detail.contract for detail in option_chain]
        tickers = ib.reqTickers(*option_contracts)

        # Find the closest strike to the target price
        closest_strike = None
        min_difference = float('inf')

        for option, ticker in zip(option_contracts, tickers):
            bid_price = ticker.bid
            if bid_price is None or math.isnan(bid_price):
                continue

            strike = option.strike
            difference = abs(strike - price)
            if difference < min_difference:
                min_difference = difference
                closest_strike = strike

        if closest_strike is not None:
            print(f"Info: Closest strike for price {price} and right {right} is {closest_strike}")
            return closest_strike
        else:
            print(f"Warning: No matching strike found with valid bid prices for price {price}.")
            return float('nan')

    except Exception as e:
        print(f"Error: Exception occurred while fetching closest strike: {e}")
        return float('nan')

def get_today_expiry():
    print(f"Entering function: get_today_expiry")
    return datetime.today().strftime('%Y%m%d')
    #return "20241202"


def get_atm_strike(qualified_contract, exchange, opt_exchange, expiry, current_price, secType):
    print(f"Entering function: get_atm_strike with parameters: {locals()}")
    try:
        option_contract = Contract()
        option_contract.symbol = qualified_contract.symbol
        option_contract.secType = secType
        option_contract.exchange = exchange
        option_contract.currency = qualified_contract.currency
        option_contract.lastTradeDateOrContractMonth = expiry

        option_details = ib.reqContractDetails(option_contract)
        if not option_details:
            print("Warning: No options found for the given expiry.")
            return float('nan')

        closest_strike = None
        min_difference = float('inf')

        for detail in option_details:
            strike = detail.contract.strike
            difference = abs(strike - current_price)
            if difference < min_difference:
                min_difference = difference
                closest_strike = strike

        if closest_strike is not None:
            print(f"Info: Closest ATM strike for price {current_price} is {closest_strike}")
            return closest_strike
        else:
            print("Warning: No ATM strike found.")
            return float('nan')
    except Exception as e:
        print(f"Error: Error fetching ATM strike: {e}")
        return float('nan')


def get_option_by_target_price(und_contract, right, opt_exchange, expiry, target_price, atm_strike):
    print(f"Entering function: get_option_by_target_price with parameters: {locals()}")
    try:
        chains = ib.reqSecDefOptParams(
            und_contract.symbol, '', und_contract.secType, und_contract.conId)
        print(f"Info: Option chains retrieved: {chains}")
    except Exception as e:
        print(f"Error: Error retrieving option chains: {e}")
        return None, None

    all_strikes = set()
    trading_classes = set()
    for chain in chains:
        if expiry in chain.expirations:
            if right == 'P':
                all_strikes.update([strike for strike in chain.strikes if strike <= atm_strike])
            elif right == 'C':
                all_strikes.update([strike for strike in chain.strikes if strike >= atm_strike])
            trading_classes.add(chain.tradingClass)

    if not all_strikes:
        print("Warning: No strikes found for the given expiry and ATM filtering.")
        return None, None

    strikes = sorted(all_strikes)
    contracts = []
    for strike in strikes:
        for trading_class in trading_classes:
            option = Option(
                symbol=und_contract.symbol,
                lastTradeDateOrContractMonth=expiry,
                strike=strike,
                right=right,
                exchange=opt_exchange,
                currency=und_contract.currency,
                tradingClass=trading_class)
            contracts.append(option)
    print(f"Info: Created {len(contracts)} option contracts with right '{right}' and filtered strikes.")

    qualified_contracts = ib.qualifyContracts(*contracts)

    if not qualified_contracts:
        print("Warning: No qualified contracts found.")
        return None, None

    tickers = ib.reqTickers(*qualified_contracts)
    ib.sleep(2)

    valid_options = []
    for ticker in tickers:
        if right == 'P' and ticker.ask != float('inf') and ticker.ask > 0:
            valid_options.append((ticker.contract, ticker.ask))
        elif right == 'C' and ticker.bid != float('inf') and ticker.bid > 0:
            valid_options.append((ticker.contract, ticker.bid))

    if not valid_options:
        print("Warning: No options with valid ask/bid prices found.")
        return None, None

    if right == 'P':
        min_diff = min(abs(ask - target_price) for _, ask in valid_options)
        closest_options = [(contract, ask) for contract, ask in valid_options if abs(ask - target_price) == min_diff]
    else:
        min_diff = min(abs(bid - target_price) for _, bid in valid_options)
        closest_options = [(contract, bid) for contract, bid in valid_options if abs(bid - target_price) == min_diff]

    print(f"Info: Options with minimum price difference: {closest_options}")

    if right == 'P':
        closest_options.sort(key=lambda x: x[0].strike, reverse=True)
    else:
        closest_options.sort(key=lambda x: x[0].strike, reverse=False)

    selected_option = closest_options[0][0]
    selected_price = closest_options[0][1]

    print(f"Info: Option closest to target price found: {selected_option} with bid/ask price {selected_price}")

    return selected_option, selected_price