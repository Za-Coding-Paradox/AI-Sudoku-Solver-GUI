"""GUI layer — all pygame-ce rendering.  Never imports solver or data directly."""

from sudoku.gui.theme import Theme, ThemeManager
from sudoku.gui.board_widget import BoardWidget
from sudoku.gui.control_panel import ControlPanel
from sudoku.gui.status_bar import StatusBar

__all__ = [
    "Theme",
    "ThemeManager",
    "BoardWidget",
    "ControlPanel",
    "StatusBar",
]
