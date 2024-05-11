import itertools

import click
import datetime

from functools import cached_property
from typing import Optional, List, Dict, Iterable

from .session import Session
from .apitypes import IDProperty
from .timeutil import parse_zrh_day


class DayRange:
    """A range of days, including both start and end dates."""
    def __init__(self, start: datetime.date, end: datetime.date):
        assert isinstance(start, datetime.date)
        assert isinstance(end, datetime.date)
        self.start = start
        self.end = end

    def append_consecutive(self, day: datetime.date) -> bool:
        """If the day is consecutive or already included, extend the range if needed. Otherwise, return False."""
        if self.start <= day <= self.end:
            return True
        if self.end + datetime.timedelta(days=1) == day:
            self.end = day
            return True
        return False

    def __eq__(self, other):
        return self.start == other.start and self.end == other.end

    def __repr__(self):
        return f"DayRange({repr(self.start)}, {repr(self.end)})"


def normalize_ranges(ranges: List[DayRange]) -> List[DayRange]:
    """Merges overlapping and consecutive ranges into a single range."""
    if not ranges:
        return ranges

    result = []
    current_range = DayRange(ranges[0].start, ranges[0].end)
    for r in ranges[1:]:
        if current_range.end + datetime.timedelta(days=1) >= r.start:
            current_range.end = r.end
        else:
            result.append(current_range)
            current_range = DayRange(r.start, r.end)
    result.append(current_range)
    return result


class DayRangeSet:
    def __init__(self, ranges: Iterable[DayRange]):
        self.ranges = normalize_ranges(sorted(ranges, key=lambda r: r.start))

    def get_days(self):
        """Iterate over every day in the included ranges in increasing order."""
        cur = datetime.date(1900, 1, 1)
        for r in self.ranges:
            # Ranges can overlap, so we only jump to the start if it is in the future
            if r.start > cur:
                cur = r.start
            while cur <= r.end:
                yield cur
                cur += datetime.timedelta(days=1)

    def get_covering_weeks(self):
        """Get DayRanges from Monday to Sunday to cover all days in all ranges."""
        prev_monday = datetime.date(1900, 1, 1)
        for r in self.ranges:
            monday = r.start - datetime.timedelta(days=r.start.weekday())
            if monday == prev_monday:
                # We already had this week, skip ahead
                monday = monday + datetime.timedelta(days=7)
                if monday > r.end:
                    # Already covered the whole range
                    continue

            while True:
                sunday = monday + datetime.timedelta(days=6)
                yield DayRange(monday, sunday)
                prev_monday = monday
                monday += datetime.timedelta(days=7)
                if sunday >= r.end:
                    break

    def intersect(self, other: 'DayRangeSet') -> 'DayRangeSet':
        """Return a DateRangeSet that contains only days present in both sets."""
        ranges = []
        i, j = 0, 0
        while i < len(self.ranges) and j < len(other.ranges):
            if self.ranges[i].end < other.ranges[j].start:
                i += 1  # our range is completely before the other
            elif self.ranges[i].start > other.ranges[j].end:
                j += 1  # our range is completely after the other
            else:
                # We have some sort of overlap.
                start = max(self.ranges[i].start, other.ranges[j].start)
                end = min(self.ranges[i].end, other.ranges[j].end)
                ranges.append(DayRange(start, end))
                # The range that ends earlier gets fully consumed
                if self.ranges[i].end < other.ranges[j].end:
                    i += 1
                elif self.ranges[i].end > other.ranges[j].end:
                    j += 1
                else:  # Both end on the same day -> both consumed
                    i += 1
                    j += 1
        return DayRangeSet(ranges)

    def subtract(self, other: 'DayRangeSet') -> 'DayRangeSet':
        """Return a DateRangeSet that contains only days present in this set but not other."""
        ranges = []
        i, j = 0, 0
        while i < len(self.ranges) and j < len(other.ranges):
            if self.ranges[i].end < other.ranges[j].start:
                ranges.append(self.ranges[i])  # our range is completely before the other --> keep it
                i += 1
            elif self.ranges[i].start > other.ranges[j].end:
                j += 1  # our range is completely after the other
            else:
                # We have some sort of overlap.
                start = self.ranges[i].start
                for r in other.ranges[j:]:
                    if start < r.start:
                        # Keep part before overlapping range
                        ranges.append(DayRange(start, r.start - datetime.timedelta(days=1)))
                    start = r.end + datetime.timedelta(days=1)
                    if start > self.ranges[i].end:
                        break
                if start <= self.ranges[i].end:
                    # Keep any reminder
                    ranges.append(DayRange(start, self.ranges[i].end))
                i += 1  # our range is consumed, but the other range could still overlap the next one.
        # Any ranges we haven't consumed yet can be kept
        ranges.extend(self.ranges[i:])
        return DayRangeSet(ranges)

    def __repr__(self):
        return f'DayRangeSet({repr(self.ranges)})'


class Installation:
    """CLI context for tracking the selected installation."""
    id: str

    def __init__(self, installation_id: str):
        self.id = installation_id


class DataSelection:
    """CLI context for tracking the time-range of interest and available data."""
    _session: Session
    _installation_id: str
    _data_type: Optional[str]
    _date_from: Optional[str]
    _date_to: Optional[str]
    limit: int

    def __init__(self, session: Session, installation_id: str, data_type: Optional[str],
                 date_from: Optional[str], date_to: Optional[str], limit: int):
        self._session = session
        self._installation_id = installation_id
        self._data_type = data_type
        self._date_from = date_from
        self._date_to = date_to
        self.limit = limit

    @cached_property
    def _properties(self) -> List[IDProperty]:
        return self._session.get_installation_data(self._installation_id)['status']

    @cached_property
    def _mapped_properties(self) -> Dict[str, IDProperty]:
        return {x['property']: x for x in self._properties}

    @cached_property
    def data_type(self):
        if self._data_type:
            return self._data_type

        if 'VERB_15MIN' in self._mapped_properties:
            return 'PK_VERB_15MIN'
        else:
            return 'PK_VERB_TAG_EDM'

    @cached_property
    def property_key(self) -> str:
        # The type used in the API and the property key seem to differ by a PK_ prefix...
        pkey = self.data_type
        if pkey.startswith('PK_'):
            pkey = pkey[3:]
        return pkey

    @cached_property
    def date_to(self) -> str:
        if self._date_to:
            return self._date_to
        return self._mapped_properties[self.property_key]['bis'] or datetime.date.today().strftime('%Y-%m-%d')

    @cached_property
    def date_from(self) -> str:
        if self._date_from:
            return self._date_from
        return (datetime.datetime.strptime(self.date_to, '%Y-%m-%d').date() -
                datetime.timedelta(days=7)).strftime('%Y-%m-%d')

    @cached_property
    def explicit_daterange(self) -> bool:
        return self._date_from is not None or self._date_to is not None

    @cached_property
    def earliest_day(self) -> str:
        return self._mapped_properties[self.property_key]['ab'] or None

    @cached_property
    def latest_day(self) -> str:
        return self._mapped_properties[self.property_key]['bis'] or None

    @cached_property
    def available_ranges(self) -> DayRangeSet:
        return DayRangeSet([DayRange(parse_zrh_day(x['ab']), parse_zrh_day(x['bis'])) for
                            x in self._properties if x['property'] == self.property_key])

    @cached_property
    def requested_ranges(self) -> DayRangeSet:
        if self.explicit_daterange:
            return DayRangeSet([DayRange(parse_zrh_day(self.date_from), parse_zrh_day(self.date_to))])
        return self.available_ranges

    def requested_weeks(self) -> Iterable[DayRange]:
        if (len(self.requested_ranges.ranges) == 1 and
                (self.requested_ranges.ranges[0].end - self.requested_ranges.ranges[0].start).days <= 7):
            return [self.requested_ranges.ranges[0]]  # Requested a week or less, so just return that.
        return itertools.islice(self.requested_ranges.get_covering_weeks(), self.limit)


pass_session = click.make_pass_decorator(Session)
pass_installation = click.make_pass_decorator(Installation)
pass_data = click.make_pass_decorator(DataSelection)
