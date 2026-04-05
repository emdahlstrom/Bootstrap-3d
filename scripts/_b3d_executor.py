"""
b3d Blender executor - runs inside Blender's Python environment.
Reads a scene JSON file, builds the scene using bpy, and renders.

This file is NOT meant to be imported directly. It is called by b3d.Scene.render()
via: blender --background --python _b3d_executor.py -- scene.json
"""

import bpy
import json
import sys
import os
import math


def load_scene_data():
    argv = sys.argv
    if "--" not in argv:
        raise RuntimeError("Expected -- <scene.json> in arguments")
    json_path = argv[argv.index("--") + 1]
    with open(json_path) as f:
        return json.load(f)


def clear_scene():
    bpy.ops.object.select_all(action='SELECT')
    bpy.ops.object.delete()
    for block in bpy.data.meshes:
        if block.users == 0:
            bpy.data.meshes.remove(block)
    for block in bpy.data.materials:
        if block.users == 0:
            bpy.data.materials.remove(block)


def create_material(mat_data):
    if mat_data is None:
        return None
    mat = bpy.data.materials.new(name=mat_data.get('name', 'Material'))
    mat.use_nodes = True
    bsdf = mat.node_tree.nodes["Principled BSDF"]
    bsdf.inputs["Base Color"].default_value = mat_data['color']
    bsdf.inputs["Metallic"].default_value = mat_data.get('metallic', 0.0)
    bsdf.inputs["Roughness"].default_value = mat_data.get('roughness', 0.5)
    if mat_data.get('emission_color'):
        bsdf.inputs["Emission Color"].default_value = mat_data['emission_color']
        bsdf.inputs["Emission Strength"].default_value = mat_data.get('emission_strength', 1.0)
    return mat


def create_mesh(obj_data):
    prim = obj_data['primitive']
    loc = tuple(obj_data['location'])
    scale = tuple(obj_data['scale'])
    rot = tuple(obj_data.get('rotation', (0, 0, 0)))

    if prim == 'file' and obj_data.get('file_path'):
        path = obj_data['file_path']
        ext = os.path.splitext(path)[1].lower()
        if ext in ('.glb', '.gltf'):
            bpy.ops.import_scene.gltf(filepath=path)
        elif ext == '.obj':
            bpy.ops.wm.obj_import(filepath=path)
        elif ext in ('.stl',):
            bpy.ops.import_mesh.stl(filepath=path)
        elif ext in ('.fbx',):
            bpy.ops.import_scene.fbx(filepath=path)
        obj = bpy.context.active_object
    elif prim == 'cube':
        bpy.ops.mesh.primitive_cube_add(location=loc)
        obj = bpy.context.active_object
    elif prim == 'sphere':
        bpy.ops.mesh.primitive_uv_sphere_add(
            location=loc,
            segments=obj_data.get('segments', 32),
            ring_count=obj_data.get('ring_count', 16),
        )
        obj = bpy.context.active_object
    elif prim == 'cylinder':
        bpy.ops.mesh.primitive_cylinder_add(
            location=loc,
            depth=obj_data.get('depth', 1.0),
            radius=obj_data.get('radius', 1.0),
        )
        obj = bpy.context.active_object
    elif prim == 'plane':
        bpy.ops.mesh.primitive_plane_add(location=loc)
        obj = bpy.context.active_object
    elif prim == 'cone':
        bpy.ops.mesh.primitive_cone_add(location=loc)
        obj = bpy.context.active_object
    elif prim == 'torus':
        bpy.ops.mesh.primitive_torus_add(location=loc)
        obj = bpy.context.active_object
    else:
        raise ValueError(f"Unknown primitive: {prim}")

    obj.name = obj_data.get('name', 'Object')
    obj.scale = scale
    obj.rotation_euler = rot

    mat = create_material(obj_data.get('material'))
    if mat:
        if obj.data.materials:
            obj.data.materials[0] = mat
        else:
            obj.data.materials.append(mat)

    return obj


def create_camera(cam_data):
    loc = tuple(cam_data['location'])
    bpy.ops.object.camera_add(location=loc)
    cam = bpy.context.active_object
    cam.name = cam_data.get('name', 'Camera')
    cam.data.lens = cam_data.get('lens', 50)

    target = cam_data.get('target')
    if target:
        bpy.ops.object.empty_add(location=tuple(target))
        target_obj = bpy.context.active_object
        target_obj.name = f"{cam.name}_Target"
        constraint = cam.constraints.new(type='TRACK_TO')
        constraint.target = target_obj
        constraint.track_axis = 'TRACK_NEGATIVE_Z'
        constraint.up_axis = 'UP_Y'

    bpy.context.scene.camera = cam
    return cam


def create_light(light_data):
    light_type = light_data.get('light_type', 'AREA')
    loc = tuple(light_data['location'])
    bpy.ops.object.light_add(type=light_type, location=loc)
    light = bpy.context.active_object
    light.name = light_data.get('name', 'Light')
    light.data.energy = light_data.get('energy', 200)
    light.data.color = tuple(light_data.get('color', (1, 1, 1)))
    if hasattr(light.data, 'size'):
        light.data.size = light_data.get('size', 2.0)
    return light


def setup_world(world_data):
    world = bpy.context.scene.world
    if world is None:
        world = bpy.data.worlds.new("World")
        bpy.context.scene.world = world
    world.use_nodes = True
    nodes = world.node_tree.nodes
    links = world.node_tree.links
    for node in nodes:
        nodes.remove(node)
    bg = nodes.new('ShaderNodeBackground')
    bg.inputs['Color'].default_value = tuple(world_data.get('color', (0.05, 0.05, 0.1, 1.0)))
    bg.inputs['Strength'].default_value = world_data.get('strength', 0.5)
    output = nodes.new('ShaderNodeOutputWorld')
    links.new(bg.outputs['Background'], output.inputs['Surface'])


def configure_render(scene_data):
    scene = bpy.context.scene
    engine = scene_data.get('engine', 'CYCLES')
    scene.render.engine = engine

    if engine == 'CYCLES':
        scene.cycles.device = 'CPU'
        scene.cycles.samples = scene_data.get('samples', 64)
        scene.cycles.use_denoising = False

    res = scene_data.get('resolution', [1920, 1080])
    scene.render.resolution_x = res[0]
    scene.render.resolution_y = res[1]
    scene.render.resolution_percentage = 100
    scene.render.image_settings.file_format = 'PNG'
    scene.render.image_settings.color_mode = 'RGBA' if scene_data.get('transparent') else 'RGB'
    scene.render.film_transparent = scene_data.get('transparent', False)
    scene.render.filepath = scene_data['output_path']


def main():
    data = load_scene_data()
    clear_scene()

    for obj_data in data.get('objects', []):
        create_mesh(obj_data)

    for light_data in data.get('lights', []):
        create_light(light_data)

    for cam_data in data.get('cameras', []):
        create_camera(cam_data)

    setup_world(data.get('world', {}))
    configure_render(data)

    if data.get('blend_path'):
        bpy.ops.wm.save_as_mainfile(filepath=data['blend_path'])
        print(f"[b3d] Scene saved: {data['blend_path']}")

    print("[b3d] Rendering...")
    bpy.ops.render.render(write_still=True)
    print(f"[b3d] Render saved: {data['output_path']}")


if __name__ == "__main__":
    main()
