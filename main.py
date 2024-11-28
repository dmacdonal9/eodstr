from options import get_today_expiry, get_closest_strike
from orders import submit_adaptive_order_trailing_stop
from market_data import get_current_mid_price, get_combo_prices
from qualify import qualify_contract
from orders import create_bag
from math import isnan
import cfg


def create_strangle(symbol: str):
    """
    Creates and submits a naked strangle for the given symbol with parameters from cfg.py.
    Args:
        symbol (str): The ticker symbol (e.g., SPY, QQQ, IWM).
    """
    print(f"Processing symbol: {symbol}")

    # Fetch parameters from cfg
    symbol_params = cfg.params[symbol]
    quantity = symbol_params["quantity"]
    live_order = symbol_params["live_order"]
    exchange = symbol_params["exchange"]
    opt_exchange = symbol_params["opt_exchange"]

    # Fetch the qualified underlying contract
    und_contract = qualify_contract(
        symbol=symbol, secType=symbol_params["sec_type"], exchange=exchange, currency='USD'
    )
    current_price = get_current_mid_price(und_contract)

    if current_price is None or isnan(current_price):
        print(f"Error: Could not retrieve market data for {symbol}.")
        return

    print(f"Current price for {symbol}: {current_price}")

    # Use today’s expiry
    expiry = get_today_expiry()

    # Use get_closest_strike to determine put and call strikes
    put_strike = get_closest_strike(contract=und_contract, right='P', exchange=opt_exchange, expiry=expiry,
                                    price=current_price - symbol_params["put_strike_distance"] )
    call_strike = get_closest_strike(contract=und_contract, right='C', exchange=opt_exchange, expiry=expiry,
                                     price=current_price + symbol_params["call_strike_distance"])

    if isnan(put_strike) or isnan(call_strike):
        print(f"Error: Could not find valid strikes for {symbol}.")
        return

    print(f"Selected put strike: {put_strike}, call strike: {call_strike}")

    # Qualify option contracts for the strangle
    put_leg = qualify_contract(
        symbol=symbol, secType='OPT', lastTradeDateOrContractMonth=expiry,
        strike=put_strike, right='P', exchange=opt_exchange, currency='USD'
    )
    call_leg = qualify_contract(
        symbol=symbol, secType='OPT', lastTradeDateOrContractMonth=expiry,
        strike=call_strike, right='C', exchange=opt_exchange, currency='USD'
    )

    # Create the combo bag
    bag_contract = create_bag(
        und_contract=und_contract,
        legs=[put_leg, call_leg],
        actions=['BUY', 'BUY'],
        ratios=[1, 1]
    )

    # Retrieve combo prices
    legs = [(put_leg, 'SELL', 1), (call_leg, 'SELL', 1)]
    bid_price, mid_price, ask_price = get_combo_prices(legs)

    if bid_price == 0.0 or isnan(bid_price):
        print(f"Warning: Invalid bid price ({bid_price}) for {symbol} combo. Skipping order.")
        return

    print(f"Combo prices - Bid: {bid_price}, Mid: {mid_price}, Ask: {ask_price}")

    # Submit an adaptive limit order at the bid price
    submit_adaptive_order_trailing_stop(
        order_contract=bag_contract,
        order_type='LMT',  # Change to limit order
        action='SELL',
        is_live=live_order,
        quantity=quantity,
        stop_loss_amt=mid_price,  # Use the bid price for the limit
        limit_price=bid_price  # Explicitly set the limit price to the bid
    )
def main():
    for symbol in cfg.SYMBOLS:
        create_strangle(symbol)


if __name__ == '__main__':
    main()