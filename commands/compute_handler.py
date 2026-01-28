# Compute Handler - Recomputes CustomFeature when dependencies change

import traceback

import adsk.core
import adsk.fusion

from ..core import coordinate_mapper, curve_generator, sketch_parser, surface_analyzer


def _get_parameter_value(cust_feature, param_name, default_value):
    """
    Get parameter value from CustomFeature parameters or attributes.

    Tries attributes first (for edited features), then falls back to parameters
    (for initial creation). This ensures edited values take precedence.

    Args:
        cust_feature: The CustomFeature instance
        param_name: Name of the parameter
        default_value: Default value if neither parameter nor attribute exists

    Returns:
        The parameter value as a float
    """
    # Try getting from attributes first (edited features have priority)
    attrs = cust_feature.attributes
    attr = attrs.itemByName("SketchOnFace", param_name)
    if attr:
        return float(attr.value)

    # Fall back to parameters (initial creation)
    params = cust_feature.parameters
    try:
        param = params.itemById(param_name)
        if param:
            return param.value
    except Exception:
        # Parameter doesn't exist or can't be accessed
        pass

    # Use default if neither exists
    return default_value


class ComputeHandler(adsk.fusion.CustomFeatureEventHandler):
    """Handles recomputation of SketchOnFace custom features."""

    def __init__(self):
        super().__init__()

    def notify(self, args: adsk.fusion.CustomFeatureEventArgs):
        app = adsk.core.Application.get()
        ui = app.userInterface

        try:
            cust_feature = args.customFeature

            # Retrieve dependencies
            face_dep = cust_feature.dependencies.itemById("face")
            if not face_dep or not face_dep.entity:
                return

            face = face_dep.entity

            # Collect source curves from dependencies
            sketch_curves = []
            i = 0
            while True:
                curve_dep = cust_feature.dependencies.itemById(f"curve_{i}")
                if not curve_dep or not curve_dep.entity:
                    break
                sketch_curves.append(curve_dep.entity)
                i += 1

            if not sketch_curves:
                return

            # Collect parent sketches to hide after wrapping
            # Use dict keyed by entityToken to avoid duplicates (can't use set with Fusion objects)
            parent_sketches_dict = {}
            for curve in sketch_curves:
                try:
                    if hasattr(curve, 'parentSketch') and curve.parentSketch:
                        sketch = curve.parentSketch
                        parent_sketches_dict[sketch.entityToken] = sketch
                except Exception:
                    pass

            parent_sketches = list(parent_sketches_dict.values())

            # Get optional reference edge
            ref_edge = None
            edge_dep = cust_feature.dependencies.itemById("refEdge")
            if edge_dep and edge_dep.entity:
                ref_edge = edge_dep.entity

            # Retrieve parameters (from CustomFeature parameters or attributes)
            # Uses helper function that checks both parameters (initial creation) and
            # attributes (edited features) to support both workflows
            scale_x = _get_parameter_value(cust_feature, "scaleX", 1.0)
            scale_y = _get_parameter_value(cust_feature, "scaleY", 1.0)
            offset_x = _get_parameter_value(cust_feature, "offsetX", 0.0)
            offset_y = _get_parameter_value(cust_feature, "offsetY", 0.0)

            # Get offset parameter with backwards compatibility
            # BACKWARDS COMPATIBILITY: Prior to v1.1, the surface offset parameter was named "offset"
            # instead of "offsetNormal". We renamed it for clarity since "offset" is ambiguous.
            # Try the new name first, then fall back to the legacy name for old features.
            offset_normal = _get_parameter_value(cust_feature, "offsetNormal", 0.0)
            if offset_normal == 0.0:
                # Fall back to legacy "offset" parameter name for features created before v1.1
                offset_normal = _get_parameter_value(cust_feature, "offset", 0.0)

            # Get invert parameters (stored as 1.0/0.0 for true/false)
            invert_x = _get_parameter_value(cust_feature, "invertX", 0.0) > 0.5
            invert_y = _get_parameter_value(cust_feature, "invertY", 0.0) > 0.5

            # Analyze surface and generate new geometry
            design = adsk.fusion.Design.cast(app.activeProduct)
            root_comp = design.rootComponent

            try:
                surface_info = surface_analyzer.analyze(face, ref_edge)
            except Exception as e:
                ui.messageBox(
                    f"Failed to analyze surface. The face may have been deleted or modified.\n\n"
                    f"Error: {e}\n\n"
                    f"Try deleting and recreating the SketchOnFace feature."
                )
                return

            point_sequences = sketch_parser.parse(sketch_curves)
            mapped_sequences = coordinate_mapper.map_to_surface(
                point_sequences, surface_info, scale_x, scale_y,
                offset_x, offset_y, offset_normal, invert_x, invert_y
            )

            # Try to find existing BaseFeature to reuse (prevents timeline duplication during edits)
            base_feat = None
            base_feat_token = cust_feature.attributes.itemByName("SketchOnFace", "baseFeatureToken")

            if base_feat_token:
                try:
                    found_entities = design.findEntityByToken(base_feat_token.value)
                    if found_entities and len(found_entities) > 0:
                        entity = found_entities[0]
                        if entity.objectType == adsk.fusion.BaseFeature.classType():
                            base_feat = adsk.fusion.BaseFeature.cast(entity)
                except Exception:
                    pass  # Will create new one

            # Find existing sketch to update in place (preserves downstream references)
            existing_sketch = None
            old_sketch_token = cust_feature.attributes.itemByName("SketchOnFace", "sketchToken")
            if old_sketch_token:
                try:
                    found_entities = design.findEntityByToken(old_sketch_token.value)
                    if found_entities and len(found_entities) > 0:
                        entity = found_entities[0]
                        if entity.objectType == adsk.fusion.Sketch.classType():
                            existing_sketch = adsk.fusion.Sketch.cast(entity)
                except Exception:
                    pass  # Will create new one

            # Create or reuse base feature
            if not base_feat:
                base_feats = root_comp.features.baseFeatures
                base_feat = base_feats.add()

            if base_feat:
                base_feat.startEdit()
                try:
                    # Update existing sketch in place or create new one
                    new_sketch = curve_generator.generate(mapped_sequences, app, existing_sketch)
                    if new_sketch:
                        # Store sketch token (only needed if we created a new sketch)
                        if not existing_sketch:
                            attr = cust_feature.attributes.itemByName("SketchOnFace", "sketchToken")
                            if attr:
                                attr.value = new_sketch.entityToken
                            else:
                                cust_feature.attributes.add("SketchOnFace", "sketchToken", new_sketch.entityToken)
                finally:
                    base_feat.finishEdit()

                # Store base feature token (if newly created)
                if not base_feat_token:
                    cust_feature.attributes.add("SketchOnFace", "baseFeatureToken", base_feat.entityToken)

                # Group base feature with custom feature (only on initial creation)
                if not base_feat_token:
                    try:
                        timeline = design.timeline
                        base_timeline = base_feat.timelineObject
                        feat_timeline = cust_feature.timelineObject

                        if base_timeline and feat_timeline:
                            timeline.timelineGroups.add(feat_timeline.index, base_timeline.index)
                    except Exception:
                        pass  # Timeline grouping is optional UI enhancement

            # Hide parent sketches (Fusion UX pattern: hide source sketch after wrapping)
            for sketch in parent_sketches:
                try:
                    sketch.isVisible = False
                except Exception:
                    pass  # Hiding is optional UI enhancement

        except Exception as e:
            ui.messageBox(f"ComputeHandler failed:\n{e}\n{traceback.format_exc()}")
