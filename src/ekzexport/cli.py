import itertools
import json
import os
import os.path
import traceback

import click

from platformdirs import user_config_dir, site_config_dir
from rich.console import Console
from rich.table import Table
from rich import box

from .session import Session
from .timeutil import format_api_date
from .util import Installation, pass_installation, pass_session, DataSelection, pass_data
from .exporters import ALL_EXPORT_COMMANDS


@click.group()
@click.option('--user', default=None, help='Username')
@click.option('--password', default=None, help='Password')
@click.option('--otp', default='', help='OTP Secret')
@click.pass_context
def cli(ctx: click.Context, user: str, password: str, otp: str):
    """EKZ API client.

    The client only supports user/password login; 3rd party login providers are not supported.
    All dates are expected to be in Y-m-d notation, e.g. 2000-06-30."""
    locations = [os.curdir, os.path.expanduser('~'),
                 user_config_dir('ekzexport', roaming=True), site_config_dir('ekzexport')]

    if user is None or password is None:
        for location in locations:
            try:
                with open(os.path.join(location, 'ekzexport.json'), 'r') as f:
                    config = json.load(f)
                    user = config['user']
                    password = config['password']
                    otp = config.get('otp', '')
                    break
            except Exception as e:
                pass

    if user is None or password is None:
        click.echo('Unable to determine username and password. Either use the --user and --password options '
                   'or place them in a JSON file at one of these locations:', err=True)
        for location in locations:
            click.echo('  ' + os.path.join(location, 'ekzexport.json'), err=True)
        raise click.UsageError('Missing username or password')

    ctx.obj = ctx.with_resource(Session(user, password, otp))


@cli.command()
@pass_session
def overview(session: Session):
    """Get an overview over available contracts."""
    contracts = Table(title='Contracts', box=box.MINIMAL_HEAVY_HEAD)
    contracts.add_column('Installation ID')
    contracts.add_column('Address')
    contracts.add_column('Move-in Date')
    contracts.add_column('Move-out Date')

    for c in session.installation_selection_data['contracts']:
        address = 'N/A'
        for s in session.installation_selection_data['evbs']:
            if s['vstelle'] == c['vstelle']:
                address = (f"{s['address']['street']} {s['address']['houseNumber']}, "
                           f"{s['address']['postalCode']} {s['address']['city']}")
                break
        contracts.add_row(c['anlage'], address, c['einzdat'], c['auszdat'])

    console = Console()
    console.print(contracts)


@cli.group('installation')
@click.argument('installation_id')
@click.pass_context
def installation_group(ctx: click.Context, installation_id: str):
    """Installation-specific actions."""
    ctx.obj = Installation(installation_id)


@installation_group.command('properties')
@pass_installation
@pass_session
def installation_properties(session: Session, installation: Installation):
    """List installation properties."""
    table = Table(title='Properties', box=box.MINIMAL_HEAVY_HEAD)
    table.add_column('Property')
    table.add_column('From')
    table.add_column('Until')

    for p in session.get_installation_data(installation.id)['status']:
        table.add_row(p['property'], p['ab'], p['bis'])

    console = Console()
    console.print(table)


@installation_group.group('data')
@click.option('--type', 'data_type', default=None, metavar='TYPE',
              help='Type of consumption data to fetch. '
                   'Defaults to PK_VERB_15MIN if available, PK_VERB_TAG_EDM otherwise.')
@click.option('--from', 'date_from', default=None, metavar='YYYY-MM-DD',
              help='Date from which to start fetching data. Defaults to 7 days before to.')
@click.option('--to', 'date_to', default=None, metavar='YYYY-MM-DD',
              help='Date until which to fetch data. Defaults to the latest date with data available.')
@click.option('-l', '--limit', type=int, default=4, help='Maximum number of weeks to download.')
@pass_installation
@pass_session
@click.pass_context
def installation_data(ctx: click.Context, session: Session, installation: Installation,
                      data_type: str | None, date_from: str | None, date_to: str | None, limit: int):
    """Data retrieval actions.

    You can control the time window of data to be downloaded with the --from and --to options. If they are not
    explicitly specified, the bounds of available data reported by the API will be used. The number of weeks
    worth of data is limited to prevent unintended large downloads. Use --limit to override."""
    ctx.obj = DataSelection(session, installation.id, data_type, date_from, date_to, limit)


@installation_data.command('show')
@pass_data
@pass_installation
@pass_session
def show_installation_data(session: Session, installation: Installation, data: DataSelection):
    """Show consumption data."""
    table = Table(title='Consumption Data', box=box.MINIMAL_HEAVY_HEAD)
    table.add_column('Time')
    table.add_column('kWh')
    table.add_column('Tariff')
    table.add_column('Status')

    weekly_data = []
    for week in data.requested_weeks():
        d = session.get_consumption_data(installation.id, data.data_type,
                                         format_api_date(week.start), format_api_date(week.end))
        weekly_data.append((dict(x, tariff='NT') for x in d['seriesNt']['values']))
        weekly_data.append((dict(x, tariff='HT') for x in d['seriesHt']['values']))

    values = sorted(itertools.chain(*weekly_data), key=lambda x: x['timestamp'])
    for v in values:
        table.add_row(f'{v["date"]} {v["time"]}', str(v['value']), v['tariff'], v['status'])

    console = Console()
    console.print(table)


@installation_data.group('export')
def export_group():
    """Export consumption data."""
    pass


for cmd in ALL_EXPORT_COMMANDS:
    export_group.add_command(cmd)


def main():
    try:
        cli()
    except Exception as e:
        click.echo(click.style('An unexpected error occurred during execution:', fg='red'), err=True)
        for line in traceback.format_exception(e):
            click.echo('  ' + line, err=True)
        return 1
