from dipdup.prometheus import Counter
from dipdup.prometheus import Gauge
from dipdup.prometheus import Histogram


def test_counter_math() -> None:
    counter1 = Counter('test_counter1', 'Test Counter 1')
    counter2 = Counter('test_counter2', 'Test Counter 2')

    counter1 += 5
    counter2 += 10

    assert counter1.value == 5.0
    assert counter2.value == 10.0

    result = counter1 + counter2
    assert result == 15.0

    result = counter1 + 5
    assert result == 10.0

    result = counter1 - 5
    assert result == 0


def test_counter_setitem() -> None:
    counter = Counter('test_counter', 'Test Counter', ['label'])

    # Test setting value for a specific label set (should raise TypeError)
    try:
        counter['label1'] = 5.0
    except TypeError as e:
        assert str(e) == 'Counters can only be incremented, use the += operator or the `inc` method instead'


def test_gauge_math() -> None:
    gauge1 = Gauge('test_gauge1', 'Test Gauge 1')
    gauge2 = Gauge('test_gauge2', 'Test Gauge 2')

    gauge1 += 5
    gauge2 += 10.0

    assert gauge1.value == 5.0
    assert gauge2.value == 10.0

    result = gauge1 + gauge2
    assert result == 15.0

    result = gauge1 + 5
    assert result == 10.0

    result = gauge1 - 5.0
    assert result == 0


def test_gauge_setitem() -> None:
    gauge = Gauge('test_gauge', 'Test Gauge', ['label'])

    # Test setting value for a specific label set
    gauge['label1'] = 5.0
    assert gauge['label1'].value == 5.0

    gauge['label2'] = 10.0
    assert gauge['label2'].value == 10.0

    # Test incrementing value for a specific label set
    gauge['label1'] += 5.0
    assert gauge['label1'].value == 10.0

    # Test decrementing value for a specific label set
    gauge['label2'] -= 5.0
    assert gauge['label2'].value == 5.0

    # Test setting value with a Gauge instance (should raise TypeError)
    try:
        gauge['label1'] = gauge
    except TypeError as e:
        assert str(e) == 'Cannot reassign a Gauge with another Gauge'

    # Test setting value for a non-parent Gauge (should raise TypeError)
    non_parent_gauge = Gauge('non_parent_gauge', 'Non Parent Gauge')
    try:
        non_parent_gauge['label1'] = 5.0
    except TypeError as e:
        assert str(e) == 'This Gauge is not a parent'


def test_histogram_math() -> None:
    histogram1 = Histogram('test_histogram1', 'Test Histogram 1')
    histogram2 = Histogram('test_histogram2', 'Test Histogram 2')

    histogram1 += 5.0
    histogram2 += 10

    assert histogram1.value == 5.0
    assert histogram2.value == 10.0

    histogram1 -= 5
    histogram2 -= 5

    assert histogram1.value == 0
    assert histogram2.value == 5

    result = histogram1 + histogram2
    assert result == 5

    result = histogram2 + 5
    assert result == 10

    result = histogram2 - 5
    assert result == 0


def test_histogram_setitem() -> None:
    histogram = Histogram('test_histogram', 'Test Histogram', ['label'])

    # Test setting value for a specific label set
    histogram['label1'] = 5.0
    assert histogram['label1'].value == 5.0

    histogram['label2'] = 10.0
    assert histogram['label2'].value == 10.0

    # Test incrementing value for a specific label set
    histogram['label1'] += 5.0
    assert histogram['label1'].value == 10.0

    # Test decrementing value for a specific label set
    histogram['label2'] -= 5.0
    assert histogram['label2'].value == 5.0

    # Test setting value with a Histogram instance (should raise TypeError)
    try:
        histogram['label1'] = histogram
    except TypeError as e:
        assert str(e) == 'Cannot reassign a Histogram with another Histogram'

    # Test setting value for a non-parent Histogram (should raise TypeError)
    non_parent_histogram = Histogram('non_parent_histogram', 'Non Parent Histogram')
    try:
        non_parent_histogram['label1'] = 5.0
    except TypeError as e:
        assert str(e) == 'This Histogram is not a parent'
