from ekzexport.timeutil import *


def test_convert_zrh_datetime_sequence():
    times = [
        '29.10.2023 01:59',
        '29.10.2023 02:00',
        '29.10.2023 02:01',
        '29.10.2023 02:00',
        '29.10.2023 02:01',
        '29.10.2023 03:00',
    ]
    output = convert_zrh_datetime_sequence(
        times,
        lambda x: x,
        lambda dt, x: dt.timestamp())
    assert list(output) == [
        1698537540.0,
        1698537600.0,  # + 60
        1698537660.0,  # + 60
        1698541200.0,  # + 59*60
        1698541260.0,  # + 60
        1698544800.0,  # + 59*60
    ]
