"""
Session user helper.

Builds the `user` dict stored in the session, centralised so that
login and account updates use the same shape.
"""


def build_session_user(profile) -> dict:
    """
    Build the session user dict from a Profile object.
    """
    if profile is None:
        return {}

    return {
        "user_id":   profile.user_id,
        "username":  profile.username,
        "full_name": profile.full_name,
        "initials":  profile.initials,
        "role_id":   profile.role_id,
        "role_name": profile.role_name or "",
        "email":     profile.email,
        "phone":     profile.phone,
    }
