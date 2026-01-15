# Author: Daniel
# Description: Wrap 2D sketch curves onto arbitrary 3D surfaces

import adsk.core
import adsk.fusion
import traceback

wrap_command = None

try:
    from .commands import wrap_command
except Exception as e:
    # Import error will be shown when trying to run
    pass

# Global references
app = None
ui = None

ADDIN_NAME = 'SketchOnFace'


def run(context):
    """Entry point when add-in is started."""
    global app, ui
    try:
        app = adsk.core.Application.get()
        ui = app.userInterface

        if wrap_command:
            wrap_command.start(app, ui)
        else:
            ui.messageBox("SketchOnFace: Failed to load modules. Check the Text Commands window for errors.")

    except:
        if ui:
            ui.messageBox(f'Failed to start {ADDIN_NAME}:\n{traceback.format_exc()}')


def stop(context):
    """Called when add-in is stopped."""
    global app, ui
    try:
        if wrap_command:
            wrap_command.stop(ui)

        app = None
        ui = None

    except:
        if ui:
            ui.messageBox(f'Failed to stop {ADDIN_NAME}:\n{traceback.format_exc()}')
