# Bootstrap 3D

A programmatic 3D graphics pipeline using Blender's Python API (`bpy`) for headless scene creation, character modeling, and rendering.

## Overview

This project provides a framework for creating 3D characters and scenes entirely through Python scripts, rendered headlessly via Blender. No GUI required.

## Requirements

- **Blender 4.0+** (`apt install blender`)
- **Xvfb** (`apt install xvfb`) - virtual framebuffer for headless rendering
- **Python 3.11+** with `trimesh`, `numpy`

## Quick Start

```bash
# Render the demo robot character
xvfb-run -a blender --background --python scripts/hello_3d.py -- --output renders/hello_robot.png

# Or use the helper script
./scripts/render_scene.sh scripts/hello_3d.py renders/hello_robot.png
```

## Project Structure

```
Bootstrap-3d/
  scripts/       # Blender Python scene scripts
  renders/       # Rendered output images
  models/        # Exported 3D model files (.blend, .glb, .obj)
```

## How It Works

Each script in `scripts/` defines a complete 3D scene:
1. **Geometry** - Build characters/objects from primitives or procedural mesh ops
2. **Materials** - PBR materials with color, metallic, roughness, emission
3. **Lighting** - Three-point lighting setups (key, fill, rim)
4. **Camera** - Framing and lens configuration
5. **Render** - Cycles path tracing to PNG output

Scripts run via `blender --background --python script.py` with `xvfb-run` providing the virtual display.

## Creating New Scenes

Write a Python script using `bpy` that:
1. Clears the default scene
2. Creates geometry and assigns materials
3. Sets up lighting and camera
4. Configures render settings
5. Calls `bpy.ops.render.render(write_still=True)`

See `scripts/hello_3d.py` for a complete example.
