import collections
import os.path

import click
from datetime import datetime
import itertools
from typing import TypedDict, List, Optional, Dict

from ..session import Session
from ..util import pass_installation, pass_data, pass_session, Installation, DataSelection, DayRange, DayRangeSet
from ..timeutil import convert_zrh_datetime_sequence, format_api_date, parse_api_timestamp, ZRH_TZ

SEP = 'sep=;'
HEADER = 'Zeitraum;HT [kWh];NT [kWh]'


class Datapoint(TypedDict):
    time: datetime
    ht: Optional[float]
    nt: Optional[float]


def read_csv(filename: str) -> List[Datapoint]:
    if not os.path.exists(filename):
        return []

    with open(filename, 'r', newline='\n') as f:
        if f.readline().strip() != SEP:
            raise Exception(f'Expected CSV file to start with {SEP}')

        if f.readline().strip() != HEADER:
            raise Exception(f'Expected CSV file to have a header like "{HEADER}"')

        return list(convert_zrh_datetime_sequence(
            (line.strip().split(';') for line in f),  # Each row is dd.mm.yyyy hh:mm;ht;nt
            lambda x: x[0],
            lambda dt, line_parts: {
                'time': dt,
                'ht': float(line_parts[1]) if line_parts[1] else None,
                'nt': float(line_parts[2]) if line_parts[2] else None,
            }
        ))


def write_csv(filename: str, data: List[Datapoint]):
    with open(filename, 'w', newline='\n') as f:
        f.write(f'{SEP}\n')
        f.write(f'{HEADER}\n')

        for dp in data:
            time = dp['time'].astimezone(ZRH_TZ).strftime('%d.%m.%Y %H:%M')  # CSV always contains local time.
            ht = str(dp['ht']) if dp.get('ht') else ''
            nt = str(dp['nt']) if dp.get('nt') else ''
            f.write(f'{time};{ht};{nt}\n')


@click.command('csv')
@click.option('-f', '--file', 'filename', type=str, required=True)
@pass_data
@pass_installation
@pass_session
def cli(session: Session, installation: Installation, data: DataSelection, filename):
    """Export data to a CSV file formatted the same as EKZ's CSV export.

    If the file already exists, only data for weeks not already present will be retrieved
    and added to the file."""
    ranges_with_data = []
    datapoints = read_csv(filename)
    current_range = None
    for dp in datapoints:
        day = dp['time'].date()
        if dp['ht'] is not None or dp['nt'] is not None:
            if current_range is None:
                current_range = DayRange(day, day)
            elif not current_range.append_consecutive(day):
                ranges_with_data.append(current_range)
                current_range = DayRange(day, day)
    if current_range is not None:
        ranges_with_data.append(current_range)

    present_set = DayRangeSet(ranges_with_data)
    new_datapoints: Dict[int, Datapoint] = collections.defaultdict(dict)
    for week in itertools.islice(data.requested_ranges.subtract(present_set).get_covering_weeks(), data.limit):
        d = session.get_consumption_data(installation.id, data.data_type,
                                         format_api_date(week.start), format_api_date(week.end))
        for v in d['seriesHt']['values']:
            if v['status'] == 'VALID':
                ts = parse_api_timestamp(v['timestamp'])
                value = float(v['value'])
                new_datapoints[int(ts.timestamp())]['time'] = ts
                new_datapoints[int(ts.timestamp())]['ht'] = value
        for v in d['seriesNt']['values']:
            if v['status'] == 'VALID':
                ts = parse_api_timestamp(v['timestamp'])
                value = float(v['value'])
                new_datapoints[int(ts.timestamp())]['time'] = ts
                new_datapoints[int(ts.timestamp())]['nt'] = value
        click.echo(f'Retrieved: {week.start} - {week.end}', err=True)

    if not new_datapoints:
        click.echo('No new valid datapoints found', err=True)
        return

    # The new points have to be merged back with the existing ones in sequence
    result = []
    new: List[Datapoint] = sorted(new_datapoints.values(), key=lambda x: x['time'].timestamp())
    i = 0
    for dp in datapoints:
        if i >= len(new) or dp['time'].timestamp() < new[i]['time'].timestamp():
            result.append(dp)  # Keep old datapoint since it's older or we don't have any new ones anymore
        elif dp['time'].timestamp() == new[i]['time'].timestamp():
            result.append(new[i])  # Overwrite old datapoint with fresh values
            i += 1
        else:
            while i < len(new) and dp['time'].timestamp() > new[i]['time'].timestamp():
                result.append(new[i])  # New datapoint is before the existing one
                i += 1
    # We could still have unconsumed new datapoints
    while i < len(new):
        result.append(new[i])
        i += 1

    write_csv(filename, result)
