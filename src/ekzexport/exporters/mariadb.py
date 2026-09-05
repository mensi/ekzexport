import click
import datetime
import itertools

from ..session import Session
from ..timeutil import format_api_date, parse_api_timestamp
from ..util import pass_session, pass_data, pass_installation, Installation, DataSelection, DayRange, DayRangeSet

try:
    import pymysql
    _HAVE_MARIADB = True
except ImportError:
    _HAVE_MARIADB = False


@click.command('mariadb')
@click.option('-h', '--host', type=str, default='localhost')
@click.option('-P', '--port', type=int, default=3306)
@click.option('-u', '--user', type=str, required=True)
@click.option('-p', '--password', type=str, required=True)
@click.option('-d', '--database', type=str, required=True)
@click.option('-t', '--table', type=str, default='ekz_energy')
@pass_data
@pass_installation
@pass_session
def cli(session: Session, installation: Installation, data: DataSelection,
        host: str, port: int, user: str, password: str, database: str, table: str):
    """Export to a MariaDB/MySQL database.

    Upserts rows keyed by timestamp into --table (created automatically if it doesn't exist yet), with
    one column each for the HT and NT tariff readings.

    Only data after the latest existing row will be exported. If the table is empty, the complete range
    is exported.
    """
    if not _HAVE_MARIADB:
        raise click.UsageError('PyMySQL is not installed. Run "pip install pymysql" to get it.')

    conn = pymysql.connect(host=host, port=port, user=user, password=password, database=database, autocommit=False)
    try:
        with conn.cursor() as cursor:
            cursor.execute(
                f'CREATE TABLE IF NOT EXISTS `{table}` ('
                '`time` DATETIME NOT NULL PRIMARY KEY, `ht` DOUBLE NULL, `nt` DOUBLE NULL)')
            cursor.execute(f'SELECT MAX(`time`) FROM `{table}`')
            latest_time, = cursor.fetchone()
        conn.commit()

        requested_range = data.requested_ranges
        if latest_time is not None:
            click.echo(f'Already got data until: {format_api_date(latest_time)}', err=True)
            requested_range = requested_range.intersect(DayRangeSet([
                DayRange(latest_time.date(), datetime.date.today())]))

        if requested_range.empty:
            click.echo(f'Requested data until {format_api_date(data.requested_ranges.end)} leaves nothing to get',
                      err=True)
            return

        upsert = (f'INSERT INTO `{table}` (`time`, `ht`, `nt`) VALUES (%s, %s, %s) '
                 'ON DUPLICATE KEY UPDATE '
                 '`ht` = COALESCE(VALUES(`ht`), `ht`), `nt` = COALESCE(VALUES(`nt`), `nt`)')

        for week in itertools.islice(requested_range.get_covering_weeks(), data.limit):
            d = session.get_consumption_data(installation.id, data.data_type,
                                             format_api_date(week.start), format_api_date(week.end))
            rows = {}
            for v in d['seriesHt']['values']:
                if v['status'] == 'VALID':
                    rows.setdefault(parse_api_timestamp(v['timestamp']), {})['ht'] = float(v['value'])
            for v in d['seriesNt']['values']:
                if v['status'] == 'VALID':
                    rows.setdefault(parse_api_timestamp(v['timestamp']), {})['nt'] = float(v['value'])

            if rows:
                with conn.cursor() as cursor:
                    cursor.executemany(upsert, [
                        (ts, values.get('ht'), values.get('nt')) for ts, values in rows.items()])
                conn.commit()
            click.echo(f'Retrieved: {week.start} - {week.end}', err=True)
    finally:
        conn.close()