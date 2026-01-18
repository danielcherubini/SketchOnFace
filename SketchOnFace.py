# Author: Daniel
# Description: Wrap 2D sketch curves onto arbitrary 3D surfaces

import traceback

import adsk.core
import adsk.fusion

wrap_command = None
edit_command = None
compute_handler_module = None

try:
    from .commands import edit_command, wrap_command
    from .commands.compute_handler import ComputeHandler
except Exception:
    # Import error will be shown when trying to run
    pass

# Global references
app = None
ui = None
handlers = []

# Custom Feature Definition
CUSTOM_FEATURE_ID = "adskSketchOnFace"
CUSTOM_FEATURE_NAME = "Sketch On Face"
_custom_feature_def = None

ADDIN_NAME = "SketchOnFace"


def run(context):
    """Entry point when add-in is started."""
    global app, ui, _custom_feature_def
    try:
        app = adsk.core.Application.get()
        ui = app.userInterface

        if not wrap_command:
            ui.messageBox(
                "SketchOnFace: Failed to load modules. Check the Text Commands window for errors."
            )
            return

        # Create CustomFeatureDefinition for parametric timeline support
        _custom_feature_def = adsk.fusion.CustomFeatureDefinition.create(
            CUSTOM_FEATURE_ID, CUSTOM_FEATURE_NAME, "resources"
        )

        # Register edit command first (must exist before we reference its ID)
        if edit_command:
            edit_command.start(app, ui, _custom_feature_def)
            # Link the edit command for double-click editing
            _custom_feature_def.editCommandId = edit_command.COMMAND_ID

        # Register compute handler for auto-recompute when dependencies change
        try:
            compute_handler = ComputeHandler()
            _custom_feature_def.customFeatureCompute.add(compute_handler)
            handlers.append(compute_handler)
        except Exception as e:
            print(f"SketchOnFace: Failed to register compute handler: {e}")

        # Start the main wrap command
        wrap_command.start(app, ui, _custom_feature_def)

    except:
        if ui:
            ui.messageBox(f"Failed to start {ADDIN_NAME}:\n{traceback.format_exc()}")


def stop(context):
    """Called when add-in is stopped."""
    global app, ui, handlers, _custom_feature_def
    try:
        if wrap_command:
            wrap_command.stop(ui)

        if edit_command:
            edit_command.stop(ui)

        handlers = []
        _custom_feature_def = None
        app = None
        ui = None

    except:
        if ui:
            ui.messageBox(f"Failed to stop {ADDIN_NAME}:\n{traceback.format_exc()}")
