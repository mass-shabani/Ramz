"""
FX sources — pluggable rate providers for the FX provider.

Each source implements `BaseFxSource` (see base.py) with a single
async method `get_rates()` returning a dict of currency → rate vs RLS.

Sources are stateless w.r.t. caching: the FX provider (../provider.py)
holds the cache. A source may still maintain its own internal cache
if the upstream API requires it, but that is an implementation detail.
"""
