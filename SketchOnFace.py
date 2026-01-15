# Author: Daniel
# Description: Wrap 2D sketch curves onto arbitrary 3D surfaces

import adsk.core
import adsk.fusion
import traceback

from .commands import wrap_command

# Global references
app = None
ui = None

ADDIN_NAME = 'SketchOnFace'
ADDIN_PANEL_ID = 'SolidScriptsAddinsPanel'


def run(context):
    """Entry point when add-in is started."""
    global app, ui
    try:
        app = adsk.core.Application.get()
        ui = app.userInterface

        # Initialize the wrap command
        wrap_command.start(app, ui)

    except:
        if ui:
            ui.messageBox(f'Failed to start {ADDIN_NAME}:\n{traceback.format_exc()}')


def stop(context):
    """Called when add-in is stopped."""
    global app, ui
    try:
        # Clean up the wrap command
        wrap_command.stop(ui)

        app = None
        ui = None

    except:
        if ui:
            ui.messageBox(f'Failed to stop {ADDIN_NAME}:\n{traceback.format_exc()}')
