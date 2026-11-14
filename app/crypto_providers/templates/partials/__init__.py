"""
partials — Jinja2 partials for crypto_providers settings UI.

Each partial is rendered standalone (not extending base.html) and
injected into account_setting's content-container by
`content-container.js` when a Connected Services nav item is
clicked.

Files (added in TASK 78.9):
    overview.html   — list of configurable providers + status
    nobitex.html    — Nobitex API key/secret form
"""
