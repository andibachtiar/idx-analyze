"""Base types for application database migrations."""

from __future__ import annotations

from typing import Protocol


class Migration(Protocol):
    """Interface implemented by every migration module."""

    name: str

    def up(self, cursor) -> None:
        """Apply the migration."""
        ...

    def down(self, cursor) -> None:
        """Reverse the migration."""
        ...
