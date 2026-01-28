# Edit Command - Handles editing existing SketchOnFace custom features

import traceback

import adsk.core
import adsk.fusion

from ..core import logger

# Command identity
COMMAND_ID = "SketchOnFaceEditCommand"
COMMAND_NAME = "Edit Sketch On Face"

# Input IDs (parameters only - face/curves/edge cannot be changed after creation)
INPUT_SCALE_X = COMMAND_ID + "_scaleX"
INPUT_SCALE_Y = COMMAND_ID + "_scaleY"
INPUT_OFFSET_X = COMMAND_ID + "_offsetX"
INPUT_OFFSET_Y = COMMAND_ID + "_offsetY"
INPUT_OFFSET_NORMAL = COMMAND_ID + "_offsetNormal"
INPUT_INVERT_X = COMMAND_ID + "_invertX"
INPUT_INVERT_Y = COMMAND_ID + "_invertY"

# Global event handlers
handlers = []

# Global references
_app = None
_ui = None
_edited_feature = None
_custom_feature_def = None


def _get_parameter_value(cust_feature, param_name, default_value):
    """
    Get parameter value from CustomFeature parameters or attributes.

    Tries attributes first (edited features always use attributes), then falls back
    to parameters (for features that have never been edited).

    Args:
        cust_feature: The CustomFeature instance
        param_name: Name of the parameter
        default_value: Default value if neither parameter nor attribute exists

    Returns:
        The parameter value as a float (always in internal units - cm)
    """
    # Try getting from attributes first (edited features)
    # Attributes always have the latest values after any edit
    attrs = cust_feature.attributes
    attr = attrs.itemByName("SketchOnFace", param_name)
    if attr:
        return float(attr.value)

    # Fall back to parameters (initial creation, never edited)
    params = cust_feature.parameters
    try:
        param = params.itemById(param_name)
        if param:
            # Parameters store values in internal units (cm)
            # Just return directly - no conversion needed
            return param.value
    except Exception as e:
        # Parameter doesn't exist or can't be accessed
        from ..core import logger
        logger.log(f"SketchOnFace Edit: Failed to get parameter '{param_name}': {e}")

    # Use default if neither exists
    return default_value


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

            # Get current parameter values (from parameters or attributes)
            # Uses helper function that checks both sources to support both initial creation
            # and edited features
            current_scale_x = _get_parameter_value(_edited_feature, "scaleX", 1.0)
            current_scale_y = _get_parameter_value(_edited_feature, "scaleY", 1.0)
            current_offset_x = _get_parameter_value(_edited_feature, "offsetX", 0.0)
            current_offset_y = _get_parameter_value(_edited_feature, "offsetY", 0.0)

            # Get offset parameter with backwards compatibility
            # BACKWARDS COMPATIBILITY: Prior to v1.1, the surface offset parameter was named "offset"
            # instead of "offsetNormal". We renamed it for clarity since "offset" is ambiguous.
            # Try the new name first, then fall back to the legacy name for old features.
            current_offset_normal = _get_parameter_value(_edited_feature, "offsetNormal", 0.0)
            if current_offset_normal == 0.0:
                # Fall back to legacy "offset" parameter name for features created before v1.1
                current_offset_normal = _get_parameter_value(_edited_feature, "offset", 0.0)

            logger.log(f"SketchOnFace Edit: Read from storage - current_offset_normal={current_offset_normal} cm")

            # IMPORTANT: Values are stored in internal units (cm).
            # For spinner with units="mm", the initial value is in DISPLAY units (mm).
            # So we need to convert cm → mm for display.
            current_offset_normal_mm = current_offset_normal * 10.0

            logger.log(f"SketchOnFace Edit: Will display value - {current_offset_normal} cm = {current_offset_normal_mm} mm")

            # Get invert parameters (stored as 1.0/0.0 for true/false)
            current_invert_x = _get_parameter_value(_edited_feature, "invertX", 0.0) > 0.5
            current_invert_y = _get_parameter_value(_edited_feature, "invertY", 0.0) > 0.5

            # === UI INPUTS ===
            # Note: Face/curves/edge cannot be changed after creation - only parameters

            # X Scale
            scale_x_input = inputs.addFloatSpinnerCommandInput(
                INPUT_SCALE_X, "X Scale", "", 0.01, 100.0, 0.1, current_scale_x
            )

            # Y Scale
            scale_y_input = inputs.addFloatSpinnerCommandInput(
                INPUT_SCALE_Y, "Y Scale", "", 0.01, 100.0, 0.1, current_scale_y
            )

            # X Offset
            offset_x_input = inputs.addFloatSpinnerCommandInput(
                INPUT_OFFSET_X, "X Offset", "", -1.0, 1.0, 0.05, current_offset_x
            )

            # Y Offset
            offset_y_input = inputs.addFloatSpinnerCommandInput(
                INPUT_OFFSET_Y, "Y Offset", "", -1.0, 1.0, 0.05, current_offset_y
            )

            # Surface normal offset
            # Use units="mm" to match the initial creation spinner
            # Pass the value in DISPLAY units (mm) - Fusion expects this!
            logger.log(f"SketchOnFace Edit: About to create spinner with value={current_offset_normal_mm} mm")
            try:
                offset_normal_input = inputs.addFloatSpinnerCommandInput(
                    INPUT_OFFSET_NORMAL, "Surface Offset", "mm", -100.0, 100.0, 0.1,
                    current_offset_normal_mm
                )
                logger.log(f"SketchOnFace Edit: Spinner created successfully")
            except Exception as e:
                logger.log(f"SketchOnFace Edit: Failed to create spinner: {e}")
                # Fallback: create without initial value
                offset_normal_input = inputs.addFloatSpinnerCommandInput(
                    INPUT_OFFSET_NORMAL, "Surface Offset", "mm", -100.0, 100.0, 0.1, 0.0
                )

            # Invert options for orientation control
            inputs.addBoolValueInput(INPUT_INVERT_X, "Invert X (Wrap Direction)", True, "", current_invert_x)
            inputs.addBoolValueInput(INPUT_INVERT_Y, "Invert Y (Height Direction)", True, "", current_invert_y)

        except Exception as e:
            logger.log(f"SketchOnFace Edit: Command creation failed: {e}\n{traceback.format_exc()}")
            if _ui:
                _ui.messageBox(
                    f"Edit command created failed:\n{e}\n{traceback.format_exc()}"
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

        except Exception as e:
            print(f"Edit activate failed: {e}\n{traceback.format_exc()}")


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

            # IMPORTANT: The offset_normal spinner has units="mm".
            # When we read .value, Fusion returns it in internal units (cm).
            # No conversion needed - just store directly.
            offset_normal_input = inputs.itemById(INPUT_OFFSET_NORMAL)
            offset_normal = offset_normal_input.value  # Already in cm (internal units)

            # Get invert values
            invert_x = inputs.itemById(INPUT_INVERT_X).value
            invert_y = inputs.itemById(INPUT_INVERT_Y).value

            logger.log(f"SketchOnFace Edit: Read from inputs - offsetNormal.value={offset_normal} cm, invertX={invert_x}, invertY={invert_y}")

            # Note: CustomFeature parameters are stored in attributes, not real parameters.
            # We update the attributes and force a recompute.

            design = adsk.fusion.Design.cast(_app.activeProduct)
            if not design:
                _ui.messageBox("No active design found.")
                return

            # Store new values in attributes (which the compute handler reads)
            attrs = _edited_feature.attributes

            logger.log(f"SketchOnFace Edit: Storing scaleX={scale_x}, scaleY={scale_y}, offsetX={offset_x}, offsetY={offset_y}, offsetNormal={offset_normal}, invertX={invert_x}, invertY={invert_y}")

            # Update or create attribute values
            if attrs.itemByName("SketchOnFace", "scaleX"):
                attrs.itemByName("SketchOnFace", "scaleX").value = str(scale_x)
            else:
                attrs.add("SketchOnFace", "scaleX", str(scale_x))

            if attrs.itemByName("SketchOnFace", "scaleY"):
                attrs.itemByName("SketchOnFace", "scaleY").value = str(scale_y)
            else:
                attrs.add("SketchOnFace", "scaleY", str(scale_y))

            if attrs.itemByName("SketchOnFace", "offsetX"):
                attrs.itemByName("SketchOnFace", "offsetX").value = str(offset_x)
            else:
                attrs.add("SketchOnFace", "offsetX", str(offset_x))

            if attrs.itemByName("SketchOnFace", "offsetY"):
                attrs.itemByName("SketchOnFace", "offsetY").value = str(offset_y)
            else:
                attrs.add("SketchOnFace", "offsetY", str(offset_y))

            if attrs.itemByName("SketchOnFace", "offsetNormal"):
                attrs.itemByName("SketchOnFace", "offsetNormal").value = str(offset_normal)
            else:
                attrs.add("SketchOnFace", "offsetNormal", str(offset_normal))

            # Store invert values (as 1.0/0.0 for true/false)
            invert_x_val = 1.0 if invert_x else 0.0
            invert_y_val = 1.0 if invert_y else 0.0

            if attrs.itemByName("SketchOnFace", "invertX"):
                attrs.itemByName("SketchOnFace", "invertX").value = str(invert_x_val)
            else:
                attrs.add("SketchOnFace", "invertX", str(invert_x_val))

            if attrs.itemByName("SketchOnFace", "invertY"):
                attrs.itemByName("SketchOnFace", "invertY").value = str(invert_y_val)
            else:
                attrs.add("SketchOnFace", "invertY", str(invert_y_val))

            # Force the custom feature to recompute
            # Strategy: Update just ONE parameter to trigger the compute handler.
            # The compute handler reads ALL values from attributes (which we've already updated).
            # This ensures only a single recompute instead of one per parameter.
            logger.log(f"SketchOnFace Edit: Triggering recompute by updating single parameter")

            try:
                # Get the parameter collection
                params = _edited_feature.parameters

                # Update only the first parameter to trigger compute handler
                # The compute handler will read all values from attributes
                param_scale_x = params.itemById("scaleX")
                if param_scale_x:
                    # Changing the expression triggers the compute handler
                    param_scale_x.expression = str(scale_x)
                    logger.log(f"SketchOnFace Edit: Updated scaleX parameter to trigger recompute")

            except Exception as e:
                logger.log(f"SketchOnFace Edit: Parameter update failed: {e}")
                # If parameter update fails, try to force recompute another way
                logger.log(f"SketchOnFace Edit: Will try to force recompute via timeline")

            # Clear reference
            _edited_feature = None

        except Exception as e:
            if _ui:
                _ui.messageBox(f"Edit execution failed:\n{e}\n{traceback.format_exc()}")


def start(app: adsk.core.Application, ui: adsk.core.UserInterface, custom_feature_def=None):
    """Register the edit command with Fusion 360."""
    global _app, _ui, _custom_feature_def
    _app = app
    _ui = ui
    _custom_feature_def = custom_feature_def

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

    except Exception as e:
        if ui:
            ui.messageBox(f"Failed to start edit command:\n{e}\n{traceback.format_exc()}")


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

    except Exception as e:
        if ui:
            ui.messageBox(f"Failed to stop edit command:\n{e}\n{traceback.format_exc()}")
