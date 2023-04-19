import json
from contextlib import suppress
from os.path import dirname, join
from web3 import Web3
from web3.utils.address import to_checksum_address, ChecksumAddress
from web3.exceptions import ContractLogicError
from typing import Union, List, Optional

package_dir = dirname(dirname(__file__))

with open(join(package_dir, 'abi/erc20/ERC20.json')) as f:
    erc20_abi = json.load(f)

with open(join(package_dir, 'abi/erc20/ERC20NameBytes.json')) as f:
    erc20_symbol_bytes_abi = json.load(f)

with open(join(package_dir, 'abi/erc20/ERC20SymbolBytes.json')) as f:
    erc20_name_bytes_abi = json.load(f)


class ERC20Token:
    def __init__(self, address: ChecksumAddress, web3: Web3):
        self.web3 = web3
        self.address = address
        self.contract = self.web3.eth.contract(address=self.address, abi=erc20_abi)

    @classmethod
    def from_address(cls, token_address: Union[str, bytes], rpc_endpoint: str) -> 'ERC20Token':
        web3 = Web3(Web3.HTTPProvider(rpc_endpoint))
        address = to_checksum_address(token_address)
        return ERC20Token(address, web3)

    def get_symbol(self) -> str:
        with suppress(ContractLogicError):
            return self.contract.functions.symbol().call()

        with suppress(ContractLogicError):
            contract = self.web3.eth.contract(address=self.address, abi=erc20_symbol_bytes_abi)
            return contract.functions.symbol().call().decode('utf-8').rstrip('\x00')

        token = StaticTokenDefinition.from_address(self.address)
        if token:
            return token.symbol

        return 'unknown'

    def get_name(self) -> str:
        with suppress(ContractLogicError):
            return self.contract.functions.name().call()

        with suppress(ContractLogicError):
            contract = self.web3.eth.contract(address=self.address, abi=erc20_name_bytes_abi)
            return contract.functions.name().call().decode('utf-8').rstrip('\x00')

        token = StaticTokenDefinition.from_address(self.address)
        if token:
            return token.name

        return 'unknown'

    def get_decimals(self) -> int:
        with suppress(ContractLogicError):
            return self.contract.functions.decimals().call()

        token = StaticTokenDefinition.from_address(self.address)
        if token:
            return token.decimals

        raise ValueError(f'Cannot get decimals for token {self.address}')

    def get_total_supply(self) -> int:
        with suppress(Exception):
            self.contract.functions.totalSupply().call()

        return 0


class StaticTokenDefinition:
    def __init__(self, address: str, symbol: str, name: str, decimals: int):
        self.address = address
        self.symbol = symbol
        self.name = name
        self.decimals = decimals

    @staticmethod
    def get_static_definitions() -> List['StaticTokenDefinition']:
        static_definitions = [
            StaticTokenDefinition('0xe0b7927c4af23765cb51314a0e0521a9645f0e2a', 'DGD', 'DGD', 9),
            StaticTokenDefinition('0x7fc66500c84a76ad7e9c93437bfc5ac33e2ddae9', 'AAVE', 'Aave Token', 18),
            StaticTokenDefinition('0xeb9951021698b42e4399f9cbb6267aa35f82d59d', 'LIF', 'Lif', 18),
            StaticTokenDefinition('0xbdeb4b83251fb146687fa19d1c660f99411eefe3', 'SVD', 'savedroid', 18),
            StaticTokenDefinition('0xbb9bc244d798123fde783fcc1c72d3bb8c189413', 'TheDAO', 'TheDAO', 16),
            StaticTokenDefinition('0x38c6a68304cdefb9bec48bbfaaba5c5b47818bb2', 'HPB', 'HPBCoin', 18)
        ]
        return static_definitions

    @staticmethod
    def from_address(token_address: ChecksumAddress) -> Optional['StaticTokenDefinition']:
        static_definitions = StaticTokenDefinition.get_static_definitions()
        for static_definition in static_definitions:
            if to_checksum_address(static_definition.address) == token_address:
                return static_definition
        return None
