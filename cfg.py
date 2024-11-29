SYMBOLS = ['SPY', 'QQQ', 'IWM']
myStrategyTag = 'eodstr'

# IBKR Connection Parameters
ib_host = '127.0.0.1'
ib_port = 7497  # Port should be an integer
ib_clientid = 1  # Client ID should also be an integer

params = {
    'SPY': {
        "quantity": 1,
        "min_tick": 0.01,
        "live_order": False,
        "exchange": 'CBOE',
        "opt_exchange": 'CBOE',
        "sec_type": 'STK',
        "mult": '1',
        "call_strike_distance": 1,  # Percentage offset for long strikes
        "put_strike_distance": 1, # Percentage offset for short strikes
    },
    'IWM': {
        "quantity": 2,
        "min_tick": 0.01,
        "live_order": False,
        "exchange": 'CBOE',
        "opt_exchange": 'CBOE',
        "sec_type": 'STK',
        "mult": '1',
        "call_strike_distance": 1,  # Percentage offset for long strikes
        "put_strike_distance": 1, # Percentage offset for short strikes
    },
    'QQQ': {
        "quantity": 1,
        "min_tick": 0.01,
        "live_order": False,
        "exchange": 'CBOE',
        "opt_exchange": 'CBOE',
        "sec_type": 'STK',
        "mult": '1',
        "call_strike_distance": 1,  # Percentage offset for long strikes
        "put_strike_distance": 1, # Percentage offset for short strikes

    }
}