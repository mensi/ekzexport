from ekzexport.util import *


def _r(r: str) -> DayRange:
    """Test helper to create range from 'YYYY-MM-DD YYYY-MM-DD' strings."""
    start, end = r.split(' ')
    return DayRange(parse_zrh_day(start), parse_zrh_day(end))


def test_dayrange_disjoint_aligned():
    range1 = _r('2000-01-03 2000-01-09')
    range2 = _r('2000-01-17 2000-01-23')

    both = DayRangeSet([range1, range2])
    assert list(both.get_covering_weeks()) == [range1, range2]

    # The order should not matter
    both = DayRangeSet([range2, range1])
    assert list(both.get_covering_weeks()) == [range1, range2]


def test_dayrange_disjoint_unaligned():
    range1 = _r('2000-01-04 2000-01-09')
    range2 = _r('2000-01-17 2000-01-22')
    expected_range1 = _r('2000-01-03 2000-01-09')
    expected_range2 = _r('2000-01-17 2000-01-23')

    both = DayRangeSet([range1, range2])
    assert list(both.get_covering_weeks()) == [expected_range1, expected_range2]

    # The order should not matter
    both = DayRangeSet([range2, range1])
    assert list(both.get_covering_weeks()) == [expected_range1, expected_range2]


def test_dayrange_consecutive():
    range1 = _r('2000-01-03 2000-01-09')
    range2 = _r('2000-01-10 2000-01-16')

    both = DayRangeSet([range1, range2])
    assert list(both.get_covering_weeks()) == [range1, range2]

    # The order should not matter
    both = DayRangeSet([range2, range1])
    assert list(both.get_covering_weeks()) == [range1, range2]


def test_dayrange_consecutive_single_week():
    range1 = _r('2000-01-03 2000-01-05')
    range2 = _r('2000-01-06 2000-01-09')
    expected_range = _r('2000-01-03 2000-01-09')

    both = DayRangeSet([range1, range2])
    assert list(both.get_covering_weeks()) == [expected_range]

    # The order should not matter
    both = DayRangeSet([range2, range1])
    assert list(both.get_covering_weeks()) == [expected_range]


def test_dayrange_overlapping():
    range1 = _r('2000-01-04 2000-01-08')
    range2 = _r('2000-01-07 2000-01-14')
    expected_range1 = _r('2000-01-03 2000-01-09')
    expected_range2 = _r('2000-01-10 2000-01-16')

    both = DayRangeSet([range1, range2])
    assert list(both.get_covering_weeks()) == [expected_range1, expected_range2]

    # The order should not matter
    both = DayRangeSet([range2, range1])
    assert list(both.get_covering_weeks()) == [expected_range1, expected_range2]


def test_dayrange_covering():
    range1 = _r('2000-01-04 2000-01-08')
    range2 = _r('2000-01-05 2000-01-06')
    expected_range1 = _r('2000-01-03 2000-01-09')

    both = DayRangeSet([range1, range2])
    assert list(both.get_covering_weeks()) == [expected_range1]

    # The order should not matter
    both = DayRangeSet([range2, range1])
    assert list(both.get_covering_weeks()) == [expected_range1]


def test_dayrange_intersection_disjoint():
    range1 = _r('2000-01-01 2000-01-05')
    range2 = _r('2000-01-06 2000-01-10')

    intersection = DayRangeSet([range1]).intersect(DayRangeSet([range2]))
    assert len(intersection.ranges) == 0

    intersection = DayRangeSet([range2]).intersect(DayRangeSet([range1]))
    assert len(intersection.ranges) == 0


def test_dayrange_intersection_covering():
    range1 = _r('2000-01-01 2000-01-05')
    range2 = _r('2000-01-06 2000-01-10')

    range3 = _r('2000-01-01 2000-01-10')
    range4 = _r('2000-01-11 2000-01-20')

    expected_range = _r('2000-01-01 2000-01-10')

    intersection = DayRangeSet([range1, range2]).intersect(DayRangeSet([range3]))
    assert intersection.ranges == [expected_range]

    # The order shouldn't matter
    intersection = DayRangeSet([range3]).intersect(DayRangeSet([range1, range2]))
    assert intersection.ranges == [expected_range]

    # A random extra range shouldn't matter either
    intersection = DayRangeSet([range4, range3]).intersect(DayRangeSet([range1, range2]))
    assert intersection.ranges == [expected_range]


def test_dayrange_intersection_overlap_single_day():
    range1 = _r('2000-01-01 2000-01-05')
    range2 = _r('2000-01-05 2000-01-10')

    intersection = DayRangeSet([range1]).intersect(DayRangeSet([range2]))
    assert intersection.ranges == [_r('2000-01-05 2000-01-05')]


def test_dayrange_intersection_overlap():
    range1 = _r('2000-01-01 2000-01-05')
    range2 = _r('2000-01-06 2000-01-10')
    range3 = _r('2000-01-03 2000-01-08')

    intersection = DayRangeSet([range1, range2]).intersect(DayRangeSet([range3]))
    assert intersection.ranges == [range3]


def test_dayrange_subtraction_complete_cover():
    range1 = _r('2000-01-01 2000-01-03')
    range2 = _r('2000-01-07 2000-01-10')
    range3 = _r('2000-01-01 2000-01-10')

    remainder = DayRangeSet([range1, range2]).subtract(DayRangeSet([range3]))
    assert not remainder.ranges


def test_dayrange_subtraction_disjoint():
    range1 = _r('2000-01-05 2000-01-05')
    range2 = _r('2000-01-07 2000-01-10')

    pre_range = _r('2000-01-01 2000-01-04')
    mid_range = _r('2000-01-06 2000-01-06')
    post_range = _r('2000-01-11 2000-01-12')

    assert DayRangeSet([range1, range2]).subtract(DayRangeSet([pre_range])).ranges == [range1, range2]
    assert DayRangeSet([range1, range2]).subtract(DayRangeSet([mid_range])).ranges == [range1, range2]
    assert DayRangeSet([range1, range2]).subtract(DayRangeSet([post_range])).ranges == [range1, range2]

    assert DayRangeSet([range1, range2]).subtract(
        DayRangeSet([pre_range, mid_range, post_range])).ranges == [range1, range2]


def test_dayrange_subtraction_overlap():
    range1 = _r('2000-01-01 2000-01-06')
    range2 = _r('2000-01-07 2000-01-10')
    range3 = _r('2000-01-05 2000-01-08')

    expected_range1 = _r('2000-01-01 2000-01-04')
    expected_range2 = _r('2000-01-09 2000-01-10')

    remainder = DayRangeSet([range1, range2]).subtract(DayRangeSet([range3]))
    assert remainder.ranges == [expected_range1, expected_range2]


def test_large_intersection():
    range1 = _r('2000-01-01 2020-01-10')
    range2 = _r('1990-01-01 1995-01-01')
    range3 = _r('2020-01-01 2020-01-10')

    intersection = DayRangeSet([range1, range2]).intersect(DayRangeSet([range3]))
    assert intersection.ranges == [range3]
    assert list(intersection.get_covering_weeks()) == [_r('2019-12-30 2020-01-05'), _r('2020-01-06 2020-01-12')]
