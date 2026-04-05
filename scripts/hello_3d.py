"""
Bootstrap 3D - Hello World Scene
Creates a simple robot character from primitives with materials, lighting,
and renders to an image. Proof-of-concept for the headless Blender pipeline.

Usage:
    xvfb-run -a blender --background --python scripts/hello_3d.py -- --output renders/hello_robot.png
"""

import bpy
import sys
import os
import math


def parse_args():
    """Parse arguments after the -- separator."""
    argv = sys.argv
    output = "renders/hello_robot.png"
    if "--" in argv:
        args = argv[argv.index("--") + 1:]
        for i, arg in enumerate(args):
            if arg == "--output" and i + 1 < len(args):
                output = args[i + 1]
    return output


def clear_scene():
    """Remove all default objects."""
    bpy.ops.object.select_all(action='SELECT')
    bpy.ops.object.delete()
    # Remove orphan data
    for block in bpy.data.meshes:
        if block.users == 0:
            bpy.data.meshes.remove(block)
    for block in bpy.data.materials:
        if block.users == 0:
            bpy.data.materials.remove(block)


def make_material(name, color, metallic=0.0, roughness=0.5):
    """Create a simple material with the given RGBA color."""
    mat = bpy.data.materials.new(name=name)
    mat.use_nodes = True
    bsdf = mat.node_tree.nodes["Principled BSDF"]
    bsdf.inputs["Base Color"].default_value = color
    bsdf.inputs["Metallic"].default_value = metallic
    bsdf.inputs["Roughness"].default_value = roughness
    return mat


def add_mesh(primitive_fn, name, location, scale, material, **kwargs):
    """Add a mesh primitive, position it, and assign a material."""
    primitive_fn(**kwargs)
    obj = bpy.context.active_object
    obj.name = name
    obj.location = location
    obj.scale = scale
    obj.data.materials.append(material)
    return obj


def create_robot():
    """Build a simple robot character from primitives."""
    # Materials
    body_mat = make_material("RobotBody", (0.2, 0.4, 0.8, 1.0), metallic=0.7, roughness=0.3)
    head_mat = make_material("RobotHead", (0.8, 0.8, 0.9, 1.0), metallic=0.8, roughness=0.2)
    eye_mat = make_material("RobotEye", (1.0, 0.2, 0.1, 1.0), metallic=0.0, roughness=0.1)
    joint_mat = make_material("RobotJoint", (0.3, 0.3, 0.3, 1.0), metallic=0.9, roughness=0.4)
    antenna_mat = make_material("Antenna", (1.0, 0.8, 0.0, 1.0), metallic=0.5, roughness=0.3)

    # Body (rounded cube approximated with a cube + subdivision)
    add_mesh(bpy.ops.mesh.primitive_cube_add, "Body",
             location=(0, 0, 1.0), scale=(0.6, 0.4, 0.8), material=body_mat)

    # Head
    add_mesh(bpy.ops.mesh.primitive_cube_add, "Head",
             location=(0, 0, 2.2), scale=(0.45, 0.35, 0.4), material=head_mat)

    # Eyes
    add_mesh(bpy.ops.mesh.primitive_uv_sphere_add, "LeftEye",
             location=(-0.18, -0.35, 2.3), scale=(0.08, 0.08, 0.08), material=eye_mat,
             radius=1, segments=16, ring_count=8)
    add_mesh(bpy.ops.mesh.primitive_uv_sphere_add, "RightEye",
             location=(0.18, -0.35, 2.3), scale=(0.08, 0.08, 0.08), material=eye_mat,
             radius=1, segments=16, ring_count=8)

    # Eye glow (emission)
    eye_mat.node_tree.nodes["Principled BSDF"].inputs["Emission Color"].default_value = (1.0, 0.2, 0.1, 1.0)
    eye_mat.node_tree.nodes["Principled BSDF"].inputs["Emission Strength"].default_value = 5.0

    # Antenna
    add_mesh(bpy.ops.mesh.primitive_cylinder_add, "AntennaPole",
             location=(0, 0, 2.8), scale=(0.03, 0.03, 0.25), material=joint_mat,
             radius=1, depth=1)
    add_mesh(bpy.ops.mesh.primitive_uv_sphere_add, "AntennaBall",
             location=(0, 0, 3.1), scale=(0.08, 0.08, 0.08), material=antenna_mat,
             radius=1, segments=16, ring_count=8)

    # Arms
    add_mesh(bpy.ops.mesh.primitive_cylinder_add, "LeftArm",
             location=(-0.8, 0, 1.2), scale=(0.08, 0.08, 0.4), material=joint_mat,
             radius=1, depth=1)
    add_mesh(bpy.ops.mesh.primitive_cylinder_add, "RightArm",
             location=(0.8, 0, 1.2), scale=(0.08, 0.08, 0.4), material=joint_mat,
             radius=1, depth=1)

    # Hands (spheres)
    add_mesh(bpy.ops.mesh.primitive_uv_sphere_add, "LeftHand",
             location=(-0.8, 0, 0.75), scale=(0.12, 0.12, 0.12), material=body_mat,
             radius=1, segments=16, ring_count=8)
    add_mesh(bpy.ops.mesh.primitive_uv_sphere_add, "RightHand",
             location=(0.8, 0, 0.75), scale=(0.12, 0.12, 0.12), material=body_mat,
             radius=1, segments=16, ring_count=8)

    # Legs
    add_mesh(bpy.ops.mesh.primitive_cylinder_add, "LeftLeg",
             location=(-0.25, 0, -0.1), scale=(0.1, 0.1, 0.4), material=joint_mat,
             radius=1, depth=1)
    add_mesh(bpy.ops.mesh.primitive_cylinder_add, "RightLeg",
             location=(0.25, 0, -0.1), scale=(0.1, 0.1, 0.4), material=joint_mat,
             radius=1, depth=1)

    # Feet (flattened cubes)
    add_mesh(bpy.ops.mesh.primitive_cube_add, "LeftFoot",
             location=(-0.25, -0.08, -0.55), scale=(0.14, 0.2, 0.06), material=body_mat)
    add_mesh(bpy.ops.mesh.primitive_cube_add, "RightFoot",
             location=(0.25, -0.08, -0.55), scale=(0.14, 0.2, 0.06), material=body_mat)


def setup_ground():
    """Add a ground plane with a subtle material."""
    ground_mat = make_material("Ground", (0.15, 0.15, 0.18, 1.0), metallic=0.0, roughness=0.8)
    add_mesh(bpy.ops.mesh.primitive_plane_add, "Ground",
             location=(0, 0, -0.62), scale=(5, 5, 1), material=ground_mat)


def setup_lighting():
    """Create a three-point lighting setup."""
    # Key light
    bpy.ops.object.light_add(type='AREA', location=(3, -3, 5))
    key = bpy.context.active_object
    key.name = "KeyLight"
    key.data.energy = 200
    key.data.size = 2
    key.data.color = (1.0, 0.95, 0.9)

    # Fill light
    bpy.ops.object.light_add(type='AREA', location=(-3, -2, 3))
    fill = bpy.context.active_object
    fill.name = "FillLight"
    fill.data.energy = 80
    fill.data.size = 3
    fill.data.color = (0.8, 0.85, 1.0)

    # Rim light
    bpy.ops.object.light_add(type='AREA', location=(0, 4, 4))
    rim = bpy.context.active_object
    rim.name = "RimLight"
    rim.data.energy = 120
    rim.data.size = 1.5
    rim.data.color = (1.0, 1.0, 1.0)


def setup_camera():
    """Position the camera to frame the robot."""
    bpy.ops.object.camera_add(location=(5.0, -5.0, 3.0))
    cam = bpy.context.active_object
    cam.name = "Camera"

    # Point camera at the robot's chest area
    constraint = cam.constraints.new(type='TRACK_TO')
    # Create an empty as the camera target
    bpy.ops.object.empty_add(location=(0, 0, 1.2))
    target = bpy.context.active_object
    target.name = "CameraTarget"
    constraint.target = target
    constraint.track_axis = 'TRACK_NEGATIVE_Z'
    constraint.up_axis = 'UP_Y'

    bpy.context.scene.camera = cam
    cam.data.lens = 35


def setup_world():
    """Set up a gradient background."""
    world = bpy.context.scene.world
    if world is None:
        world = bpy.data.worlds.new("World")
        bpy.context.scene.world = world
    world.use_nodes = True
    nodes = world.node_tree.nodes
    links = world.node_tree.links

    # Clear existing nodes
    for node in nodes:
        nodes.remove(node)

    # Background
    bg = nodes.new('ShaderNodeBackground')
    bg.inputs['Color'].default_value = (0.05, 0.05, 0.1, 1.0)
    bg.inputs['Strength'].default_value = 0.5

    output = nodes.new('ShaderNodeOutputWorld')
    links.new(bg.outputs['Background'], output.inputs['Surface'])


def configure_render(output_path):
    """Configure render settings for quality output."""
    scene = bpy.context.scene

    # Use Cycles for better quality
    scene.render.engine = 'CYCLES'
    scene.cycles.device = 'CPU'
    scene.cycles.samples = 128
    scene.cycles.use_denoising = False

    # Output settings
    scene.render.resolution_x = 1920
    scene.render.resolution_y = 1080
    scene.render.resolution_percentage = 100
    scene.render.image_settings.file_format = 'PNG'
    scene.render.image_settings.color_mode = 'RGBA'
    scene.render.filepath = os.path.abspath(output_path)

    # Film
    scene.render.film_transparent = False


def main():
    output_path = parse_args()

    # Ensure output directory exists
    os.makedirs(os.path.dirname(os.path.abspath(output_path)), exist_ok=True)

    print(f"=== Bootstrap 3D - Hello Robot ===")
    print(f"Output: {output_path}")

    clear_scene()
    create_robot()
    setup_ground()
    setup_lighting()
    setup_camera()
    setup_world()
    configure_render(output_path)

    # Export the scene as .blend file
    blend_path = output_path.replace('.png', '.blend')
    bpy.ops.wm.save_as_mainfile(filepath=os.path.abspath(blend_path))
    print(f"Scene saved: {blend_path}")

    # Render
    print("Rendering...")
    bpy.ops.render.render(write_still=True)
    print(f"Render complete: {output_path}")


if __name__ == "__main__":
    main()
