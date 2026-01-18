# Wrap Command - UI and event handlers for SketchOnFace

import traceback

import adsk.core
import adsk.fusion

print("SketchOnFace: Loading wrap_command module...")

try:
    from ..core import (
        coordinate_mapper,
        curve_generator,
        sketch_parser,
        surface_analyzer,
    )

    print("SketchOnFace: Core modules imported successfully")
except Exception as e:
    print(f"SketchOnFace: Failed to import core modules: {e}")
    print(traceback.format_exc())

# Command identity
COMMAND_ID = "SketchOnFaceCommand"
COMMAND_NAME = "Sketch On Face"
COMMAND_DESCRIPTION = "Wrap 2D sketch curves onto a 3D surface."
COMMAND_RESOURCES = "./resources"

# Input IDs
INPUT_FACE = COMMAND_ID + "_face"
INPUT_SKETCH = COMMAND_ID + "_sketch"
INPUT_EDGE = COMMAND_ID + "_edge"
INPUT_SCALE_X = COMMAND_ID + "_scaleX"
INPUT_SCALE_Y = COMMAND_ID + "_scaleY"
INPUT_OFFSET_X = COMMAND_ID + "_offsetX"
INPUT_OFFSET_Y = COMMAND_ID + "_offsetY"
INPUT_OFFSET_NORMAL = COMMAND_ID + "_offsetNormal"

# Global event handlers (prevent garbage collection)
handlers = []

# Global app/ui references
_app = None
_ui = None
_custom_feature_def = None
_preview_sketch = None  # Track preview sketch for cleanup


class CommandCreatedHandler(adsk.core.CommandCreatedEventHandler):
    """Handles command creation - builds the UI."""

    def __init__(self):
        super().__init__()

    def notify(self, args: adsk.core.CommandCreatedEventArgs):
        try:
            cmd = args.command
            inputs = cmd.commandInputs

            # Add event handlers
            on_execute = ExecuteHandler()
            cmd.execute.add(on_execute)
            handlers.append(on_execute)

            on_preview = PreviewHandler()
            cmd.executePreview.add(on_preview)
            handlers.append(on_preview)

            on_validate = ValidateInputsHandler()
            cmd.validateInputs.add(on_validate)
            handlers.append(on_validate)

            on_destroy = CommandDestroyHandler()
            cmd.destroy.add(on_destroy)
            handlers.append(on_destroy)

            on_input_changed = InputChangedHandler()
            cmd.inputChanged.add(on_input_changed)
            handlers.append(on_input_changed)

            # === UI INPUTS ===

            # Face selection (required)
            face_input = inputs.addSelectionInput(
                INPUT_FACE, "Target Face", "Select the face to wrap sketch onto"
            )
            face_input.addSelectionFilter("Faces")
            face_input.setSelectionLimits(1, 1)

            # Sketch curve selection (required)
            sketch_input = inputs.addSelectionInput(
                INPUT_SKETCH, "Sketch Curves", "Select sketch curves to wrap"
            )
            sketch_input.addSelectionFilter("SketchCurves")
            sketch_input.addSelectionFilter("SketchPoints")
            sketch_input.setSelectionLimits(1, 0)  # 1 minimum, unlimited maximum

            # Reference edge selection (optional - for manual override)
            edge_input = inputs.addSelectionInput(
                INPUT_EDGE,
                "Reference Edge (Optional)",
                "Select edge to define wrap direction. Auto-detects if not specified.",
            )
            edge_input.addSelectionFilter("Edges")
            edge_input.setSelectionLimits(0, 1)  # Optional

            # X Scale
            inputs.addFloatSpinnerCommandInput(
                INPUT_SCALE_X,
                "X Scale",
                "",
                0.01,  # min
                100.0,  # max
                0.1,  # step
                1.0,  # initial
            )

            # Y Scale
            inputs.addFloatSpinnerCommandInput(
                INPUT_SCALE_Y, "Y Scale", "", 0.01, 100.0, 0.1, 1.0
            )

            # X Offset (wrap direction, 0-1 where 1 = full circumference)
            inputs.addFloatSpinnerCommandInput(
                INPUT_OFFSET_X, "X Offset", "", -1.0, 1.0, 0.05, 0.0
            )

            # Y Offset (height direction, 0-1 where 1 = full height)
            inputs.addFloatSpinnerCommandInput(
                INPUT_OFFSET_Y, "Y Offset", "", -1.0, 1.0, 0.05, 0.0
            )

            # Surface normal offset (distance from surface)
            inputs.addFloatSpinnerCommandInput(
                INPUT_OFFSET_NORMAL, "Surface Offset", "mm", -100.0, 100.0, 0.1, 0.0
            )

        except Exception as e:
            if _ui:
                _ui.messageBox(f"Command created failed:\n{e}\n{traceback.format_exc()}")


class ExecuteHandler(adsk.core.CommandEventHandler):
    """Handles command execution - performs the wrap operation."""

    def __init__(self):
        super().__init__()

    def notify(self, args):
        global _preview_sketch
        try:
            # Clean up preview sketch before creating the CustomFeature
            if _preview_sketch:
                try:
                    _preview_sketch.deleteMe()
                except Exception as e:
                    print(f"SketchOnFace: Failed to delete preview sketch: {e}")
                    # Continue execution - preview cleanup failure is non-critical
                _preview_sketch = None

            cmd = args.command
            inputs = cmd.commandInputs

            # Get input values
            face_input = inputs.itemById(INPUT_FACE)
            sketch_input = inputs.itemById(INPUT_SKETCH)
            edge_input = inputs.itemById(INPUT_EDGE)
            scale_x_input = inputs.itemById(INPUT_SCALE_X)
            scale_y_input = inputs.itemById(INPUT_SCALE_Y)
            offset_x_input = inputs.itemById(INPUT_OFFSET_X)
            offset_y_input = inputs.itemById(INPUT_OFFSET_Y)
            offset_normal_input = inputs.itemById(INPUT_OFFSET_NORMAL)

            # Extract selected entities
            face = face_input.selection(0).entity

            sketch_curves = []
            for i in range(sketch_input.selectionCount):
                sketch_curves.append(sketch_input.selection(i).entity)

            ref_edge = None
            if edge_input.selectionCount > 0:
                ref_edge = edge_input.selection(0).entity

            scale_x = scale_x_input.value
            scale_y = scale_y_input.value
            offset_x = offset_x_input.value
            offset_y = offset_y_input.value
            offset_normal = offset_normal_input.value

            # Create CustomFeature - the compute handler will create the sketch
            if _custom_feature_def:
                _create_custom_feature(
                    face, sketch_curves, ref_edge, scale_x, scale_y,
                    offset_x, offset_y, offset_normal
                )
            else:
                # Fallback if CustomFeature not available - create sketch directly
                surface_info = surface_analyzer.analyze(face, ref_edge)
                point_sequences = sketch_parser.parse(sketch_curves)
                mapped_sequences = coordinate_mapper.map_to_surface(
                    point_sequences, surface_info, scale_x, scale_y,
                    offset_x, offset_y, offset_normal
                )
                curve_generator.generate(mapped_sequences, _app)

        except Exception as e:
            _ui.messageBox(f"Execution failed:\n{e}\n{traceback.format_exc()}")


class PreviewHandler(adsk.core.CommandEventHandler):
    """Handles preview - shows temporary geometry before commit."""

    def __init__(self):
        super().__init__()

    def notify(self, args):
        global _preview_sketch
        try:
            # Clean up previous preview
            if _preview_sketch:
                try:
                    _preview_sketch.deleteMe()
                except Exception as e:
                    print(f"SketchOnFace: Failed to delete preview sketch: {e}")
                    # Continue execution - preview cleanup failure is non-critical
                _preview_sketch = None

            cmd = args.command
            inputs = cmd.commandInputs

            face_input = inputs.itemById(INPUT_FACE)
            sketch_input = inputs.itemById(INPUT_SKETCH)
            edge_input = inputs.itemById(INPUT_EDGE)
            scale_x_input = inputs.itemById(INPUT_SCALE_X)
            scale_y_input = inputs.itemById(INPUT_SCALE_Y)
            offset_x_input = inputs.itemById(INPUT_OFFSET_X)
            offset_y_input = inputs.itemById(INPUT_OFFSET_Y)
            offset_normal_input = inputs.itemById(INPUT_OFFSET_NORMAL)

            # Check we have required inputs
            if face_input.selectionCount < 1 or sketch_input.selectionCount < 1:
                args.isValidResult = False
                return

            face = face_input.selection(0).entity

            sketch_curves = []
            for i in range(sketch_input.selectionCount):
                sketch_curves.append(sketch_input.selection(i).entity)

            ref_edge = None
            if edge_input.selectionCount > 0:
                ref_edge = edge_input.selection(0).entity

            scale_x = scale_x_input.value
            scale_y = scale_y_input.value
            offset_x = offset_x_input.value
            offset_y = offset_y_input.value
            offset_normal = offset_normal_input.value

            # Create preview geometry
            surface_info = surface_analyzer.analyze(face, ref_edge)
            point_sequences = sketch_parser.parse(sketch_curves)
            mapped_sequences = coordinate_mapper.map_to_surface(
                point_sequences, surface_info, scale_x, scale_y,
                offset_x, offset_y, offset_normal
            )
            _preview_sketch = curve_generator.generate(mapped_sequences, _app)

            # Set to False so ExecuteHandler runs and creates the CustomFeature
            # The preview geometry is visible but won't be "committed" by Fusion
            args.isValidResult = False

        except Exception as e:
            print(f"SketchOnFace: Preview handler error: {e}")
            args.isValidResult = False


class ValidateInputsHandler(adsk.core.ValidateInputsEventHandler):
    """Validates that required inputs are selected."""

    def __init__(self):
        super().__init__()

    def notify(self, args):
        try:
            cmd = args.firingEvent.sender
            inputs = cmd.commandInputs

            face_input = inputs.itemById(INPUT_FACE)
            sketch_input = inputs.itemById(INPUT_SKETCH)

            # Require at least face and one sketch curve
            args.areInputsValid = (
                face_input.selectionCount == 1 and sketch_input.selectionCount >= 1
            )

        except Exception as e:
            print(f"SketchOnFace: Input validation failed: {e}")
            args.areInputsValid = False


class InputChangedHandler(adsk.core.InputChangedEventHandler):
    """Handles input changes for preview updates."""

    def __init__(self):
        super().__init__()

    def notify(self, args: adsk.core.InputChangedEventArgs):
        # Future: Could add live preview here
        pass


class CommandDestroyHandler(adsk.core.CommandEventHandler):
    """Handles command destruction - cleanup."""

    def __init__(self):
        super().__init__()

    def notify(self, args):
        # Don't clear handlers here - it removes the CommandCreatedHandler
        # which prevents the command from being run again
        pass


def _create_custom_feature(
    face, sketch_curves, ref_edge, scale_x, scale_y, offset_x, offset_y, offset_normal
):
    """Create a CustomFeature - compute handler will create the sketch."""
    try:
        design = adsk.fusion.Design.cast(_app.activeProduct)
        if not design:
            return

        root_comp = design.rootComponent

        # Create custom feature input
        cust_feat_input = root_comp.features.customFeatures.createInput(
            _custom_feature_def
        )

        # Add dependencies (entities that trigger recompute when changed)
        cust_feat_input.addDependency("face", face)
        for i, curve in enumerate(sketch_curves):
            cust_feat_input.addDependency(f"curve_{i}", curve)
        if ref_edge:
            cust_feat_input.addDependency("refEdge", ref_edge)

        # Add parameters (internal to CustomFeature, edited via edit dialog)
        # Set isVisible=False to prevent cluttering the Parameters panel
        cust_feat_input.addCustomParameter(
            "scaleX", "X Scale", adsk.core.ValueInput.createByReal(scale_x), "", False
        )
        cust_feat_input.addCustomParameter(
            "scaleY", "Y Scale", adsk.core.ValueInput.createByReal(scale_y), "", False
        )
        cust_feat_input.addCustomParameter(
            "offsetX", "X Offset", adsk.core.ValueInput.createByReal(offset_x), "", False
        )
        cust_feat_input.addCustomParameter(
            "offsetY", "Y Offset", adsk.core.ValueInput.createByReal(offset_y), "", False
        )
        cust_feat_input.addCustomParameter(
            "offsetNormal", "Surface Offset",
            adsk.core.ValueInput.createByReal(offset_normal), "mm", False
        )

        # Create the custom feature - this triggers the compute handler
        root_comp.features.customFeatures.add(cust_feat_input)

    except Exception as e:
        if _ui:
            _ui.messageBox(
                f"CustomFeature creation failed:\n{e}\n{traceback.format_exc()}"
            )


def start(
    app: adsk.core.Application, ui: adsk.core.UserInterface, custom_feature_def=None
):
    """Register the command with Fusion 360."""
    global _app, _ui, _custom_feature_def
    _app = app
    _ui = ui
    _custom_feature_def = custom_feature_def

    try:
        # Create command definition
        cmd_def = ui.commandDefinitions.itemById(COMMAND_ID)
        if not cmd_def:
            cmd_def = ui.commandDefinitions.addButtonDefinition(
                COMMAND_ID, COMMAND_NAME, COMMAND_DESCRIPTION, COMMAND_RESOURCES
            )

        # Add command created handler
        on_command_created = CommandCreatedHandler()
        cmd_def.commandCreated.add(on_command_created)
        handlers.append(on_command_created)

        # Add to Add-Ins panel
        panel = ui.allToolbarPanels.itemById("SolidScriptsAddinsPanel")
        if panel:
            button = panel.controls.itemById(COMMAND_ID)
            if not button:
                button = panel.controls.addCommand(cmd_def)
                button.isPromotedByDefault = True
                button.isPromoted = True

    except Exception as e:
        if ui:
            ui.messageBox(f"Failed to start command:\n{e}\n{traceback.format_exc()}")


def stop(ui: adsk.core.UserInterface):
    """Unregister the command from Fusion 360."""
    global handlers, _custom_feature_def

    try:
        # Remove from panel
        panel = ui.allToolbarPanels.itemById("SolidScriptsAddinsPanel")
        if panel:
            button = panel.controls.itemById(COMMAND_ID)
            if button:
                button.deleteMe()

        # Remove command definition
        cmd_def = ui.commandDefinitions.itemById(COMMAND_ID)
        if cmd_def:
            cmd_def.deleteMe()

        handlers = []
        _custom_feature_def = None

    except Exception as e:
        if ui:
            ui.messageBox(f"Failed to stop command:\n{e}\n{traceback.format_exc()}")
