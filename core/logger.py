# Logger - Write debug messages to Fusion 360 Text Commands window

import adsk.core


class TextCommandsLogger:
    """Logger that writes to Fusion 360's Text Commands window."""

    def __init__(self):
        app = adsk.core.Application.get()
        ui = app.userInterface
        palettes = ui.palettes
        self.textPalette = palettes.itemById("TextCommands")
        if self.textPalette:
            self.textPalette.isVisible = True

    def log(self, text):
        """Write text to the Text Commands window."""
        if self.textPalette:
            self.textPalette.writeText(str(text) + "\n")
            adsk.doEvents()  # Force UI update


# Global logger instance
_logger = None


def get_logger():
    """Get or create the global logger instance."""
    global _logger
    if _logger is None:
        _logger = TextCommandsLogger()
    return _logger


def log(text):
    """Convenience function to log text."""
    get_logger().log(text)
