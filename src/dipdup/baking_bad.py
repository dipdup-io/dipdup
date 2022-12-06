"""This module contains constants related to Baking Bad hosted services.

If you selfhost the whole DipDup stack (TzKT, Sentry, etc.) you don't need theese.
"""
SENTRY_DSN = 'https://ef33481a853b44e39187bdf2d9eef773@newsentry.baking-bad.org/6'
METADATA_API_URL = 'https://metadata.dipdup.net'
MAX_TZKT_BATCH_SIZE = 10000
TZKT_API_URLS: dict[str, str] = {
    'https://api.tzkt.io': 'mainnet',
    'https://api.ghostnet.tzkt.io': 'ghostnet',
    'https://api.jakartanet.tzkt.io': 'jakartanet',
    'https://staging.api.tzkt.io': 'staging',
}
