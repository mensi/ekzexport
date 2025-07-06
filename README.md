# ekzexport

This is an exporter for EKZ data provided on the http://my.ekz.ch customer portal
written in Python. It uses your credentials to login and then calls the EKZ API
the website uses to directly export the data. Data can be synced either to a CSV 
file or InfluxDB.

## Installing

Get it from PyPI:

```console
$ python -m pip install ekzexport
```

You can then use the `ekzexport` CLI.

## Example Usage

To authenticate, you can either put your credentials into a JSON file
`ekzexport.json` in your home directory:

```json
{
  "user": "myusername",
  "password": "mypassword"
}
```

If you're using a TOTP token via an authenticator app, you can create a dedicated token to use.
Click on the "can't scan QR code" link to get the code to manually enter and put it in the
JSON file so it looks similar to this:

```json
{
  "user": "myusername",
  "password": "mypassword",
  "otp": "AAAA BBBB CCCC DDDD EEEE FFFF GGGG HHHH"
}
```

Instead of the JSON config file, you can also use the `--user` and `--password` (and `--otp`) 
CLI options directly. The following examples use a JSON file.

> [!IMPORTANT]
> If you have enabled SMS as a second factor authentication,
> myEKZ will send you a code each time you run ekzexport. While you can enter it each time,
> it is more convenient to disable SMS authentication in the account settings or use a TOTP
> authenticator app.

First, list your contracts to find the installation ID of interest:

```console
$ ekzexport overview
                                        Contracts                                        
                  ╷                                      ╷              ╷
  Installation ID │ Address                              │ Move-in Date │ Move-out Date 
╺━━━━━━━━━━━━━━━━━┿━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━┿━━━━━━━━━━━━━━┿━━━━━━━━━━━━━━━╸
  123             │ Somestreet 1, 8000 Someplace         │ 2010-01-01   │ 2020-01-01
  456             │ Some Other Street 2, 8001 Otherplace │ 2020-01-02   │
                  ╵                                      ╵              ╵
```

With the installation ID, we can then figure out what kind of data is available
for your account:

```console
$ ekzexport installation 456 properties
                 Properties                 
                 ╷            ╷
  Property       │ From       │ Until      
╺━━━━━━━━━━━━━━━━┿━━━━━━━━━━━━┿━━━━━━━━━━━━╸
  CONTRACT       │ 2020-01-02 │ 2024-05-01
  SMART_METER    │ 2020-01-02 │ 2024-05-01
  VERB_15MIN     │ 2020-01-02 │ 2024-05-01
  VERB_TAG_EDM   │ 2020-01-02 │ 2024-05-01
  VERB_TAG_METER │ 2020-01-02 │ 2024-05-01
                 ╵            ╵
```

If you do not see any entry for 15 minute values, you likely have to enable
granular data on myEKZ first.

You can print consumption data to get an idea what is available:

```console
$ ekzexport installation 456 data --type PK_VERB_TAG_EDM --from 2024-04-01 --to 2024-04-02 show
                 Consumption Data                 
                      ╷        ╷        ╷
  Time                │ kWh    │ Tariff │ Status 
╺━━━━━━━━━━━━━━━━━━━━━┿━━━━━━━━┿━━━━━━━━┿━━━━━━━━╸
  2024-04-01 00:00:00 │ 12.123 │ NT     │ VALID
  2024-04-01 00:00:00 │ 10.123 │ HT     │ VALID
  2024-04-02 00:00:00 │ 12.678 │ NT     │ VALID
  2024-04-02 00:00:00 │ 8.678  │ HT     │ VALID
                      ╵        ╵        ╵
```

But the more interesting use-case is to export data. Available exporters are:

 - `csv` to sync data to a CSV file in the same format as myEKZ offers
 - `influxdb` to sync data to an InfluxDB 2.x server

The CLI's help command will provide further detail on the exporter-specific
options, for example:

```console
$ ekzexport installation 456 data export csv --help
```

## Running Exports Periodically

If you're using a Linux distribution using systemd, you can create a service
and trigger to run the export periodically. To do so, create
`/etc/systemd/system/ekzexport.service` with something like:

```ini
[Unit]
Description=Pull EKZ data

[Service]
Type=oneshot
ExecStart=/path/to/ekzexport/venv/bin/ekzexport installation 456 data export csv -f data.csv
WorkingDirectory=/path/to/ekzexport
```

This example assumes you created a Python virtualenv to install ekzexport
in (which keeps the dependencies local in the venv). You can also
set up an `OnFailure` hook to send emails in case the export fails.

A corresponding timer can look something like this in `/etc/systemd/system/ekzexport.timer`:

```ini
[Unit]
Description=Run ekzexport once a day

[Timer]
OnCalendar=*-*-* 04:00:00
RandomizedDelaySec=30m
Persistent=true

[Install]
WantedBy=timers.target
```

Please keep the randomized delay to avoid myEKZ getting a flood of requests
at exactly 04:00 every night. Remember to enable and start the timer.