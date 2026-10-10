"""
Access control.

Role-based checks that combine the `role`, `form`, `condition_of`, and
`form_access` tables. Backed by an in-memory cache to avoid hitting the
database on every request.

To be implemented in phase 5.
"""


class AccessChecker:
    """
    Role-based access checker with cache.

    Constructor receives the DbManagerService (for repository access)
    and an optional logger.
    """

    def __init__(self, db_service, logger=None):
        self._db = db_service
        self._logger = logger
        # Caches will be added in phase 5:
        #   self._user_cache: dict[int, tuple[float, bool]]
        #   self._access_cache: dict[tuple[int, str], tuple[float, bool]]

    # Placeholder — implementation in phase 5
