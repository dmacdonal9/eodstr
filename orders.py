from ib_insync import LimitOrder, ComboLeg, Contract, Order, TagValue, PriceCondition, Trade
from ib_instance import ib
from datetime import datetime, timedelta
from typing import Optional
import cfg
from math import isnan

# Define the minimum tick sizes for various symbols
minTick: dict[str, float] = {
    "ES": 0.05,
    "SPX": 0.1
}

def create_bag(und_contract: Contract, legs: list, actions: list, ratios: list) -> Contract:
    print(f"Creating combo bag with parameters: {locals()}")
    bag_contract = Contract()
    bag_contract.symbol = und_contract.symbol
    bag_contract.secType = 'BAG'
    bag_contract.currency = und_contract.currency
    bag_contract.exchange = und_contract.exchange
    bag_contract.comboLegs = []

    for leg, action, ratio in zip(legs, actions, ratios):
        combo_leg = ComboLeg()
        combo_leg.conId = leg.conId
        combo_leg.action = action
        combo_leg.ratio = ratio
        combo_leg.exchange = leg.exchange
        combo_leg.openClose = 0
        bag_contract.comboLegs.append(combo_leg)

    return bag_contract

def submit_limit_order(order_contract, limit_price: float, action: str, is_live: bool, quantity: int):
    print(f"Entering function: submit_limit_order with parameters: {locals()}")
    order = LimitOrder(action=action, lmtPrice=limit_price, transmit=is_live, totalQuantity=quantity)
    print(f"Submitting order for {order_contract.symbol} at limit price {limit_price}.")
    order.orderRef = cfg.myStrategyTag

    try:
        trade = ib.placeOrder(order_contract, order)
        ib.sleep(2)

        if trade.orderStatus.status in ('Submitted', 'PendingSubmit', 'PreSubmitted', 'Filled'):
            status = f"Order sent with status: {trade.orderStatus.status}"
        else:
            status = f"Order failed with status: {trade.orderStatus.status}"
        return status
    except Exception as e:
        error_message = f"Error: Order placement failed with error: {str(e)}"
        print(error_message)
        return error_message

def create_bag(und_contract: Contract, legs: list, actions: list, ratios: list) -> Contract:
    print(f"Entering function: create_bag with parameters: {locals()}")
    bag_contract = Contract()
    bag_contract.symbol = und_contract.symbol
    bag_contract.secType = 'BAG'
    bag_contract.currency = und_contract.currency
    bag_contract.exchange = und_contract.exchange
    bag_contract.comboLegs = []

    for leg, action, ratio in zip(legs, actions, ratios):
        combo_leg = ComboLeg()
        combo_leg.conId = leg.conId
        combo_leg.action = action
        combo_leg.ratio = ratio
        combo_leg.exchange = leg.exchange
        combo_leg.openClose = 0
        bag_contract.comboLegs.append(combo_leg)

    return bag_contract

def get_active_orders():
    print(f"Entering function: get_active_orders with parameters: {locals()}")
    try:
        print("Requesting active orders from IB account...")
        active_orders = ib.reqAllOpenOrders()
        print(f"Number of active orders retrieved: {len(active_orders)}")

        for order in active_orders:
            print(f"Active Order - ID: {order.orderId}, Symbol: {order.contract.symbol}, "
                  f"Type: {order.orderType}, Quantity: {order.totalQuantity}, "
                  f"Status: {order.status}")

        return active_orders

    except Exception as e:
        print(f"Error: Failed to retrieve active orders: {e}")
        return []

def get_recently_filled_orders(timeframe='today'):
    print(f"Entering function: get_recently_filled_orders with parameters: {locals()}")
    try:
        print(f"Requesting filled orders for timeframe: {timeframe}.")
        all_trades = ib.reqExecutions()

        if timeframe == 'today':
            start_time = datetime.combine(datetime.today(), datetime.min.time())
        elif timeframe == 'yesterday':
            start_time = datetime.combine(datetime.today() - timedelta(days=1), datetime.min.time())
        else:
            try:
                start_time = datetime.strptime(timeframe, '%Y-%m-%d')
            except ValueError:
                print("Error: Invalid date format. Use 'today', 'yesterday', or 'YYYY-MM-DD'.")
                return []

        end_time = start_time + timedelta(days=1)
        filled_orders = [trade for trade in all_trades if start_time <= trade.time < end_time]
        print(f"Number of filled orders retrieved: {len(filled_orders)}")

        for trade in filled_orders:
            print(f"Filled Order - ID: {trade.order.orderId}, Symbol: {trade.contract.symbol}, "
                  f"Type: {trade.order.orderType}, Quantity: {trade.order.totalQuantity}, "
                  f"Time: {trade.time}, Fill Price: {trade.execution.avgPrice}")

        return filled_orders

    except Exception as e:
        print(f"Error: Failed to retrieve filled orders: {e}")
        return []


def submit_adaptive_order_conditional_stop(
        order_contract: Contract,
        order_type: str,
        action: str,
        is_live: bool,
        quantity: int,
        trigger_price: float,
        underlying_contract: Contract,
        limit_price: float = None
) -> Optional[Order]:
    """
    Submits a bracket order with a primary order and a conditional stop-loss order (no take profit).

    :param order_contract: The contract for the order.
    :param limit_price: Limit price for the primary order.
    :param order_type: 'LMT' or 'MKT'.
    :param action: 'BUY' or 'SELL'.
    :param is_live: Whether to transmit the order (True = live, False = staged).
    :param quantity: Number of contracts.
    :param trigger_price: Trigger price for the stop-loss order.
    :param underlying_contract: The underlying contract for the stop condition.
    :return: The parent order object if successful, None otherwise.
    """
    print(f"Entering function: submit_adaptive_order_with_bracket_stop with parameters: {locals()}")

    # Validate inputs
    if action not in ["BUY", "SELL"]:
        print(f"Error: Invalid action: {action}. Must be 'BUY' or 'SELL'.")
        return None

    if order_type not in ["MKT", "LMT"]:
        print(f"Error: Invalid order type: {order_type}. Must be 'MKT' or 'LMT'.")
        return None

    try:
        # Create the primary (entry) order
        print(f"Creating primary order with action: {action}, order type: {order_type}, limit price: {limit_price}")
        parent_order = Order(
            orderType=order_type,
            action=action,
            totalQuantity=quantity,
            tif='DAY',
            algoStrategy='Adaptive',
            orderRef=cfg.myStrategyTag,
            algoParams=[TagValue('adaptivePriority', 'Normal')],
            transmit=False  # Ensure the child order is linked before transmitting
        )

        if order_type == 'LMT':
            parent_order.lmtPrice = limit_price
            print(f"Primary order limit price set to: {limit_price}")

        # Place the primary order
        print(f"Placing primary order: {parent_order}")
        ib.placeOrder(order_contract, parent_order)
        ib.sleep(1)  # Allow time for order ID generation

        if not parent_order.orderId:
            print("Error: Primary order failed to generate an order ID.")
            return None
        print(f"Primary order placed successfully with order ID: {parent_order.orderId}")

        # Create the stop-loss order
        stop_loss_order = Order(
            orderType='STP',
            action='SELL' if action == 'BUY' else 'BUY',
            totalQuantity=quantity,
            auxPrice=trigger_price,
            parentId=parent_order.orderId,
            tif='DAY',
            transmit=is_live,  # Transmit this order when ready
            orderRef=cfg.myStrategyTag
        )

        # Set price condition for the stop-loss order
        condition = PriceCondition(
            isMore=True if action == 'SELL' else False,
            price=trigger_price,
            conId=underlying_contract.conId,
            exch=underlying_contract.exchange
        )
        stop_loss_order.conditions = [condition]
        print(f"Condition added to stop-loss order: {condition}")

        # Place the stop-loss order
        print(f"Placing stop-loss order: {stop_loss_order}")
        ib.placeOrder(order_contract, stop_loss_order)
        print("Bracket order with stop-loss submitted successfully.")

        return parent_order

    except Exception as e:
        print(f"Error: Failed to submit bracket order with stop-loss: {str(e)}")
        return None

def submit_adaptive_order(order_contract, limit_price: float = None, order_type: str = 'MKT', action: str = 'BUY', is_live: bool = False, quantity: int = 1):
    """
    Submits an adaptive order (limit or market) for the given contract and checks the status.

    Args:
        order_contract: The contract for which the order is being placed.
        limit_price: The limit price for the order (if None, a market order is placed).
        order_type: Type of order ('MKT' or 'LMT').
        action: 'BUY' or 'SELL'.
        is_live: Whether to transmit the order.
        quantity: Number of contracts.

    Returns:
        The Trade object for the submitted order or None in case of an error.
    """
    try:
        order_contract.exchange = 'SMART' # override for adaptive order type.
        print("---- Starting submit_adaptive_order ----")
        print(f"Contract Details: {order_contract}")
        print(f"Parameters -> Limit Price: {limit_price}, Order Type: {order_type}, Action: {action}, Is Live: {is_live}, Quantity: {quantity}")

        # Define Adaptive Algo parameters
        algo_params = [TagValue(tag='adaptivePriority', value='Normal')]
        print(f"Algo Params: {algo_params}")

        # Create the order object
        order = Order(
            action=action,
            orderType=order_type,
            totalQuantity=quantity,
            lmtPrice=limit_price if limit_price is not None else None,
            algoStrategy='Adaptive',
            algoParams=algo_params,
            transmit=is_live
        )
        print(f"Order created: {order}")

        # Place the order using IB
        trade = ib.placeOrder(order_contract, order)
        print("Order submitted to IB API. Waiting for status update...")

        # Sleep for 2 seconds to allow order status to propagate
        ib.sleep(2)

        # Fetch and log the final order status
        final_status = trade.orderStatus.status
        print(f"Order submitted successfully:")
        print(f"    Order ID: {trade.order.orderId}")
        print(f"    Final Status: {final_status}")
        print(f"    Filled Quantity: {trade.orderStatus.filled}, Remaining Quantity: {trade.orderStatus.remaining}")

        return trade

    except Exception as e:
        print("Error occurred during submit_adaptive_order execution:")
        print(f"    Error: {e}")
        return None

def submit_adaptive_order_trailing_stop(
        order_contract: Contract,
        order_type: str,
        action: str,
        is_live: bool,
        quantity: int,
        stop_loss_amt: float,
        limit_price: float = None
) -> Optional[tuple[Trade, Trade]]:
    """
    Submits an adaptive order with a trailing stop and returns both orders (parent and child) as Trade objects.

    Args:
        order_contract: The contract for the order.
        order_type: 'LMT' or 'MKT'.
        action: 'BUY' or 'SELL'.
        is_live: Whether to transmit the orders immediately.
        quantity: Number of contracts.
        stop_loss_amt: The trailing stop loss amount.
        limit_price: Limit price for the primary order (optional for LMT orders).

    Returns:
        A tuple of (primary_trade, trailing_stop_trade) if successful, None otherwise.
    """
    print(f"Entering function: submit_adaptive_order_trailing_stop with parameters: {locals()}")
    order_contract.exchange = 'SMART'

    if action not in ["BUY", "SELL"]:
        print(f"Error: Invalid action: {action}. Must be 'BUY' or 'SELL'.")
        return None

    if order_type not in ["MKT", "LMT"]:
        print(f"Error: Invalid order type: {order_type}. Must be 'MKT' or 'LMT'.")
        return None

    if order_type == "LMT" and (limit_price is None or isnan(limit_price)):
        print(f"Error: Must specify a limit price for adaptive LMT orders")
        return None

    # Create the primary order
    primary_order = Order(
        orderType=order_type,
        action=action,
        totalQuantity=quantity,
        tif='DAY',
        algoStrategy='Adaptive',
        orderRef=cfg.myStrategyTag,
        algoParams=[TagValue('adaptivePriority', 'Normal')],
        transmit=False  # Do not transmit yet
    )

    if order_type == 'LMT':
        primary_order.lmtPrice = limit_price

    # Place the primary order
    primary_trade = ib.placeOrder(order_contract, primary_order)
    ib.sleep(1)

    if not primary_order.orderId:
        print("Error: Primary order failed to generate an order ID.")
        return None

    # Create the trailing stop order
    trailing_stop_order = Order(
        orderType='TRAIL',
        action='SELL' if action == 'BUY' else 'BUY',
        totalQuantity=quantity,
        auxPrice=stop_loss_amt,
        parentId=primary_order.orderId,
        orderRef=cfg.myStrategyTag,
        tif='DAY',
        transmit=is_live  # Transmit live if specified
    )

    # Place the trailing stop order
    trailing_stop_trade = ib.placeOrder(order_contract, trailing_stop_order)

    if primary_trade.orderStatus.status and trailing_stop_trade.orderStatus.status:
        print("Info: Adaptive order with linked trailing stop submitted successfully.")
    else:
        print("Error: Order submission failed.")
        return None

    return primary_trade, trailing_stop_trade