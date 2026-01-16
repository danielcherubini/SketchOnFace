# Edit Command - Handles editing existing SketchOnFace custom features

import traceback

import adsk.core
import adsk.fusion

# Command identity
COMMAND_ID = "SketchOnFaceEditCommand"
COMMAND_NAME = "Edit Sketch On Face"

# Input IDs (parameters only - face/curves/edge cannot be changed after creation)
INPUT_SCALE_X = COMMAND_ID + "_scaleX"
INPUT_SCALE_Y = COMMAND_ID + "_scaleY"
INPUT_OFFSET_X = COMMAND_ID + "_offsetX"
INPUT_OFFSET_Y = COMMAND_ID + "_offsetY"
INPUT_OFFSET_NORMAL = COMMAND_ID + "_offsetNormal"

# Global event handlers
handlers = []

# Global references
_app = None
_ui = None
_edited_feature = None


class EditCommandCreatedHandler(adsk.core.CommandCreatedEventHandler):
    """Handles edit command creation - builds UI with current values."""

    def __init__(self):
        super().__init__()

    def notify(self, args: adsk.core.CommandCreatedEventArgs):
        global _edited_feature
        try:
            cmd = args.command
            inputs = cmd.commandInputs

            # Add event handlers
            on_activate = EditActivateHandler()
            cmd.activate.add(on_activate)
            handlers.append(on_activate)

            on_execute = EditExecuteHandler()
            cmd.execute.add(on_execute)
            handlers.append(on_execute)

            on_preview = EditPreviewHandler()
            cmd.executePreview.add(on_preview)
            handlers.append(on_preview)

            on_validate = EditValidateInputsHandler()
            cmd.validateInputs.add(on_validate)
            handlers.append(on_validate)

            # Get the custom feature being edited from selection
            design = adsk.fusion.Design.cast(_app.activeProduct)
            if not design:
                return

            # The feature to edit should be in the active selection
            sel = _ui.activeSelections
            if sel.count > 0:
                entity = sel.item(0).entity
                if entity.objectType == "adsk::fusion::CustomFeature":
                    _edited_feature = entity

            if not _edited_feature:
                _ui.messageBox("No SketchOnFace feature selected for editing.")
                return

            # Get current parameter values
            params = _edited_feature.parameters
            current_scale_x = (
                params.itemById("scaleX").value if params.itemById("scaleX") else 1.0
            )
            current_scale_y = (
                params.itemById("scaleY").value if params.itemById("scaleY") else 1.0
            )
            current_offset_x = (
                params.itemById("offsetX").value if params.itemById("offsetX") else 0.0
            )
            current_offset_y = (
                params.itemById("offsetY").value if params.itemById("offsetY") else 0.0
            )
            current_offset_normal = (
                params.itemById("offsetNormal").value
                if params.itemById("offsetNormal")
                else (params.itemById("offset").value if params.itemById("offset") else 0.0)
            )

            # === UI INPUTS ===
            # Note: Face/curves/edge cannot be changed after creation - only parameters

            # X Scale
            inputs.addFloatSpinnerCommandInput(
                INPUT_SCALE_X, "X Scale", "", 0.01, 100.0, 0.1, current_scale_x
            )

            # Y Scale
            inputs.addFloatSpinnerCommandInput(
                INPUT_SCALE_Y, "Y Scale", "", 0.01, 100.0, 0.1, current_scale_y
            )

            # X Offset
            inputs.addFloatSpinnerCommandInput(
                INPUT_OFFSET_X, "X Offset", "", -1.0, 1.0, 0.05, current_offset_x
            )

            # Y Offset
            inputs.addFloatSpinnerCommandInput(
                INPUT_OFFSET_Y, "Y Offset", "", -1.0, 1.0, 0.05, current_offset_y
            )

            # Surface normal offset
            inputs.addFloatSpinnerCommandInput(
                INPUT_OFFSET_NORMAL, "Surface Offset", "cm", -10.0, 10.0, 0.01,
                current_offset_normal
            )

        except:
            if _ui:
                _ui.messageBox(
                    f"Edit command created failed:\n{traceback.format_exc()}"
                )


class EditActivateHandler(adsk.core.CommandEventHandler):
    """Handles command activation - rolls timeline back and deletes current sketch."""

    def __init__(self):
        super().__init__()

    def notify(self, args):
        try:
            if _edited_feature:
                # Roll timeline TO this feature (not before) so we can edit it
                timeline_obj = _edited_feature.timelineObject
                if timeline_obj:
                    timeline_obj.rollTo(False)  # False = roll to the feature itself

        except:
            print(f"Edit activate failed: {traceback.format_exc()}")


class EditPreviewHandler(adsk.core.CommandEventHandler):
    """Handles preview during editing - no geometry, just validation."""

    def __init__(self):
        super().__init__()

    def notify(self, args):
        # Don't create preview geometry during edit to avoid duplicate sketches
        # The compute handler will create the sketch when user clicks OK
        args.isValidResult = False


class EditValidateInputsHandler(adsk.core.ValidateInputsEventHandler):
    """Validates that inputs are valid."""

    def __init__(self):
        super().__init__()

    def notify(self, args):
        # All parameter inputs are always valid (spinners have min/max constraints)
        args.areInputsValid = True


class EditExecuteHandler(adsk.core.CommandEventHandler):
    """Handles edit execution - updates dependencies and parameters."""

    def __init__(self):
        super().__init__()

    def notify(self, args):
        global _edited_feature
        try:
            if not _edited_feature:
                return

            cmd = args.command
            inputs = cmd.commandInputs

            # Get new parameter values from inputs
            scale_x = inputs.itemById(INPUT_SCALE_X).value
            scale_y = inputs.itemById(INPUT_SCALE_Y).value
            offset_x = inputs.itemById(INPUT_OFFSET_X).value
            offset_y = inputs.itemById(INPUT_OFFSET_Y).value
            offset_normal = inputs.itemById(INPUT_OFFSET_NORMAL).value

            # Note: Updating dependencies (face/curves/edge) is not reliably supported
            # by the Fusion API. Users should recreate the feature to change these.

            # Update parameters
            params = _edited_feature.parameters
            if params.itemById("scaleX"):
                params.itemById("scaleX").value = scale_x
            if params.itemById("scaleY"):
                params.itemById("scaleY").value = scale_y
            if params.itemById("offsetX"):
                params.itemById("offsetX").value = offset_x
            if params.itemById("offsetY"):
                params.itemById("offsetY").value = offset_y
            if params.itemById("offsetNormal"):
                params.itemById("offsetNormal").value = offset_normal

            # Roll timeline forward to end
            design = adsk.fusion.Design.cast(_app.activeProduct)
            if design:
                design.timeline.moveToEnd()

            # Clear reference
            _edited_feature = None

        except:
            if _ui:
                _ui.messageBox(f"Edit execution failed:\n{traceback.format_exc()}")


def start(app: adsk.core.Application, ui: adsk.core.UserInterface):
    """Register the edit command with Fusion 360."""
    global _app, _ui
    _app = app
    _ui = ui

    try:
        # Create command definition
        cmd_def = ui.commandDefinitions.itemById(COMMAND_ID)
        if not cmd_def:
            cmd_def = ui.commandDefinitions.addButtonDefinition(
                COMMAND_ID, COMMAND_NAME, "Edit an existing Sketch On Face feature"
            )

        # Add command created handler
        on_command_created = EditCommandCreatedHandler()
        cmd_def.commandCreated.add(on_command_created)
        handlers.append(on_command_created)

    except:
        if ui:
            ui.messageBox(f"Failed to start edit command:\n{traceback.format_exc()}")


def stop(ui: adsk.core.UserInterface):
    """Unregister the edit command from Fusion 360."""
    global handlers, _edited_feature

    try:
        # Remove command definition
        cmd_def = ui.commandDefinitions.itemById(COMMAND_ID)
        if cmd_def:
            cmd_def.deleteMe()

        handlers = []
        _edited_feature = None

    except:
        if ui:
            ui.messageBox(f"Failed to stop edit command:\n{traceback.format_exc()}")
