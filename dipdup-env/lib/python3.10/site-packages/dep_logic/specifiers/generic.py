from __future__ import annotations

import operator
import typing as t
from dataclasses import dataclass

from dep_logic.specifiers.base import BaseSpecifier, InvalidSpecifier
from dep_logic.specifiers.special import AnySpecifier, EmptySpecifier
from dep_logic.utils import DATACLASS_ARGS

Operator = t.Callable[[str, str], bool]


@dataclass(frozen=True, unsafe_hash=True, **DATACLASS_ARGS)
class GenericSpecifier(BaseSpecifier):
    op: str
    value: str
    op_order: t.ClassVar[dict[str, int]] = {"==": 0, "!=": 1, "in": 2, "not in": 3}
    _op_map: t.ClassVar[dict[str, Operator]] = {
        "==": operator.eq,
        "!=": operator.ne,
        "in": lambda lhs, rhs: lhs in rhs,
        "not in": lambda lhs, rhs: lhs not in rhs,
        ">": operator.gt,
        ">=": operator.ge,
        "<": operator.lt,
        "<=": operator.le,
    }

    def __post_init__(self) -> None:
        if self.op not in self._op_map:
            raise InvalidSpecifier(f"Invalid operator: {self.op!r}")

    def __str__(self) -> str:
        return f'{self.op} "{self.value}"'

    def __invert__(self) -> BaseSpecifier:
        invert_map = {
            "==": "!=",
            "!=": "==",
            "not in": "in",
            "in": "not in",
            "<": ">=",
            "<=": ">",
            ">": "<=",
            ">=": "<",
        }
        op = invert_map[self.op]
        return GenericSpecifier(op, self.value)

    def __and__(self, other: t.Any) -> BaseSpecifier:
        if not isinstance(other, GenericSpecifier):
            return NotImplemented
        if self == other:
            return self
        this, that = sorted(
            (self, other), key=lambda x: self.op_order.get(x.op, len(self.op_order))
        )
        if this.op == that.op == "==":
            # left must be different from right
            return EmptySpecifier()
        elif (this.op, that.op) == ("==", "!="):
            if this.value == that.value:
                return EmptySpecifier()
            return this
        elif (this.op, that.op) == ("in", "not in") and this.value == that.value:
            return EmptySpecifier()
        elif (this.op, that.op) == ("==", "in"):
            if this.value in that.value:
                return this
            return EmptySpecifier()
        elif (this.op, that.op) == ("!=", "not in") and this.value in that.value:
            return that
        else:
            raise NotImplementedError

    def __or__(self, other: t.Any) -> BaseSpecifier:
        if not isinstance(other, GenericSpecifier):
            return NotImplemented
        if self == other:
            return self
        this, that = sorted(
            (self, other), key=lambda x: self.op_order.get(x.op, len(self.op_order))
        )
        if this.op == "==" and that.op == "!=":
            if this.value == that.value:
                return AnySpecifier()
            return that
        elif this.op == "!=" and that.op == "!=":
            return AnySpecifier()
        elif this.op == "in" and that.op == "not in" and this.value == that.value:
            return AnySpecifier()
        elif this.op == "!=" and that.op == "in" and this.value in that.value:
            return AnySpecifier()
        elif this.op == "!=" and that.op == "not in":
            if this.value in that.value:
                return this
            return AnySpecifier()
        elif this.op == "==" and that.op == "in" and this.value in that.value:
            return that
        else:
            raise NotImplementedError

    def __contains__(self, value: str) -> bool:
        return self._op_map[self.op](value, self.value)
