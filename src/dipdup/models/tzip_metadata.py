from enum import Enum


class TzipMetadataNetwork(Enum):
    """Tezos network enum for TZIP-16 metadata.

    :param mainnet: mainnet
    :param ghostnet: ghostnet
    :param mumbainet: mumbainet
    :param nairobinet: nairobinet
    :param oxfordnet: oxfordnet
    """

    mainnet = 'mainnet'
    ghostnet = 'ghostnet'
    mumbainet = 'mumbainet'
    nairobinet = 'nairobinet'
    oxfordnet = 'oxfordnet'
