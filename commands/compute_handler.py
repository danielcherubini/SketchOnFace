# Compute Handler - Recomputes CustomFeature when dependencies change

import traceback

import adsk.core
import adsk.fusion

from ..core import coordinate_mapper, curve_generator, sketch_parser, surface_analyzer


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

            # Get optional reference edge
            ref_edge = None
            edge_dep = cust_feature.dependencies.itemById("refEdge")
            if edge_dep and edge_dep.entity:
                ref_edge = edge_dep.entity

            # Retrieve parameters
            params = cust_feature.parameters
            scale_x = (
                params.itemById("scaleX").value if params.itemById("scaleX") else 1.0
            )
            scale_y = (
                params.itemById("scaleY").value if params.itemById("scaleY") else 1.0
            )
            offset_x = (
                params.itemById("offsetX").value if params.itemById("offsetX") else 0.0
            )
            offset_y = (
                params.itemById("offsetY").value if params.itemById("offsetY") else 0.0
            )
            offset_normal = (
                params.itemById("offsetNormal").value
                if params.itemById("offsetNormal")
                else (params.itemById("offset").value if params.itemById("offset") else 0.0)
            )

            # Delete old base feature and sketch if they exist
            design = adsk.fusion.Design.cast(app.activeProduct)

            # Delete old base feature (which contains the sketch)
            old_base_token = cust_feature.attributes.itemByName(
                "SketchOnFace", "baseFeatureToken"
            )
            if old_base_token:
                try:
                    old_base = design.findEntityByToken(old_base_token.value)
                    if old_base and len(old_base) > 0:
                        old_base[0].deleteMe()
                except:
                    pass

            # Also try to delete old sketch directly (for backwards compatibility)
            old_sketch_token = cust_feature.attributes.itemByName(
                "SketchOnFace", "sketchToken"
            )
            if old_sketch_token:
                try:
                    old_sketch = design.findEntityByToken(old_sketch_token.value)
                    if old_sketch and len(old_sketch) > 0:
                        old_sketch[0].deleteMe()
                except:
                    pass

            # Recompute the wrapped sketch using a Base Feature to encapsulate it
            surface_info = surface_analyzer.analyze(face, ref_edge)
            point_sequences = sketch_parser.parse(sketch_curves)
            mapped_sequences = coordinate_mapper.map_to_surface(
                point_sequences, surface_info, scale_x, scale_y,
                offset_x, offset_y, offset_normal
            )

            # Use Base Feature to encapsulate the sketch creation
            root_comp = design.rootComponent
            base_feats = root_comp.features.baseFeatures

            # Create base feature and add sketch inside it
            base_feat = base_feats.add()
            if base_feat:
                base_feat.startEdit()
                try:
                    new_sketch = curve_generator.generate(mapped_sequences, app)
                    if new_sketch:
                        cust_feature.attributes.add(
                            "SketchOnFace", "sketchToken", new_sketch.entityToken
                        )
                finally:
                    base_feat.finishEdit()

                # Store base feature token for cleanup
                cust_feature.attributes.add(
                    "SketchOnFace", "baseFeatureToken", base_feat.entityToken
                )

                # Group base feature with custom feature
                try:
                    timeline = design.timeline
                    feat_timeline = cust_feature.timelineObject
                    base_timeline = base_feat.timelineObject
                    if feat_timeline and base_timeline:
                        timeline.timelineGroups.add(
                            feat_timeline.index, base_timeline.index
                        )
                except:
                    pass

        except Exception as e:
            ui.messageBox(f"ComputeHandler failed:\n{e}\n{traceback.format_exc()}")
