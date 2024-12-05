from options import get_today_expiry, get_closest_strike
from orders import submit_adaptive_order_trailing_stop
from market_data import get_current_mid_price, get_combo_prices
from qualify import qualify_contract
from orders import create_bag
from math import isnan
import cfg


def adjust_to_tick_size(price, tick_size):
    """
    Adjusts a given price to the nearest valid tick size.
    """
    return round(round(price / tick_size) * tick_size, 2)


def round_to_nearest_dollar(price):
    """
    Rounds a price to the nearest whole dollar.
    """
    return round(price)


def get_current_price(symbol, sec_type, exchange):
    """
    Retrieves the current price of the underlying contract.
    """
    und_contract = qualify_contract(
        symbol=symbol, secType=sec_type, exchange=exchange, currency='USD'
    )
    current_price = get_current_mid_price(und_contract)

    if current_price is None or isnan(current_price):
        print(f"Error: Could not retrieve market data for {symbol}.")
        return None

    return current_price, und_contract


def get_strike_prices(und_contract, opt_exchange, expiry, rounded_price, params, min_tick):
    """
    Calculates the put and call strike prices.
    """
    put_strike = adjust_to_tick_size(
        get_closest_strike(contract=und_contract, right='P', exchange=opt_exchange, expiry=expiry,
                           price=rounded_price - params["put_strike_distance"]),
        min_tick
    )
    call_strike = adjust_to_tick_size(
        get_closest_strike(contract=und_contract, right='C', exchange=opt_exchange, expiry=expiry,
                           price=rounded_price + params["call_strike_distance"]),
        min_tick
    )

    if isnan(put_strike) or isnan(call_strike):
        print(f"Error: Could not find valid strikes for {und_contract.symbol}.")
        return None, None

    return put_strike, call_strike


def qualify_option_legs(symbol, expiry, put_strike, call_strike, opt_exchange):
    """
    Qualifies the option legs for the strangle.
    """
    put_leg = qualify_contract(
        symbol=symbol, secType='OPT', lastTradeDateOrContractMonth=expiry,
        strike=put_strike, right='P', exchange=opt_exchange, currency='USD'
    )
    call_leg = qualify_contract(
        symbol=symbol, secType='OPT', lastTradeDateOrContractMonth=expiry,
        strike=call_strike, right='C', exchange=opt_exchange, currency='USD'
    )
    return put_leg, call_leg


def create_strangle_bag_contract(symbol):
    """
    Processes a single symbol to prepare for the strangle order.
    """
    print(f"Processing symbol: {symbol}")
    params = cfg.params[symbol]

    # Fetch current price
    current_price, und_contract = get_current_price(
        symbol, params["sec_type"], params["exchange"]
    )
    if not current_price:
        return None

    # Round to nearest dollar
    rounded_price = round_to_nearest_dollar(current_price)
    print(f"Current price for {symbol}: {current_price}, Rounded price: {rounded_price}")

    # Use today's expiry
    expiry = get_today_expiry()

    # Get strike prices
    put_strike, call_strike = get_strike_prices(
        und_contract, params["opt_exchange"], expiry, rounded_price, params, params["min_tick"]
    )
    if not put_strike or not call_strike:
        return None

    print(f"Selected put strike: {put_strike}, call strike: {call_strike}")

    # Qualify option legs
    put_leg, call_leg = qualify_option_legs(
        symbol, expiry, put_strike, call_strike, params["opt_exchange"]
    )

    # Create combo bag
    bag_contract = create_bag(
        und_contract=und_contract,
        legs=[put_leg, call_leg],
        actions=['BUY', 'BUY'],
        ratios=[1, 1]
    )

    # Retrieve combo prices
    legs = [(put_leg, 'SELL', 1), (call_leg, 'SELL', 1)]
    bid_price, mid_price, ask_price =  get_combo_prices(legs)

    if bid_price == 0.0 or isnan(bid_price):
        print(f"Warning: Invalid bid price ({bid_price}) for {symbol} combo. Skipping order.")
        return None

    # Adjust prices to valid tick sizes
    min_tick = params["min_tick"]
    bid_price = adjust_to_tick_size(bid_price, min_tick)
    mid_price = adjust_to_tick_size(mid_price, min_tick)
    ask_price = adjust_to_tick_size(ask_price, min_tick)

    print(f"Combo prices - Adjusted Bid: {bid_price}, Mid: {mid_price}, Ask: {ask_price}")

    return {
        "bag_contract": bag_contract,
        "bid_price": bid_price,
        "mid_price": mid_price,
        "params": params
    }

if __name__ == '__main__':
    for symbol in cfg.SYMBOLS:
        symbol_data = create_strangle_bag_contract(symbol)
        if symbol_data:
            submit_adaptive_order_trailing_stop(
                order_contract=symbol_data["bag_contract"],
                order_type='LMT',
                action='SELL',
                is_live=symbol_data["params"]["live_order"],
                quantity=symbol_data["params"]["quantity"],
                stop_loss_amt=symbol_data["mid_price"] * cfg.stop_loss_multiplier,
                limit_price=symbol_data["bid_price"]
            )