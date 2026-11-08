"""
providers — concrete implementations of BaseCryptoProvider.

Each provider lives in its own subfolder:

    providers/nobitex/      (TASK 78.4-78.5)
    providers/coingecko/    (TASK 78.6)
    providers/fx/           (TASK 78.7)

A provider subfolder typically contains:
    client.py        — HTTP client wrapper for the provider's API
    rate_limiter.py  — per-provider rate limiting
    symbols.py       — (optional) static symbol maps or helpers
    provider.py      — the BaseCryptoProvider implementation

Providers are registered in module.py under the service key
`crypto_provider_<name>` (e.g. `crypto_provider_nobitex`), where
`<name>` matches the provider instance's `.name` property.
"""
