from dataclasses import dataclass


class Os:
    def __str__(self) -> str:
        return self.__class__.__name__.lower()


@dataclass(frozen=True)
class Manylinux(Os):
    major: int
    minor: int

    def __str__(self) -> str:
        return f"manylinux_{self.major}_{self.minor}"


@dataclass(frozen=True)
class Musllinux(Os):
    major: int
    minor: int

    def __str__(self) -> str:
        return f"musllinux_{self.major}_{self.minor}"


@dataclass(frozen=True)
class Windows(Os):
    pass


@dataclass(frozen=True)
class Macos(Os):
    major: int
    minor: int

    def __str__(self) -> str:
        return f"macos_{self.major}_{self.minor}"


@dataclass(frozen=True)
class FreeBsd(Os):
    release: str

    def __str__(self) -> str:
        return f"freebsd_{self.release}"


@dataclass(frozen=True)
class NetBsd(Os):
    release: str

    def __str__(self) -> str:
        return f"netbsd_{self.release}"


@dataclass(frozen=True)
class OpenBsd(Os):
    release: str


@dataclass(frozen=True)
class Dragonfly(Os):
    release: str

    def __str__(self) -> str:
        return f"dragonfly_{self.release}"


@dataclass(frozen=True)
class Illumos(Os):
    release: str
    arch: str

    def __str__(self) -> str:
        return f"illumos_{self.release}_{self.arch}"


@dataclass(frozen=True)
class Haiku(Os):
    release: str

    def __str__(self) -> str:
        return f"haiku_{self.release}"


@dataclass(frozen=True)
class Generic(Os):
    name: str

    def __str__(self) -> str:
        return self.name.lower()
