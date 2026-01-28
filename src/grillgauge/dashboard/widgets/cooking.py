"""Cooking temperature safety guide widget."""

from typing import Any

from textual.widgets import DataTable


class CookingWidget(DataTable):
    """Widget displaying safe cooking temperatures for beef, pork, and chicken.

    Shows a table with columns:
    - MEAT: Meat type
    - DONENESS: Level of doneness
    - TEMP: Safe internal temperature
    """

    def __init__(self, *args: Any, **kwargs: Any) -> None:
        """Initialize the cooking widget."""
        super().__init__(*args, **kwargs)
        self.show_header = False
        self.zebra_stripes = True
        self.cursor_type = "none"  # Disable cursor

    def on_mount(self) -> None:
        """Set up the widget when mounted."""
        # Add columns first
        self.add_columns("", "", "")
        self.show_header = False
        # Add rows with centered content
        self.add_row("🥩 Beef", "Rare", "52-55°C")
        self.add_row("🥩 Beef", "Medium", "57-63°C")
        self.add_row("🥩 Beef", "Well-done", "68-74°C")
        self.add_row("🥓 Pork", "Safe internal", "63°C")
        self.add_row("🍗 Chicken", "Safe internal", "74°C")
