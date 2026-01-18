<div align="center">
  <img src="resources/sketch-on-face-logo.png" alt="SketchOnFace Logo" width="400"/>
</div>

# SketchOnFace

A Fusion 360 add-in that wraps 2D sketch curves onto arbitrary 3D surfaces using arc-length parameterization.

## Features

- **Works with any surface** - Not limited to cylinders. Supports ovals, ellipses, cones, and freeform surfaces.
- **Arc-length parameterization** - Preserves proportions when wrapping onto non-uniform curves like ovals.
- **Auto-detect or manual edge selection** - Automatically finds the longest edge for wrap direction, or select one manually.
- **Scale and offset controls** - Adjust X/Y scale and surface offset distance.
- **Parametric editing** - Edit wrapped features through the timeline like native Fusion features.

## Installation

### Method 1: Direct Installation (Recommended)

1. **Download the add-in**
   - Click the green **Code** button on this repository
   - Select **Download ZIP**
   - Extract the ZIP file to a location on your computer (e.g., `Documents/Fusion360/AddIns/`)

2. **Install in Fusion 360**
   - Open Fusion 360
   - Go to **Tools** → **Add-Ins** → **Scripts and Add-Ins** (or press `Shift + S`)
   - Click the **Add-Ins** tab at the top
   - Click the green **+** icon next to "My Add-Ins"
   - Navigate to the extracted `SketchOnFace` folder and select it
   - The add-in should now appear in your list

3. **Run the add-in**
   - Select **SketchOnFace** from the list
   - Click **Run**
   - The **Sketch On Face** button will appear in the **Add-Ins** panel

4. **Run on Startup (Optional)**
   - Check the **Run on Startup** checkbox to automatically load the add-in when Fusion 360 starts

### Method 2: Git Clone (For Development)

```bash
cd ~/Documents/Fusion360/AddIns/
git clone https://github.com/yourusername/SketchOnFace.git
```

Then follow steps 2-4 from Method 1.

### Troubleshooting Installation

- **Add-in doesn't appear**: Make sure you selected the `SketchOnFace` folder itself, not a parent folder
- **Errors on startup**: Check the **Text Commands** window (Tools → Text Commands) for error messages
- **Button doesn't appear**: Try restarting Fusion 360 after installation

## Usage

1. Create a 2D sketch with your curves on any plane
2. Create or select a 3D body with the target surface
3. Run the **Sketch On Face** command from the Add-Ins panel
4. Select the target face
5. Select the sketch curves to wrap
6. (Optional) Select a reference edge to control wrap direction
7. Adjust scale and offset as needed
8. Click OK

## How It Works

Unlike simple projection which distorts geometry on non-cylindrical surfaces, SketchOnFace uses **arc-length parameterization**:

1. **Surface Analysis** - Extracts parametric bounds and identifies the reference edge
2. **Arc-Length Mapping** - Uses `CurveEvaluator.getParameterAtLength()` to map X coordinates to positions along the surface perimeter, preserving distances
3. **UV Mapping** - Converts 2D sketch coordinates to surface UV parameters
4. **3D Point Generation** - Samples points on the surface and creates fitted splines

This approach ensures that a horizontal line wraps evenly around an oval, with equal arc length on all sides.

## Supported Geometry

| Sketch Type | Support |
|-------------|---------|
| Fitted Splines | Full |
| Lines | Full |
| Arcs | Full |
| Circles | Full |
| Fixed Splines | Full |
| Points | Full |

## Limitations

- **Single face only** - V1 supports wrapping to a single face. Multi-face wrapping planned for future.
- **Orientation** - May need to experiment with reference edge selection for correct wrap direction.
- **Non-developable surfaces** - Some distortion is expected on doubly-curved surfaces (spheres, etc.)

## Acknowledgments

Inspired by [Fusion360WrapSketch](https://github.com/hanskellner/Fusion360WrapSketch) by Hans Kellner, which wraps sketches onto cylinders. SketchOnFace extends this concept to arbitrary surfaces using parametric surface mapping.

## License

MIT License - See LICENSE file for details.
