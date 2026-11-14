"""
FX provider — USD ↔ RLS (and other currency vs RLS) exchange rates.

Unlike coin providers, the FX provider does NOT report prices for a
canonical coin traded against a quote currency. Instead, it reports
exchange rates between currencies:

    ProviderCoin(canonical="USD", quote="RLS", price=900000)
    means: 1 USD = 900,000 RLS.

The aggregator (crypto_market/aggregator.py) recognizes these rows as
FX rates and uses them to fill target quotes in `reference_prices`.
Because `USD`, `RLS`, `IRR`, etc. are listed in
`DEFAULT_CURRENCY_CANONICALS`, the aggregator does NOT turn FX rows
into CoinData — they only feed the conversion pipeline.

Pluggable sources
-----------------
The provider delegates the actual rate fetch to a "source" object.
Available sources:

    sources/mock.py     — reads rates from config; works out of the box
    sources/navasan.py  — stub for navasan.net; enable when API key
                          is configured

Source selection and per-source configuration live under the
`crypto_providers.fx.*` namespace in app_settings.json:

    "crypto_providers": {
      "fx": {
        "source":    "mock",       // "mock" | "navasan"
        "cache_ttl": 60.0,
        "sources": {
          "mock": {
            "usd_rls": "900000"
          },
          "navasan": {
            "api_key": "",
            "timeout": 7.0
          }
        }
      }
    }

If the selected source returns no rates (e.g., navasan with empty
api_key), the provider still registers — it just produces no
ProviderCoin rows. The aggregator handles missing FX gracefully
(no conversion, some target quotes remain unset).
"""
