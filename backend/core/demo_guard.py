"""Demo Guard — blocks real external actions for demo users."""

DEMO_USER_ID = "demo_user"


def is_demo_user(user: dict) -> bool:
    """Check if the current user is the demo user."""
    return user.get("user_id") == DEMO_USER_ID or user.get("is_demo") is True


class DemoGuardError(Exception):
    """Raised when a demo user tries a blocked action."""
    def __init__(self, action: str = "questa azione"):
        self.message = f"Azione non disponibile in modalita demo: {action}"
        super().__init__(self.message)
