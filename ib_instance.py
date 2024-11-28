from ib_insync import IB
import time
import cfg


# Initialize IB instance
ib = IB()

# Variables for retry mechanism
max_retries = 5  # Maximum number of retries if the connection fails
retry_interval = 2  # Time (in seconds) to wait between retries

# Try to connect
for attempt in range(max_retries):
    try:
        print(f"Attempt {attempt + 1} to connect to Interactive Brokers...")
        ib.connect(cfg.ib_host, cfg.ib_port, cfg.ib_clientid, readonly=False)
        print('Successfully connected to Interactive Brokers!')
        break
    except Exception as e:
        print(f'Failed to connect to pers Interactive Brokers on attempt {attempt + 1}. Error: {str(e)}')
        if attempt < max_retries - 1:  # No need to sleep on the last attempt
            time.sleep(retry_interval)
