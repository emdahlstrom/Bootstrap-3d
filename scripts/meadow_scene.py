"""
Bootstrap 3D - Meadow Scene
A peaceful outdoor scene with deer grazing in a meadow, surrounded by
trees, rocks, flowers, and grass. Uses Quaternius CC0 low-poly assets.

Usage:
    xvfb-run -a blender --background --python scripts/meadow_scene.py -- --output renders/meadow.png
"""

import bpy
import sys
import os
import math
import random


def parse_args():
    argv = sys.argv
    output = "renders/meadow.png"
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


def import_glb(filepath, location=(0, 0, 0), rotation=(0, 0, 0), scale=(1, 1, 1), name=None):
    """Import a GLB file and position it."""
    abs_path = os.path.abspath(filepath)
    if not os.path.exists(abs_path):
        print(f"Warning: {abs_path} not found, skipping")
        return None

    # Track existing objects
    before = set(bpy.data.objects)
    bpy.ops.import_scene.gltf(filepath=abs_path)
    after = set(bpy.data.objects)
    new_objects = after - before

    if not new_objects:
        return None

    # Create an empty parent for all imported objects
    bpy.ops.object.empty_add(location=location)
    parent = bpy.context.active_object
    if name:
        parent.name = name
    parent.rotation_euler = rotation
    parent.scale = scale

    for obj in new_objects:
        if obj.parent is None or obj.parent not in new_objects:
            obj.parent = parent

    return parent


def create_ground():
    """Create a large green meadow ground plane."""
    mat = bpy.data.materials.new(name="MeadowGround")
    mat.use_nodes = True
    bsdf = mat.node_tree.nodes["Principled BSDF"]
    bsdf.inputs["Base Color"].default_value = (0.25, 0.55, 0.15, 1.0)
    bsdf.inputs["Roughness"].default_value = 0.9
    bsdf.inputs["Metallic"].default_value = 0.0
    bsdf.inputs["Specular IOR Level"].default_value = 0.1

    bpy.ops.mesh.primitive_plane_add(size=60, location=(0, 0, 0))
    ground = bpy.context.active_object
    ground.name = "MeadowGround"
    ground.data.materials.append(mat)

    # Add a slight hill with a displace modifier on a subdivided plane
    bpy.ops.mesh.primitive_plane_add(size=80, location=(0, 0, -0.05))
    hills = bpy.context.active_object
    hills.name = "HillsBase"

    # Subdivide for gentle terrain
    bpy.context.view_layer.objects.active = hills
    bpy.ops.object.mode_set(mode='EDIT')
    for _ in range(4):
        bpy.ops.mesh.subdivide()
    bpy.ops.object.mode_set(mode='OBJECT')

    # Add texture for hills
    tex = bpy.data.textures.new("HillTex", type='CLOUDS')
    tex.noise_scale = 8.0

    mod = hills.modifiers.new("Displace", 'DISPLACE')
    mod.texture = tex
    mod.strength = 1.5
    mod.mid_level = 0.5

    hills.data.materials.append(mat)

    return ground


def scatter_asset(filepath, count, area_min, area_max, scale_range=(1, 1),
                  rotation_range=(0, 2 * math.pi), name_prefix="Asset", z_offset=0):
    """Scatter copies of a GLB asset randomly across an area."""
    objects = []
    for i in range(count):
        x = random.uniform(area_min[0], area_max[0])
        y = random.uniform(area_min[1], area_max[1])
        s = random.uniform(scale_range[0], scale_range[1])
        r = random.uniform(rotation_range[0], rotation_range[1])

        obj = import_glb(
            filepath,
            location=(x, y, z_offset),
            rotation=(0, 0, r),
            scale=(s, s, s),
            name=f"{name_prefix}_{i}"
        )
        if obj:
            objects.append(obj)
    return objects


def create_meadow():
    """Build the full meadow scene."""
    random.seed(12345)

    base = "assets/nature/"
    animal_base = "assets/animals/"

    # ── Animals ──
    # Main deer in foreground, grazing
    import_glb(f"{animal_base}Deer.glb",
               location=(0, 1, 0), rotation=(0, 0, math.radians(-20)),
               scale=(1.2, 1.2, 1.2), name="Deer_Main")

    # Second deer nearby
    import_glb(f"{animal_base}Deer.glb",
               location=(3, 3, 0), rotation=(0, 0, math.radians(45)),
               scale=(1.0, 1.0, 1.0), name="Deer_2")

    # Stag in the background
    import_glb(f"{animal_base}Stag.glb",
               location=(-5, 8, 0), rotation=(0, 0, math.radians(160)),
               scale=(1.3, 1.3, 1.3), name="Stag")

    # Fox sneaking in the distance
    import_glb(f"{animal_base}Fox.glb",
               location=(8, -4, 0), rotation=(0, 0, math.radians(-90)),
               scale=(0.8, 0.8, 0.8), name="Fox")

    # ── Trees ── (scattered around edges)
    # Common trees (background ring)
    scatter_asset(f"{base}CommonTree_1.glb", 4, (-18, -18), (-8, 18),
                  scale_range=(1.5, 2.5), name_prefix="CommonTree1")
    scatter_asset(f"{base}CommonTree_2.glb", 3, (8, -18), (18, 18),
                  scale_range=(1.5, 2.5), name_prefix="CommonTree2")
    scatter_asset(f"{base}CommonTree_3.glb", 3, (-18, 10), (18, 18),
                  scale_range=(1.5, 2.2), name_prefix="CommonTree3")

    # Pine trees
    scatter_asset(f"{base}PineTree_1.glb", 4, (-20, -15), (20, 20),
                  scale_range=(1.8, 3.0), name_prefix="Pine")

    # Birch tree cluster
    scatter_asset(f"{base}BirchTree_1.glb", 3, (-12, -5), (-6, 5),
                  scale_range=(1.5, 2.2), name_prefix="Birch")

    # ── Grass patches ── (lots of them in the meadow)
    scatter_asset(f"{base}Grass.glb", 30, (-12, -12), (12, 12),
                  scale_range=(0.8, 1.5), name_prefix="Grass1")
    scatter_asset(f"{base}Grass_2.glb", 25, (-12, -12), (12, 12),
                  scale_range=(0.8, 1.5), name_prefix="Grass2")

    # ── Flowers ──
    scatter_asset(f"{base}Flowers.glb", 15, (-8, -8), (8, 8),
                  scale_range=(0.6, 1.2), name_prefix="Flowers")

    # ── Bushes ──
    scatter_asset(f"{base}Bush_1.glb", 6, (-15, -15), (15, 15),
                  scale_range=(1.0, 1.8), name_prefix="Bush1")
    scatter_asset(f"{base}Bush_2.glb", 5, (-15, -15), (15, 15),
                  scale_range=(1.0, 1.5), name_prefix="Bush2")

    # ── Rocks ──
    scatter_asset(f"{base}Rock_1.glb", 5, (-15, -15), (15, 15),
                  scale_range=(1.0, 2.5), name_prefix="Rock1")
    scatter_asset(f"{base}Rock_2.glb", 4, (-15, -15), (15, 15),
                  scale_range=(1.0, 2.0), name_prefix="Rock2")
    scatter_asset(f"{base}Rock_Moss_1.glb", 4, (-10, -10), (10, 10),
                  scale_range=(1.2, 2.5), name_prefix="MossRock")

    # ── Wood log near foreground ──
    import_glb(f"{base}WoodLog.glb",
               location=(5, -2, 0), rotation=(0, 0, math.radians(30)),
               scale=(1.5, 1.5, 1.5), name="WoodLog")


def setup_lighting():
    """Golden hour lighting for the meadow."""
    # Warm sun
    bpy.ops.object.light_add(type='SUN', location=(10, -10, 15))
    sun = bpy.context.active_object
    sun.name = "Sun"
    sun.data.energy = 3.0
    sun.data.color = (1.0, 0.9, 0.7)
    sun.rotation_euler = (math.radians(45), math.radians(10), math.radians(-30))

    # Sky fill
    bpy.ops.object.light_add(type='SUN', location=(-5, 5, 10))
    sky = bpy.context.active_object
    sky.name = "SkyFill"
    sky.data.energy = 0.8
    sky.data.color = (0.7, 0.8, 1.0)
    sky.rotation_euler = (math.radians(70), 0, math.radians(120))

    # Warm bounce from ground
    bpy.ops.object.light_add(type='AREA', location=(0, 0, 0.5))
    bounce = bpy.context.active_object
    bounce.name = "GroundBounce"
    bounce.data.energy = 30
    bounce.data.size = 20
    bounce.data.color = (0.6, 0.8, 0.4)
    bounce.rotation_euler = (math.radians(-90), 0, 0)


def setup_camera():
    """Camera looking at the deer from a scenic angle."""
    bpy.ops.object.camera_add(location=(10, -8, 4))
    cam = bpy.context.active_object
    cam.name = "Camera"
    cam.data.lens = 40

    bpy.ops.object.empty_add(location=(0, 1, 1))
    target = bpy.context.active_object
    target.name = "CamTarget"

    constraint = cam.constraints.new(type='TRACK_TO')
    constraint.target = target
    constraint.track_axis = 'TRACK_NEGATIVE_Z'
    constraint.up_axis = 'UP_Y'

    bpy.context.scene.camera = cam


def setup_world():
    """Blue sky with subtle gradient."""
    world = bpy.context.scene.world
    if world is None:
        world = bpy.data.worlds.new("World")
        bpy.context.scene.world = world
    world.use_nodes = True
    nodes = world.node_tree.nodes
    links = world.node_tree.links
    for n in nodes:
        nodes.remove(n)

    # Sky texture
    sky = nodes.new('ShaderNodeTexSky')
    sky.location = (-200, 0)
    sky.sky_type = 'NISHITA'
    sky.sun_elevation = math.radians(35)
    sky.sun_rotation = math.radians(-30)

    bg = nodes.new('ShaderNodeBackground')
    bg.location = (0, 0)
    bg.inputs['Strength'].default_value = 1.0

    output = nodes.new('ShaderNodeOutputWorld')
    output.location = (200, 0)

    links.new(sky.outputs['Color'], bg.inputs['Color'])
    links.new(bg.outputs['Background'], output.inputs['Surface'])


def configure_render(output_path):
    scene = bpy.context.scene
    scene.render.engine = 'CYCLES'
    scene.cycles.device = 'CPU'
    scene.cycles.samples = 128
    scene.cycles.use_denoising = False
    scene.cycles.max_bounces = 8

    scene.render.resolution_x = 1920
    scene.render.resolution_y = 1080
    scene.render.resolution_percentage = 100
    scene.render.image_settings.file_format = 'PNG'
    scene.render.image_settings.color_mode = 'RGB'
    scene.render.filepath = os.path.abspath(output_path)


def main():
    output_path = parse_args()
    os.makedirs(os.path.dirname(os.path.abspath(output_path)), exist_ok=True)

    print("=== Bootstrap 3D - Meadow Scene ===")
    clear_scene()
    create_ground()
    create_meadow()
    setup_lighting()
    setup_camera()
    setup_world()
    configure_render(output_path)

    # Save blend
    blend_path = output_path.replace('.png', '.blend')
    bpy.ops.wm.save_as_mainfile(filepath=os.path.abspath(blend_path))
    print(f"Scene saved: {blend_path}")

    print("Rendering (this may take several minutes)...")
    bpy.ops.render.render(write_still=True)
    print(f"Render complete: {output_path}")


if __name__ == "__main__":
    main()
