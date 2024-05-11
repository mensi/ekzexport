import click
import datetime
import itertools

from ..session import Session
from ..timeutil import format_api_date, parse_api_timestamp
from ..util import pass_session, pass_data, pass_installation, Installation, DataSelection, DayRange, DayRangeSet

try:
    from influxdb_client import InfluxDBClient, Point
    _HAVE_INFLUXDB = True
except ImportError:
    _HAVE_INFLUXDB = False


@click.command('influxdb')
@click.option('-c', '--config', type=str)
@click.option('-u', '--url', type=str)
@click.option('-t', '--token', type=str)
@click.option('-o', '--org', type=str, default='default')
@click.option('-b', '--bucket', type=str, required=True)
@click.option('-m', '--measurement', type=str, default='ekz_energy')
@click.option('-f', '--field', type=str, default='energy_15min')
@pass_data
@pass_installation
@pass_session
def cli(session: Session, installation: Installation, data: DataSelection,
        config: str, url: str, token: str, org: str, bucket: str,
        measurement: str, field: str):
    """Export to InfluxDB.

    You can configure the InfluxDB client either via config file by passing --config=filename.ini,
    via environment variables by passing --config=ENV or directly with the --url, --token and --org options.

    --measurement and --field can be used to control the measurement and field name of the inserted points.

    Only data after the latest existing measurement will be exported. If none is found, the complete range is exported.
    """
    if not _HAVE_INFLUXDB:
        raise click.UsageError('InfluxDB client is not installed. Run "pip install influxdb-client" to get it.')

    try:
        if config:
            if config == 'ENV':
                client = InfluxDBClient.from_env_properties()
            else:
                client = InfluxDBClient.from_config_file(config)
        else:
            if not url:
                raise click.UsageError('--url cannot be emtpy if --config is not used')
            if not token:
                raise click.UsageError('--token cannot be emtpy if --config is not used')
            client = InfluxDBClient(url=url, token=token, org=org)
    except Exception as e:
        if isinstance(e, click.ClickException):
            raise
        raise click.BadOptionUsage('config', 'Supplied options insufficient for connecting to InfluxDB')

    query_api = client.query_api()
    latest_table = query_api.query(
        f'from(bucket:"{bucket}") |> range(start: 0, stop: now()) '
        f'|> filter(fn: (r) => r["_measurement"] == "{measurement}" and r["_field"] == "{field}")'
        '|> tail(n: 1)')

    requested_range = data.requested_ranges
    if latest_table and latest_table[0].records:
        latest_time: datetime.datetime = latest_table[0].records[0].values['_time']
        click.echo(f'Already got data until: {format_api_date(latest_time)}', err=True)
        requested_range = requested_range.intersect(DayRangeSet([
            DayRange(latest_time.date(), datetime.date.today())]))

    for week in itertools.islice(requested_range.get_covering_weeks(), data.limit):
        d = session.get_consumption_data(installation.id, data.data_type,
                                         format_api_date(week.start), format_api_date(week.end))
        with client.write_api() as writer:
            for v in d['seriesHt']['values']:
                if v['status'] == 'VALID':
                    ts = parse_api_timestamp(v['timestamp'])
                    value = float(v['value'])
                    writer.write(bucket, org,
                                 Point(measurement).time(ts).field(field, value).field('niedertarif', False))
            for v in d['seriesNt']['values']:
                if v['status'] == 'VALID':
                    ts = parse_api_timestamp(v['timestamp'])
                    value = float(v['value'])
                    writer.write(bucket, org,
                                 Point(measurement).time(ts).field(field, value).field('niedertarif', True))
        click.echo(f'Retrieved: {week.start} - {week.end}', err=True)
