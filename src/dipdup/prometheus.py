from typing import Any
from typing import NoReturn
from typing import Union

from prometheus_client import Counter as PrometheusCounter
from prometheus_client import Gauge as PrometheusGauge
from prometheus_client import Histogram as PrometheusHistogram
from prometheus_client.metrics import MetricWrapperBase


def raise_unsupported_operation(operation: str, a: MetricWrapperBase, b: float | MetricWrapperBase) -> NoReturn:
    a_type = 'Counter' if not a._labelnames else 'Counter with labels'

    b_type = type(b)
    if isinstance(b, Counter):
        b_type = 'Counter' if not b._labelnames else 'Counter with labels'

    raise TypeError(f"Unsupported operation '{operation}' between a {a_type} and a {b_type}")


class Counter(PrometheusCounter):
    """A Counter metric with added functionality for in-place addition and labeled metric value retrieval."""

    def __init__(self, *args: Any, **kwargs: Any) -> None:
        super().__init__(*args, **kwargs)

    def __add__(self, other: float) -> float:
        if isinstance(self.value, float):
            return self.value + other

        raise_unsupported_operation('+', self, other)

    def __sub__(self, other: Union[float, 'Counter']) -> float:
        # First, check if the Counter is not labeled (i.e. it's value is a float)
        if isinstance(self.value, float):
            if isinstance(other, Counter):
                if isinstance(other.value, float):
                    return self.value - other.value
            if isinstance(other, float | int):
                return self.value - other

        raise_unsupported_operation('-', self, other)

    def __iadd__(self, other: int | float) -> 'Counter':
        """Increment the counter by a given value."""
        self.inc(other)
        return self

    # def to_dict(self) -> dict[str, Any]:
    #     """Return a JSON-serializable representation of the Counter."""
    #     return {
    #         'name': self._name,
    #         'description': self._documentation,
    #         'labels': self._labelnames,
    #         'value': self.value,  # Use the existing `value` property
    #     }

    @property
    def value(self) -> float | dict[tuple[str, ...], float]:
        """Return the current value of the counter.
        If the counter has labels, return a dictionary of labels to counter values."""
        if self._is_parent():
            values: dict[tuple[str, ...], float] = {}
            for sample in self.collect():
                for s in sample.samples:
                    if s.name.endswith('_total'):
                        label_values = tuple(s.labels[label] for label in self._labelnames)
                        values[label_values] = s.value
            return values
        return float(self._value.get())

    def __getitem__(self, label_values: str | tuple[str, ...]) -> 'Counter':
        """Get a labeled metric instance."""
        if not self._is_parent():
            raise TypeError("This Counter doesn't have labels")
        if isinstance(label_values, str):
            label_values = (label_values,)
        elif not isinstance(label_values, tuple):
            raise TypeError('Label values must be a string or tuple of strings')

        return self.labels(*label_values)

    def __setitem__(self, label_values: str | tuple[str, ...], value: Union[float, 'Counter']) -> None:
        # The += (__idadd__) operator calls __setitem__ with the metric as the value
        # We already handle the increment operation in __iadd__, so we can safely ignore this call
        # Same goes for the -= (__isub__) operator
        if isinstance(value, Counter):
            if value in self._metrics.values():
                return

        raise TypeError('Counters an only be incremented, use the += operator or the `inc` method instead')

    def __int__(self) -> int:
        if isinstance(self.value, float):
            return int(self.value)

        raise TypeError('Cannot convert a labeled Counter to an integer')


class Gauge(PrometheusGauge):
    """A Gauge metric with added functionality for in-place addition/subtraction and labeled metric value retrieval."""

    def __init__(self, *args: Any, **kwargs: Any) -> None:
        super().__init__(*args, **kwargs)

    def __add__(self, other: int | float) -> float:
        if isinstance(self.value, float):
            return self.value + other

        raise_unsupported_operation('+', self, other)

    def __iadd__(self, other: int | float) -> 'Gauge':
        """Increment the gauge by a given value."""
        self.inc(other)
        return self

    def __isub__(self, other: float) -> 'Gauge':
        """Decrement the gauge by a given value."""
        self.dec(other)
        return self

    def set(self, value: float) -> None:
        """Set the gauge to a specific value."""
        super().set(value)

    @property
    def value(self) -> float | dict[tuple[str, ...], float]:
        """Return the current value of the gauge.
        If the counter has labels, return a dictionary of labels to counter values."""
        if self._is_parent():
            values: dict[tuple[str, ...], float] = {}
            for sample in self.collect():
                for s in sample.samples:
                    if s.name == self._name:
                        label_values = tuple(s.labels[label] for label in self._labelnames)
                        values[label_values] = s.value
            return values
        return float(self._value.get())

    def __getitem__(self, label_values: str | tuple[str, ...]) -> 'Gauge':
        """Get a labeled metric instance."""
        if not self._is_parent():
            raise TypeError("This Gauge doesn't have labels")
        if isinstance(label_values, str):
            label_values = (label_values,)
        elif not isinstance(label_values, tuple):
            raise TypeError('Label values must be a string or tuple of strings')
        return self.labels(*label_values)

    def __setitem__(self, label_values: str | tuple[str, ...], value: Union[float, 'Gauge']) -> None:
        """Set the gauge for a given label combination to a specified value."""
        # The += (__idadd__) operator calls __setitem__ with the metric as the value
        # We already handle the increment operation in __iadd__, so we can safely ignore this call
        # Same goes for the -= (__isub__) operator
        if isinstance(value, Gauge):
            if value in self._metrics.values():
                return
            raise_unsupported_operation('__setitem__', self, value)

        if not self._is_parent():
            raise TypeError("This Gauge doesn't have labels")

        self[label_values].set(value)


class Histogram(PrometheusHistogram):
    """A Histogram metric with added functionality for in-place addition and labeled metric value retrieval."""

    def __init__(self, *args: Any, **kwargs: Any) -> None:
        super().__init__(*args, **kwargs)

    def __iadd__(self, other: float) -> 'Histogram':
        """Observe a value in the histogram."""
        self.observe(other)
        return self

    def __isub__(self, other: float) -> 'Histogram':
        """Decrement operation is not allowed for Histogram."""
        raise TypeError('Cannot decrement a Histogram')

    @property
    def value(self) -> float | dict[tuple[str, ...], float]:
        """Return the sum of observations in the histogram."""
        if self._is_parent():
            values: dict[tuple[str, ...], float] = {}
            for sample in self.collect():
                for s in sample.samples:
                    if s.name.endswith('_sum'):
                        label_values = tuple(s.labels[label] for label in self._labelnames)
                        values[label_values] = s.value
            return values

        for sample in self.collect():
            for s in sample.samples:
                if s.name.endswith('_sum'):
                    return s.value
        else:
            # TODO: Is this the correct behavior?
            raise ValueError('Histogram has no sum value')

    def __getitem__(self, label_values: str | tuple[str, ...]) -> 'Histogram':
        """Get a labeled metric instance."""
        if not self._is_parent():
            raise TypeError("This Histogram doesn't have labels")
        if isinstance(label_values, str):
            label_values = (label_values,)
        elif not isinstance(label_values, tuple):
            raise TypeError('Label values must be a string or tuple of strings')
        return self.labels(*label_values)

    def __setitem__(self, label_values: str | tuple[str, ...], value: float) -> None:
        """Observe a value in the histogram for a given label combination."""
        # The += (__idadd__) operator calls __setitem__ with the metric as the value
        # We already handle the increment operation in __iadd__, so we can safely ignore this call
        # Same goes for the -= (__isub__) operator
        if isinstance(value, Histogram):
            if value in self._metrics.values():
                return

        if not self._is_parent():
            raise TypeError("This Histogram doesn't have labels")

        self[label_values].observe(value)
