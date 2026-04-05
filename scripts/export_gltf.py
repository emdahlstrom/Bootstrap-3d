"""
Export a Blender scene to glTF/GLB format for web viewing.

Usage:
    xvfb-run -a blender --background renders/hello_robot.blend --python scripts/export_gltf.py -- --output models/hello_robot.glb
"""

import bpy
import sys
import os


def parse_args():
    argv = sys.argv
    output = "models/hello_robot.glb"
    if "--" in argv:
        args = argv[argv.index("--") + 1:]
        for i, arg in enumerate(args):
            if arg == "--output" and i + 1 < len(args):
                output = args[i + 1]
    return output


def main():
    output = parse_args()
    os.makedirs(os.path.dirname(os.path.abspath(output)), exist_ok=True)

    abs_output = os.path.abspath(output)

    print(f"Exporting to: {abs_output}")
    bpy.ops.export_scene.gltf(
        filepath=abs_output,
        export_format='GLB',
        use_selection=False,
        export_apply=True,
        export_materials='EXPORT',
        export_lights=True,
        export_cameras=True,
    )
    print(f"Export complete: {abs_output}")


if __name__ == "__main__":
    main()
