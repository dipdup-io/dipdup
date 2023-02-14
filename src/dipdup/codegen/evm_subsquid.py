from dipdup.codegen import CodeGenerator


class SubsquidCodeGenerator(CodeGenerator):
    async def generate_abi(self) -> None:
        ...

    async def generate_schemas(self) -> None:
        ...

    async def generate_types(self, force: bool) -> None:
        ...

    async def generate_hooks(self) -> None:
        ...

    async def generate_handlers(self) -> None:
        ...
