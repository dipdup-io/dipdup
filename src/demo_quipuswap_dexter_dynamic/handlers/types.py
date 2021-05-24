from typing import Union
import demo_quipuswap_dexter.types.fa12_token.parameter.transfer as parameter
import demo_quipuswap_dexter.types.fa12_token_tzbtc.parameter.transfer as tzbtc_parameter
import demo_quipuswap_dexter.types.fa12_token_ethtz.parameter.transfer as ethtz_parameter
import demo_quipuswap_dexter.types.fa12_token.storage as storage
import demo_quipuswap_dexter.types.fa12_token_tzbtc.storage as tzbtc_storage
import demo_quipuswap_dexter.types.fa12_token_ethtz.storage as ethtz_storage
import demo_quipuswap_dexter.types.quipu_fa12.storage as quipu_storage
import demo_quipuswap_dexter.types.quipu_fa12_ethtz.storage as ethtz_quipu_storage

TransferParameterT = Union[
    parameter.TransferParameter,
    tzbtc_parameter.TransferParameter,
    ethtz_parameter.TransferParameter,
]

Fa12TokenStorageT = Union[
    storage.Fa12TokenStorage,
    tzbtc_storage.Fa12TokenTzbtcStorage,
    ethtz_storage.Fa12TokenEthtzStorage
]

QuipuFa12StorageT = Union[
    quipu_storage.QuipuFa12Storage,
    ethtz_quipu_storage.QuipuFa12EthtzStorage,
]
