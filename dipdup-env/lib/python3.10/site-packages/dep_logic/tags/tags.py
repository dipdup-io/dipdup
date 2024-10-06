from __future__ import annotations

import sys
from dataclasses import dataclass
from enum import IntEnum, auto
from platform import python_implementation
from typing import TYPE_CHECKING

from dep_logic.specifiers.range import RangeSpecifier

from ..specifiers import InvalidSpecifier, VersionSpecifier, parse_version_specifier
from .platform import Platform

if TYPE_CHECKING:
    from typing import Literal, Self


def parse_wheel_tags(filename: str) -> tuple[list[str], list[str], list[str]]:
    if not filename.endswith(".whl"):
        raise InvalidWheelFilename(
            f"Invalid wheel filename (extension must be '.whl'): {filename}"
        )

    filename = filename[:-4]
    dashes = filename.count("-")
    if dashes not in (4, 5):
        raise InvalidWheelFilename(
            f"Invalid wheel filename (wrong number of parts): {filename}"
        )

    parts = filename.split("-")
    python, abi, platform = parts[-3:]
    return python.split("."), abi.split("."), platform.split(".")


def _ensure_version_specifier(spec: str) -> VersionSpecifier:
    parsed = parse_version_specifier(spec)
    if not isinstance(parsed, VersionSpecifier):
        raise InvalidSpecifier(f"Invalid version specifier {spec}")
    return parsed


class TagsError(Exception):
    pass


class InvalidWheelFilename(TagsError, ValueError):
    pass


class UnsupportedImplementation(TagsError, ValueError):
    pass


@dataclass(frozen=True)
class Implementation:
    name: Literal["cpython", "pypy", "pyston"]
    gil_disabled: bool = False

    @property
    def short(self) -> str:
        if self.name == "cpython":
            return "cp"
        elif self.name == "pypy":
            return "pp"
        else:
            return "pt"

    @property
    def capitalized(self) -> str:
        if self.name == "pypy":
            return "PyPy"
        elif self.name == "pyston":
            return "Pyston"
        else:
            return "CPython"

    @classmethod
    def current(cls) -> Self:
        import sysconfig

        implementation = python_implementation()

        return cls.parse(
            implementation.lower(), sysconfig.get_config_var("Py_GIL_DISABLED") or False
        )

    @classmethod
    def parse(cls, name: str, gil_disabled: bool = False) -> Self:
        if gil_disabled and name != "cpython":
            raise UnsupportedImplementation("Only CPython supports GIL disabled mode")
        if name in ("cpython", "pypy", "pyston"):
            return cls(name, gil_disabled)
        else:
            raise UnsupportedImplementation(
                f"Unsupported implementation: {name}, expected cpython, pypy, or pyston"
            )


class EnvCompatibility(IntEnum):
    INCOMPATIBLE = auto()
    LOWER_OR_EQUAL = auto()
    HIGHER = auto()


@dataclass(frozen=True)
class EnvSpec:
    requires_python: VersionSpecifier
    platform: Platform | None = None
    implementation: Implementation | None = None

    def __str__(self) -> str:
        parts = [str(self.requires_python)]
        if self.platform is not None:
            parts.append(str(self.platform))
        if self.implementation is not None:
            parts.append(self.implementation.name)
        return f"({', '.join(parts)})"

    def as_dict(self) -> dict[str, str | bool]:
        result: dict[str, str | bool] = {"requires_python": str(self.requires_python)}
        if self.platform is not None:
            result["platform"] = str(self.platform)
        if self.implementation is not None:
            result["implementation"] = self.implementation.name
            result["gil_disabled"] = self.implementation.gil_disabled
        return result

    @classmethod
    def from_spec(
        cls,
        requires_python: str,
        platform: str | None = None,
        implementation: str | None = None,
        gil_disabled: bool = False,
    ) -> Self:
        return cls(
            _ensure_version_specifier(requires_python),
            Platform.parse(platform) if platform else None,
            Implementation.parse(implementation, gil_disabled=gil_disabled)
            if implementation
            else None,
        )

    @classmethod
    def current(cls) -> Self:
        # XXX: Strip pre-release and post-release tags
        python_version = f"{sys.version_info.major}.{sys.version_info.minor}.{sys.version_info.micro}"
        requires_python = _ensure_version_specifier(f"=={python_version}")
        platform = Platform.current()
        implementation = Implementation.current()
        return cls(requires_python, platform, implementation)

    def _evaluate_python(
        self, python_tag: str, abi_tag: str
    ) -> tuple[int, int, int] | None:
        """Return a tuple of (major, minor, abi) if the wheel is compatible with the environment, or None otherwise."""
        impl, major, minor = python_tag[:2], python_tag[2], python_tag[3:]
        if self.implementation is not None and impl not in [
            self.implementation.short,
            "py",
        ]:
            return None
        abi_impl = (
            abi_tag.split("_", 1)[0]
            .replace("pypy", "pp")
            .replace("pyston", "pt")
            .lower()
        )
        allow_abi3 = impl == "cp" and (
            self.implementation is None or not self.implementation.gil_disabled
        )
        free_threaded: bool | None = None
        if self.implementation is not None:
            free_threaded = self.implementation.gil_disabled
        try:
            if abi_impl == "abi3":
                if not allow_abi3:
                    return None
                if (
                    parse_version_specifier(f">={major}.{minor or 0}")
                    & self.requires_python
                ).is_empty():
                    return None
                return (int(major), int(minor or 0), 1)  # 1 for abi3
            # cp36-cp36m-*
            # cp312-cp312m-*
            # pp310-pypy310_pp75-*
            if abi_impl != "none":
                if not abi_impl.startswith(python_tag.lower()):
                    return None
                if (
                    free_threaded is not None
                    and abi_impl.endswith("t") is not free_threaded
                ):
                    return None
            if major and minor:
                wheel_range = parse_version_specifier(f"=={major}.{minor}.*")
            else:
                wheel_range = parse_version_specifier(f"=={major}.*")
        except InvalidSpecifier:
            return None
        if (wheel_range & self.requires_python).is_empty():
            return None
        return (int(major), int(minor or 0), 0 if abi_impl == "none" else 2)

    def _evaluate_platform(self, platform_tag: str) -> int | None:
        if self.platform is None:
            return -1
        platform_tags = [*self.platform.compatible_tags, "any"]
        if platform_tag not in platform_tags:
            return None
        return len(platform_tags) - platform_tags.index(platform_tag)

    def compatibility(
        self,
        wheel_python_tags: list[str],
        wheel_abi_tags: list[str],
        wheel_platform_tags: list[str],
    ) -> tuple[int, int, int, int] | None:
        python_abi_combinations = (
            (python_tag, abi_tag)
            for python_tag in wheel_python_tags
            for abi_tag in wheel_abi_tags
        )
        python_compat = max(
            filter(
                None, (self._evaluate_python(*comb) for comb in python_abi_combinations)
            ),
            default=None,
        )
        if python_compat is None:
            return None
        platform_compat = max(
            filter(None, map(self._evaluate_platform, wheel_platform_tags)),
            default=None,
        )
        if platform_compat is None:
            return None
        return (*python_compat, platform_compat)

    def wheel_compatibility(
        self, wheel_filename: str
    ) -> tuple[int, int, int, int] | None:
        wheel_python_tags, wheel_abi_tags, wheel_platform_tags = parse_wheel_tags(
            wheel_filename
        )
        return self.compatibility(
            wheel_python_tags, wheel_abi_tags, wheel_platform_tags
        )

    def markers(self) -> dict[str, str]:
        result = {}
        if (
            isinstance(self.requires_python, RangeSpecifier)
            and (version := self.requires_python.min) is not None
            and version == self.requires_python.max
        ):
            result.update(
                python_version=f"{version.major}.{version.minor}",
                python_full_version=str(version),
            )
        if self.platform is not None:
            result.update(self.platform.markers())
        if self.implementation is not None:
            result.update(
                implementation_name=self.implementation.name,
                platform_python_implementation=self.implementation.capitalized,
            )

        return result

    def compare(self, target: EnvSpec) -> EnvCompatibility:
        if self == target:
            return EnvCompatibility.LOWER_OR_EQUAL
        if (self.requires_python & target.requires_python).is_empty():
            return EnvCompatibility.INCOMPATIBLE
        if (
            self.implementation is not None
            and target.implementation is not None
            and self.implementation != target.implementation
        ):
            return EnvCompatibility.INCOMPATIBLE
        if self.platform is None or target.platform is None:
            return EnvCompatibility.LOWER_OR_EQUAL
        if self.platform.arch != target.platform.arch:
            return EnvCompatibility.INCOMPATIBLE
        if type(self.platform.os) is not type(target.platform.os):
            return EnvCompatibility.INCOMPATIBLE

        if hasattr(self.platform.os, "major") and hasattr(self.platform.os, "minor"):
            if (self.platform.os.major, self.platform.os.minor) <= (  # type: ignore[attr-defined]
                target.platform.os.major,  # type: ignore[attr-defined]
                target.platform.os.minor,  # type: ignore[attr-defined]
            ):
                return EnvCompatibility.LOWER_OR_EQUAL
            else:
                return EnvCompatibility.HIGHER
        return EnvCompatibility.LOWER_OR_EQUAL
