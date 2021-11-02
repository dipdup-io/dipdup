from dipdup.interfaces.mixin import InterfaceMixin


class TestMixin:
    def test_mixin_has_init(self) -> None:
        mixin = InterfaceMixin
        assert callable(mixin.__init__)
