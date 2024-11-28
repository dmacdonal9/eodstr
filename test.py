from market_data import get_current_mid_price
from ib_insync import IB, Contract
from ib_instance import ib
import cfg
from ib_insync import IB, Contract

def test_qualify_rut_put():

    # Define the RUT put option contract
    expiry = '20241204'
    strike = 2300.0
    exchange = 'CBOE'

    put_contract = Contract(
        symbol='RUT',
        secType='OPT',
        exchange=exchange,
        currency='USD',
        lastTradeDateOrContractMonth=expiry,
        strike=strike,
        right='P'  # 'P' for Put
    )

    # Attempt to qualify the contract
    try:
        qualified_contract = ib.qualifyContracts(put_contract)
        if qualified_contract:
            print(f"Successfully qualified contract: {qualified_contract[0]}")
        else:
            print("Error: Failed to qualify the RUT put contract.")
    except Exception as e:
        print(f"Error: Exception occurred while qualifying the contract: {e}")
    finally:
        # Disconnect from IB
        ib.disconnect()

if __name__ == "__main__":
    test_qualify_rut_put()