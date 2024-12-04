from market_data import get_current_mid_price
from spreads import find_put_spread
from qualify import qualify_contract, get_front_month_contract_date
from dteutil import get_next_contract_expiration



if __name__ == "__main__":
    # Parameters
    symbol = 'ES'
    sec_type = 'FUT'
    exchange = 'CME'
    opt_exchange='CBOE'
    mult = '50'
    contract_exp = get_next_contract_expiration(symbol)
    target_mid_price = 0.5
    target_width = 200

    contract_month = get_front_month_contract_date(symbol,
                                                   exchange,
                                                   mult,
                                                   contract_exp)

    print(f"Processing symbol: {symbol}")
    #print(f"fut_expiry: {contract_exp}")


    # Qualify the underlying contract
    #print("Qualifying underlying contract...")
    und_contract = qualify_contract(
        symbol=symbol, secType=sec_type, exchange=exchange, currency='USD', lastTradeDateOrContractMonth=contract_month
    )
    print(f"Qualified underlying contract: {und_contract}")

    # Get the current price of the underlying
    current_price = get_current_mid_price(und_contract)
    print(f"Current price: {current_price}")

    # Retrieve option chain
    #option_chain = get_option_chain(symbol, und_contract.conId, contract_exp,exchange,sectype=sec_type)

    # Find the put spread
    result = find_put_spread(und_contract,contract_exp,exchange,current_price,target_mid_price,target_width)
    if result:
        print(f"Spread Found: {result}")
    else:
        print("No suitable spread found.")