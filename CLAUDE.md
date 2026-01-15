# SketchOnFace - Claude Code Instructions

## Project Overview
Fusion 360 add-in that wraps 2D sketch curves onto arbitrary 3D surfaces using arc-length parameterization.

## Architecture
```
SketchOnFace.py          → Entry point, registers command
commands/wrap_command.py → UI, event handlers, orchestration
core/surface_analyzer.py → Extract surface evaluator, find reference edge
core/sketch_parser.py    → Parse sketch geometry into point sequences
core/coordinate_mapper.py → Arc-length mapping (the key algorithm)
core/curve_generator.py  → Create output 3D splines
```

## Key Technical Details

### Arc-Length Parameterization
The core innovation over cylinder-only tools. In `coordinate_mapper.py`:
```python
edge_eval.getParameterAtLength(start_param, arc_length)
```
This API call lets Fusion's kernel handle elliptic integrals for non-uniform curves.

### Fusion 360 API Patterns
- Event handlers must be kept in a global `handlers` list to prevent garbage collection
- Use `isComputeDeferred = True` when creating multiple sketch entities for performance
- Selection filters: `'Faces'`, `'Edges'`, `'SketchCurves'`, `'SketchPoints'`

## Testing
1. Test with cylinders first (baseline, compare to Hans Kellner's tool)
2. Then test with ovals (the main use case)
3. Check Text Commands window in Fusion 360 for error output

## Common Issues
- If add-in doesn't appear: Check manifest JSON syntax
- If selections don't work: Verify selection filter strings match Fusion API exactly
- If curves distort: Check reference edge detection logic in surface_analyzer.py

## References
- [Fusion 360 API Docs](https://help.autodesk.com/view/fusion360/ENU/?guid=GUID-A92A4B10-3781-4925-94C6-47DA85A4F65A)
- [Hans Kellner's WrapSketch](https://github.com/hanskellner/Fusion360WrapSketch) - cylinder-only inspiration
