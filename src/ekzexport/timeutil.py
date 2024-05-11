import datetime

from typing import Iterable, Callable, TypeVar
from zoneinfo import ZoneInfo

ZRH_TZ = ZoneInfo(key='Europe/Zurich')
UTC_TZ = ZoneInfo(key='UTC')
Input = TypeVar('Input')
Output = TypeVar('Output')


def parse_zrh_day(day: str) -> datetime.date:
    """Convert a day string into a date.

    Accepts both ISO-style YYYY-MM-DD and Swiss-style DD.MM.YYYY formats."""
    if '.' in day:
        return datetime.datetime.strptime(day, '%d.%m.%Y').replace(tzinfo=ZRH_TZ).date()
    return datetime.datetime.strptime(day, '%Y-%m-%d').replace(tzinfo=ZRH_TZ).date()


def parse_zrh_datetime(dt: str) -> datetime.datetime:
    """Convert Swiss-style DD.MM.YYYY HH:MM to datetime."""
    return datetime.datetime.strptime(dt, '%d.%m.%Y %H:%M').replace(tzinfo=ZRH_TZ)


def format_api_date(dt: datetime.date) -> str:
    """Format date as YYYY-MM-DD, i.e. what the API expects."""
    return dt.strftime("%Y-%m-%d")


def parse_api_timestamp(timestamp: int) -> datetime.datetime:
    """Parse UTC timestamp from API."""
    return datetime.datetime.strptime(str(timestamp), '%Y%m%d%H%M%S')


def convert_zrh_datetime_sequence(input: Iterable[Input], key: Callable[[Input], str],
                                  output: Callable[[datetime.datetime, Input], Output]):
    """Given a some sequence, parse ZRH datetimes in DST-aware fashion and generate an output.

    Since the API uses dates at times in Zurich local time, during the transition to winter time, an hour
    repeats. When handling such sequences, we thus need to be aware whether we're in the first or second run
    through the hour.

    This is achieved by setting fold=1 on the resulting datetime objects - beware however that comparisons and
    equality or not trivial (see PEP 495). It's better to convert to UNIX timestamps or UTC datetimes when doing so.

    :param input: Arbitrary iterable
    :param key: Callable that returns the datetime string for an item
    :param output: Callable f(datetime.datetime, item) returning an item of the result
    :returns: A generator with the output function applied to each item in the input
    """
    prev_dt = datetime.datetime(1970, 1, 1, tzinfo=UTC_TZ)
    in_fold = False
    for item in input:
        ts = key(item)
        dt = parse_zrh_datetime(ts)

        if in_fold:
            if dt.replace(fold=1).timestamp() != dt.timestamp():
                dt = dt.replace(fold=1)  # Still in fold
            else:
                in_fold = False
        elif dt < prev_dt and dt.replace(fold=1).timestamp() != dt.timestamp():
            dt = dt.replace(fold=1)
            in_fold = True

        prev_dt = dt
        yield output(dt, item)
