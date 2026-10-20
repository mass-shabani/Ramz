"""
Admin Panel Service

Minimal service for the admin_panel module. In later phases this
will grow to encapsulate the business logic of user management,
forms CRUD, and access grant editing.
"""


class AdminPanelService:
    """
    Facade for admin panel operations.
    """

    def __init__(self, db_service, template_service, logger=None):
        self.db = db_service
        self.template_service = template_service
        self.logger = logger

    def _log(self, message, level="INFO"):
        if self.logger:
            try:
                self.logger.log(message, level=level, tag="admin")
            except Exception:
                pass
