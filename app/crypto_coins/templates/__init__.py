"""
templates — Jinja2 templates for crypto_coins.

Directory structure (as it grows in TASK 79.3-79.4):
    templates/
    └── partials/
        ├── coins_list.html      (TASK 79.3)
        └── coins_settings.html  (TASK 79.4)

The `templates/` directory is registered with template_service in
module.py (TASK 79.3), so `template_service.render("partials/coins_list.html", ...)`
finds files here.
"""
