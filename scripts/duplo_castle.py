"""
Bootstrap 3D - Lego Duplo Castle
A colorful Duplo-style castle with transparent walls and sparkly gems.

Usage:
    xvfb-run -a blender --background --python scripts/duplo_castle.py -- --output renders/duplo_castle.png
"""

import bpy
import sys
import os
import math
import random


def parse_args():
    argv = sys.argv
    output = "renders/duplo_castle.png"
    if "--" in argv:
        args = argv[argv.index("--") + 1:]
        for i, arg in enumerate(args):
            if arg == "--output" and i + 1 < len(args):
                output = args[i + 1]
    return output


def clear_scene():
    bpy.ops.object.select_all(action='SELECT')
    bpy.ops.object.delete()
    for block in bpy.data.meshes:
        if block.users == 0:
            bpy.data.meshes.remove(block)
    for block in bpy.data.materials:
        if block.users == 0:
            bpy.data.materials.remove(block)


# ─── Materials ───

def mat_solid(name, color, roughness=0.4):
    """Solid plastic Duplo material."""
    mat = bpy.data.materials.new(name=name)
    mat.use_nodes = True
    bsdf = mat.node_tree.nodes["Principled BSDF"]
    bsdf.inputs["Base Color"].default_value = color
    bsdf.inputs["Roughness"].default_value = roughness
    bsdf.inputs["Metallic"].default_value = 0.0
    # Slight subsurface for that plasticky look
    bsdf.inputs["Subsurface Weight"].default_value = 0.05
    bsdf.inputs["Subsurface Radius"].default_value = (color[0], color[1], color[2])
    return mat


def mat_transparent(name, color, alpha=0.3):
    """Transparent/glassy wall material."""
    mat = bpy.data.materials.new(name=name)
    mat.use_nodes = True
    mat.blend_method = 'BLEND' if hasattr(mat, 'blend_method') else None
    nodes = mat.node_tree.nodes
    links = mat.node_tree.links

    # Clear default
    for n in nodes:
        nodes.remove(n)

    output = nodes.new('ShaderNodeOutputMaterial')
    output.location = (400, 0)

    glass = nodes.new('ShaderNodeBsdfGlass')
    glass.location = (0, 100)
    glass.inputs["Color"].default_value = color
    glass.inputs["Roughness"].default_value = 0.05
    glass.inputs["IOR"].default_value = 1.45

    transparent = nodes.new('ShaderNodeBsdfTransparent')
    transparent.location = (0, -100)
    transparent.inputs["Color"].default_value = color

    mix = nodes.new('ShaderNodeMixShader')
    mix.location = (200, 0)
    mix.inputs["Fac"].default_value = alpha

    links.new(transparent.outputs["BSDF"], mix.inputs[1])
    links.new(glass.outputs["BSDF"], mix.inputs[2])
    links.new(mix.outputs["Shader"], output.inputs["Surface"])

    return mat


def mat_sparkle(name, color):
    """Sparkly gem/crystal material with emission."""
    mat = bpy.data.materials.new(name=name)
    mat.use_nodes = True
    nodes = mat.node_tree.nodes
    links = mat.node_tree.links

    for n in nodes:
        nodes.remove(n)

    output = nodes.new('ShaderNodeOutputMaterial')
    output.location = (600, 0)

    # Glass base
    glass = nodes.new('ShaderNodeBsdfGlass')
    glass.location = (0, 150)
    glass.inputs["Color"].default_value = color
    glass.inputs["Roughness"].default_value = 0.0
    glass.inputs["IOR"].default_value = 2.4  # Diamond-like

    # Emission for sparkle
    emission = nodes.new('ShaderNodeEmission')
    emission.location = (0, -50)
    emission.inputs["Color"].default_value = color
    emission.inputs["Strength"].default_value = 3.0

    # Fresnel to drive emission at glancing angles
    fresnel = nodes.new('ShaderNodeFresnel')
    fresnel.location = (-200, 0)
    fresnel.inputs["IOR"].default_value = 2.4

    mix = nodes.new('ShaderNodeMixShader')
    mix.location = (300, 0)

    links.new(fresnel.outputs["Fac"], mix.inputs["Fac"])
    links.new(glass.outputs["BSDF"], mix.inputs[1])
    links.new(emission.outputs["Emission"], mix.inputs[2])
    links.new(mix.outputs["Shader"], output.inputs["Surface"])

    return mat


# ─── Duplo brick builder ───

# Duplo proportions: 1 unit = 1 stud width (31.8mm real)
STUD_R = 0.35       # stud radius relative to brick unit
STUD_H = 0.15       # stud height
BRICK_H = 0.75      # standard brick height (1 unit)


def add_obj(prim_fn, name, location, scale, material, **kwargs):
    prim_fn(**kwargs)
    obj = bpy.context.active_object
    obj.name = name
    obj.location = location
    obj.scale = scale
    if material:
        obj.data.materials.append(material)
    return obj


def duplo_brick(name, pos, size=(2, 2, 1), material=None):
    """
    Create a Duplo-style brick at pos with given stud dimensions.
    size = (width_studs, depth_studs, height_units)
    """
    x, y, z = pos
    w, d, h = size
    bh = h * BRICK_H

    # Main brick body
    body = add_obj(
        bpy.ops.mesh.primitive_cube_add, f"{name}_body",
        location=(x + w/2 - 0.5, y + d/2 - 0.5, z + bh/2),
        scale=(w/2 - 0.02, d/2 - 0.02, bh/2),
        material=material
    )

    # Add studs on top
    for sx in range(w):
        for sy in range(d):
            stud = add_obj(
                bpy.ops.mesh.primitive_cylinder_add, f"{name}_stud_{sx}_{sy}",
                location=(x + sx, y + sy, z + bh + STUD_H/2),
                scale=(STUD_R, STUD_R, STUD_H/2),
                material=material,
                radius=1, depth=1, vertices=16
            )


def duplo_wall_transparent(name, pos, size=(4, 1, 3), material=None):
    """Transparent wall panel (no studs, smooth)."""
    x, y, z = pos
    w, d, h = size
    bh = h * BRICK_H

    add_obj(
        bpy.ops.mesh.primitive_cube_add, f"{name}_panel",
        location=(x + w/2 - 0.5, y + d/2 - 0.5, z + bh/2),
        scale=(w/2 - 0.02, 0.08, bh/2 - 0.02),
        material=material
    )


def duplo_tower(name, pos, radius=1.5, height=5, material=None):
    """Cylindrical tower."""
    x, y, z = pos
    bh = height * BRICK_H

    # Tower body
    add_obj(
        bpy.ops.mesh.primitive_cylinder_add, f"{name}_body",
        location=(x, y, z + bh/2),
        scale=(radius, radius, bh/2),
        material=material,
        radius=1, depth=1, vertices=24
    )

    # Battlements on top
    for i in range(8):
        angle = (2 * math.pi / 8) * i
        bx = x + (radius - 0.15) * math.cos(angle)
        by = y + (radius - 0.15) * math.sin(angle)
        add_obj(
            bpy.ops.mesh.primitive_cube_add, f"{name}_battlement_{i}",
            location=(bx, by, z + bh + BRICK_H * 0.4),
            scale=(0.25, 0.25, BRICK_H * 0.4),
            material=material
        )

    # Cone roof
    add_obj(
        bpy.ops.mesh.primitive_cone_add, f"{name}_roof",
        location=(x, y, z + bh + BRICK_H * 1.2),
        scale=(radius * 1.1, radius * 1.1, BRICK_H * 1.5),
        material=None,
        radius1=1, radius2=0, depth=1, vertices=24
    )
    return bpy.context.active_object


def sparkle_gem(name, pos, scale=0.15, material=None):
    """A sparkly gem (icosphere)."""
    add_obj(
        bpy.ops.mesh.primitive_ico_sphere_add, f"{name}",
        location=pos,
        scale=(scale, scale, scale),
        material=material,
        radius=1, subdivisions=2
    )


# ─── Build the castle ───

def create_castle():
    random.seed(42)

    # Materials
    red = mat_solid("DuploRed", (0.85, 0.12, 0.1, 1.0))
    blue = mat_solid("DuploBlue", (0.15, 0.35, 0.85, 1.0))
    yellow = mat_solid("DuploYellow", (1.0, 0.85, 0.1, 1.0))
    green = mat_solid("DuploGreen", (0.2, 0.7, 0.2, 1.0))
    white = mat_solid("DuploWhite", (0.95, 0.95, 0.95, 1.0))
    gray = mat_solid("DuploGray", (0.5, 0.5, 0.52, 1.0))

    # Transparent wall materials
    trans_pink = mat_transparent("TransPink", (1.0, 0.4, 0.7, 1.0), alpha=0.4)
    trans_blue = mat_transparent("TransBlue", (0.3, 0.6, 1.0, 1.0), alpha=0.35)
    trans_purple = mat_transparent("TransPurple", (0.7, 0.3, 1.0, 1.0), alpha=0.4)
    trans_green = mat_transparent("TransGreen", (0.3, 1.0, 0.5, 1.0), alpha=0.35)

    # Sparkle materials
    sparkle_pink = mat_sparkle("SparklePink", (1.0, 0.3, 0.6, 1.0))
    sparkle_gold = mat_sparkle("SparkleGold", (1.0, 0.85, 0.2, 1.0))
    sparkle_blue = mat_sparkle("SparkleBlue", (0.3, 0.5, 1.0, 1.0))
    sparkle_white = mat_sparkle("SparkleWhite", (1.0, 1.0, 1.0, 1.0))

    roof_red = mat_solid("RoofRed", (0.75, 0.08, 0.08, 1.0), roughness=0.6)
    roof_blue = mat_solid("RoofBlue", (0.1, 0.25, 0.75, 1.0), roughness=0.6)

    # ── Base platform ──
    duplo_brick("base", (-6, -6, 0), size=(12, 12, 1), material=green)

    # ── Front wall (left section) ──
    duplo_brick("fwall_L1", (-5, -5, BRICK_H), size=(4, 2, 1), material=red)
    duplo_brick("fwall_L2", (-5, -5, BRICK_H*2), size=(4, 2, 1), material=yellow)
    duplo_brick("fwall_L3", (-5, -5, BRICK_H*3), size=(4, 2, 1), material=red)

    # ── Front wall (right section) ──
    duplo_brick("fwall_R1", (1, -5, BRICK_H), size=(4, 2, 1), material=red)
    duplo_brick("fwall_R2", (1, -5, BRICK_H*2), size=(4, 2, 1), material=yellow)
    duplo_brick("fwall_R3", (1, -5, BRICK_H*3), size=(4, 2, 1), material=red)

    # ── Gate arch (center) ──
    duplo_brick("gate_top", (-1, -5, BRICK_H*3), size=(2, 2, 1), material=yellow)

    # ── Back wall with transparent panels ──
    duplo_brick("bwall_1", (-5, 3, BRICK_H), size=(10, 2, 1), material=blue)
    duplo_wall_transparent("bwall_trans", (-5, 3.5, BRICK_H*2), size=(10, 1, 2), material=trans_blue)
    duplo_brick("bwall_top", (-5, 3, BRICK_H*4), size=(10, 2, 1), material=blue)

    # ── Left wall with transparent panels ──
    duplo_brick("lwall_1", (-5, -3, BRICK_H), size=(2, 6, 1), material=red)
    duplo_wall_transparent("lwall_trans", (-5, -3, BRICK_H*2), size=(2, 6, 2), material=trans_pink)
    duplo_brick("lwall_top", (-5, -3, BRICK_H*4), size=(2, 6, 1), material=red)

    # ── Right wall with transparent panels ──
    duplo_brick("rwall_1", (3, -3, BRICK_H), size=(2, 6, 1), material=blue)
    duplo_wall_transparent("rwall_trans", (3, -3, BRICK_H*2), size=(2, 6, 2), material=trans_purple)
    duplo_brick("rwall_top", (3, -3, BRICK_H*4), size=(2, 6, 1), material=blue)

    # ── Corner towers ──
    tower_positions = [(-5, -5), (4, -5), (-5, 4), (4, 4)]
    tower_mats = [red, blue, yellow, red]
    roof_mats = [roof_blue, roof_red, roof_red, roof_blue]

    for i, ((tx, ty), tmat, rmat) in enumerate(zip(tower_positions, tower_mats, roof_mats)):
        roof_obj = duplo_tower(f"tower_{i}", (tx, ty, BRICK_H), radius=1.2, height=5, material=tmat)
        roof_obj.data.materials.append(rmat)
        roof_obj.data.materials[0] = rmat

    # ── Interior details ──
    # A little table
    duplo_brick("table", (-2, 0, BRICK_H), size=(2, 2, 1), material=white)
    duplo_brick("table_top", (-2, 0, BRICK_H*2), size=(3, 3, 1), material=yellow)

    # ── Sparkly gems scattered around ──
    sparkle_mats = [sparkle_pink, sparkle_gold, sparkle_blue, sparkle_white]
    gem_positions = [
        # On tower tops
        (-5, -5, BRICK_H * 7.5),
        (4, -5, BRICK_H * 7.5),
        (-5, 4, BRICK_H * 7.5),
        (4, 4, BRICK_H * 7.5),
        # On gate
        (-0.0, -5, BRICK_H * 4.2),
        # Along walls
        (-3, -5, BRICK_H * 4.5),
        (2, -5, BRICK_H * 4.5),
        # On table
        (-1, 0.5, BRICK_H * 3.5),
        (-0.5, 0, BRICK_H * 3.5),
        # Scattered on ground
        (1, 1, BRICK_H + 0.2),
        (-3, 2, BRICK_H + 0.2),
        (2, -2, BRICK_H + 0.2),
        # Floating sparkles near transparent walls
        (-4.5, 0, BRICK_H * 3),
        (3.5, 0, BRICK_H * 3),
        (0, 3.5, BRICK_H * 3),
    ]

    for i, pos in enumerate(gem_positions):
        smat = sparkle_mats[i % len(sparkle_mats)]
        size = random.uniform(0.12, 0.25)
        sparkle_gem(f"gem_{i}", pos, scale=size, material=smat)

    # Extra floating sparkle particles (tiny emissive spheres)
    for i in range(30):
        px = random.uniform(-4.5, 4.5)
        py = random.uniform(-4.5, 4.5)
        pz = random.uniform(BRICK_H * 1.5, BRICK_H * 6)
        smat = sparkle_mats[i % len(sparkle_mats)]
        size = random.uniform(0.04, 0.08)
        sparkle_gem(f"particle_{i}", (px, py, pz), scale=size, material=smat)


# ─── Environment ───

def setup_lighting():
    # Warm key light (sunshine)
    bpy.ops.object.light_add(type='SUN', location=(5, -5, 10))
    sun = bpy.context.active_object
    sun.name = "Sun"
    sun.data.energy = 4
    sun.data.color = (1.0, 0.95, 0.85)
    sun.rotation_euler = (math.radians(40), math.radians(15), math.radians(-30))

    # Soft fill from the other side
    bpy.ops.object.light_add(type='AREA', location=(-6, 4, 6))
    fill = bpy.context.active_object
    fill.name = "Fill"
    fill.data.energy = 150
    fill.data.size = 5
    fill.data.color = (0.85, 0.9, 1.0)

    # Warm bounce from below/front
    bpy.ops.object.light_add(type='AREA', location=(0, -8, 2))
    bounce = bpy.context.active_object
    bounce.name = "Bounce"
    bounce.data.energy = 80
    bounce.data.size = 8
    bounce.data.color = (1.0, 0.95, 0.9)

    # Rim light behind
    bpy.ops.object.light_add(type='AREA', location=(0, 8, 5))
    rim = bpy.context.active_object
    rim.name = "Rim"
    rim.data.energy = 120
    rim.data.size = 4


def setup_camera():
    bpy.ops.object.camera_add(location=(12, -10, 8))
    cam = bpy.context.active_object
    cam.name = "Camera"
    cam.data.lens = 32

    bpy.ops.object.empty_add(location=(0, 0, 2))
    target = bpy.context.active_object
    target.name = "CamTarget"

    constraint = cam.constraints.new(type='TRACK_TO')
    constraint.target = target
    constraint.track_axis = 'TRACK_NEGATIVE_Z'
    constraint.up_axis = 'UP_Y'

    bpy.context.scene.camera = cam


def setup_world():
    world = bpy.context.scene.world
    if world is None:
        world = bpy.data.worlds.new("World")
        bpy.context.scene.world = world
    world.use_nodes = True
    nodes = world.node_tree.nodes
    links = world.node_tree.links
    for n in nodes:
        nodes.remove(n)

    # Gradient sky
    bg = nodes.new('ShaderNodeBackground')
    bg.location = (200, 0)

    gradient = nodes.new('ShaderNodeTexGradient')
    gradient.location = (-200, 0)

    mapping = nodes.new('ShaderNodeMapping')
    mapping.location = (-400, 0)
    mapping.inputs["Rotation"].default_value = (math.radians(90), 0, 0)

    texcoord = nodes.new('ShaderNodeTexCoord')
    texcoord.location = (-600, 0)

    colorramp = nodes.new('ShaderNodeValToRGB')
    colorramp.location = (0, 0)
    colorramp.color_ramp.elements[0].color = (0.4, 0.6, 1.0, 1.0)   # sky blue
    colorramp.color_ramp.elements[1].color = (0.85, 0.92, 1.0, 1.0)  # light horizon

    output = nodes.new('ShaderNodeOutputWorld')
    output.location = (400, 0)

    links.new(texcoord.outputs["Generated"], mapping.inputs["Vector"])
    links.new(mapping.outputs["Vector"], gradient.inputs["Vector"])
    links.new(gradient.outputs["Color"], colorramp.inputs["Fac"])
    links.new(colorramp.outputs["Color"], bg.inputs["Color"])
    bg.inputs["Strength"].default_value = 1.5
    links.new(bg.outputs["Background"], output.inputs["Surface"])


def configure_render(output_path):
    scene = bpy.context.scene
    scene.render.engine = 'CYCLES'
    scene.cycles.device = 'CPU'
    scene.cycles.samples = 200
    scene.cycles.use_denoising = False
    # Transparency bounces for glass/transparent materials
    scene.cycles.max_bounces = 12
    scene.cycles.glossy_bounces = 8
    scene.cycles.transmission_bounces = 12
    scene.cycles.transparent_max_bounces = 16

    scene.render.resolution_x = 1920
    scene.render.resolution_y = 1080
    scene.render.resolution_percentage = 100
    scene.render.image_settings.file_format = 'PNG'
    scene.render.image_settings.color_mode = 'RGBA'
    scene.render.filepath = os.path.abspath(output_path)


def main():
    output_path = parse_args()
    os.makedirs(os.path.dirname(os.path.abspath(output_path)), exist_ok=True)

    print("=== Bootstrap 3D - Duplo Castle ===")
    clear_scene()
    create_castle()
    setup_lighting()
    setup_camera()
    setup_world()
    configure_render(output_path)

    # Save .blend
    blend_path = output_path.replace('.png', '.blend')
    bpy.ops.wm.save_as_mainfile(filepath=os.path.abspath(blend_path))
    print(f"Scene saved: {blend_path}")

    print("Rendering (this may take a few minutes)...")
    bpy.ops.render.render(write_still=True)
    print(f"Render complete: {output_path}")


if __name__ == "__main__":
    main()
