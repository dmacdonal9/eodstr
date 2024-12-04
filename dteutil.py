import pytz
import pandas_market_calendars as mcal
import pandas as pd
from pandas.tseries.offsets import BDay
from datetime import datetime, timedelta, time
import cfg
from pytz import timezone

def next_market_day_mwf(start_date):

    # Convert datetime object to string in the format 'yyyy-mm-dd'
    start_date_str = start_date.strftime('%Y-%m-%d')

    # Create a calendar for NYSE
    nyse = mcal.get_calendar('NYSE')

    # Define an end date for the range, here we look one year ahead which should be more than enough
    end_date_str = (start_date + timedelta(days=30)).strftime('%Y-%m-%d')

    # Get the market schedule within the range
    market_days = nyse.schedule(start_date=start_date_str, end_date=end_date_str)

    # Find the next market day that is a Monday, Wednesday, or Friday
    for date in market_days.index:
        if date.date() > start_date.date() and date.weekday() in [0, 2, 4]:  # Check weekday
            return date.date()

    # In case no market day is found within the range (shouldn't happen with a one-year range)
    return None

def next_market_day_mindays(start_date, min_days):
    # Convert datetime object to time before market start time
    start_date = datetime.combine(start_date.date(), time(0, 0))

    # Create a calendar for NYSE
    nyse = mcal.get_calendar('NYSE')

    # Define an end date for the range. We look one year ahead which should be more than enough.
    end_date = (start_date + timedelta(days=365))

    # Get the market schedule within the range
    market_days = nyse.schedule(start_date=start_date, end_date=end_date)

    # Add business days to the start date using BDay
    target_date = pd.Timestamp(start_date) + BDay(min_days)

    # Find the next market day that is at least min_days business days away
    for date in market_days.index:
        if date >= target_date:
            return date.date()

    # In case no market day is found within the range (shouldn't happen with a one-year range)
    return None


def get_next_contract_expiration(symbol):
    # Get current datetime
    now = datetime.now()

#    if symbol in ('RTY'):
#        #print("Expiration is +2")
#        expiration = next_market_day_mindays(datetime.now(), min_days=2)
    if symbol in ['CL','MBT']:
        #print("Expiration is MWF")
        expiration = next_market_day_mwf(datetime.now())
    else:
        #print("Expiration is +1")
        expiration = next_market_day_mindays(datetime.now(), min_days=1)

    return expiration.strftime('%Y%m%d')

def is_market_open():
    # Get current datetime in EST
    est = pytz.timezone('America/New_York')
    current_datetime = datetime.now(est)
    current_day = current_datetime.weekday()
    current_time = current_datetime.time()

    # Market is closed from Friday 17:00 to Sunday 18:00
    if current_day == 4 and current_time >= time(17, 0):  # Friday post 5pm
        return False
    if current_day == 5:  # Saturday whole day
        return False
    if current_day == 6 and current_time < time(18, 0):  # Sunday pre 6pm
        return False

    # Daily trading halt from 16:15 to 16:30, Monday to Friday
    if current_day in range(0, 5) and time(16, 15) <= current_time < time(16, 30):
        return False

    return True

def safe_to_trade_fomc(exp_date):
    now = datetime.now(timezone('US/Eastern'))
    safe_time = time(14, 5)
    try:
        # Convert strings to datetime objects for comparison
        exp_date = datetime.strptime(exp_date, "%Y%m%d")
        today = datetime.today()
    except ValueError:
        return "safe_to_trade_FOMC: Incorrect date format, should be YYYYMMDD"

    # Compare each FOMC day with the input date and today
    for fomc_day in cfg.fomc_days:
        fomc_day = datetime.strptime(fomc_day, "%Y%m%d").date()

        if now.time() > safe_time and today == fomc_day:
            print("This is a FOMC day, but the time is after the release, we're OK")
            return True

        # If FOMC day falls within the range (inclusive), return False
        if today.date() <= fomc_day <= exp_date.date():
            print("safe_to_trade_FOMC returning false")
            return False
    return True


def safe_to_trade_cpi(exp_date):
    try:
        # Convert date strings to datetime objects for comparison
        exp_date = datetime.strptime(exp_date, "%Y%m%d").date()
        now = datetime.now(timezone('US/Eastern'))
    except ValueError:
        return "Incorrect date format, should be YYYYMMDD"

    today = datetime.now(timezone('US/Eastern')).date()
    safe_time = time(8, 35)

    # Compare each CPI day with the input date and today
    for cpi_day in cfg.cpi_days:
        cpi_day = datetime.strptime(cpi_day, "%Y%m%d").date()

        if now.time() < safe_time and today == cpi_day:
            print("This is a CPI day, can't trade until after 9:30 AST")
            return False

        if now.time() > safe_time and today == cpi_day:
            print("This is a CPI day, but the time is after the release, we're OK")
            return True

        # If CPI day falls within the range (inclusive), return False
        if today <= cpi_day <= exp_date:
            print(f"safe_to_trade_CPI: CPI data release pending, returning false")
            return False

    return True
