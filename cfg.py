SYMBOLS = ['SPY', 'QQQ']
SYMBOLS = ['IWM']
myStrategyTag = 'eodstr'
stop_loss_multiplier = 1.5

# IBKR Connection Parameters
ib_host = '127.0.0.1'
ib_port = 7496  # Port should be an integer
ib_clientid = 1  # Client ID should also be an integer

params = {
    'SPY': {
        "conid": 756733,
        "quantity": 1,
        "min_tick": 0.01,
        "live_order": True,
        "exchange": 'SMART',
        "opt_exchange": 'CBOE',
        "sec_type": 'STK',
        "mult": '1',
        "call_strike_distance": 1,  # Strike offset for long strikes
        "put_strike_distance": 1,  # Strike offset for short strikes
    },
    'IWM': {
        "conid": 9579970,
        "quantity": 2,
        "min_tick": 0.01,
        "live_order": True,
        "exchange": 'SMART',
        "opt_exchange": 'CBOE',
        "sec_type": 'STK',
        "mult": '1',
        "call_strike_distance": 1,  # Strike offset for long strikes
        "put_strike_distance": 1,  # Strike offset for short strikes
    },
    'QQQ': {
        "conid": 320227571,
        "quantity": 1,
        "min_tick": 0.01,
        "live_order": True,
        "exchange": 'SMART',
        "opt_exchange": 'CBOE',
        "sec_type": 'STK',
        "mult": '1',
        "call_strike_distance": 1,  # Strike offset for long strikes
        "put_strike_distance": 1,  # Strike offset for short strikes

    }
}