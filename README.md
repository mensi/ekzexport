# ekzexport

Exporter for EKZ data provided on the http://my.ekz.ch customer portal.

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

Or use the `--user` and `--password` options. The following examples use a JSON
file.

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