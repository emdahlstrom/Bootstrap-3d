"""
Demo: Using b3d to build and render a scene declaratively.
Run with: python3 scripts/demo_b3d.py
"""

import sys
sys.path.insert(0, 'scripts')

from b3d import Scene, Mesh, Camera, Light, Material, World

# Build scene declaratively - no bpy needed
scene = Scene(samples=64, resolution=(1920, 1080))

# Ground
scene.add(Mesh.plane(
    name="Ground",
    location=(0, 0, 0),
    scale=(5, 5, 1),
    material=Material(name="Ground", color=(0.2, 0.2, 0.22, 1.0), roughness=0.9)
))

# Central sphere
scene.add(Mesh.sphere(
    name="GoldSphere",
    location=(0, 0, 1),
    scale=(1, 1, 1),
    material=Material(name="Gold", color=(1.0, 0.8, 0.2, 1.0), metallic=0.9, roughness=0.2)
))

# Flanking cubes
for i, (x, color) in enumerate([(-2.5, (0.2, 0.5, 0.9, 1.0)), (2.5, (0.9, 0.2, 0.3, 1.0))]):
    scene.add(Mesh.cube(
        name=f"Cube_{i}",
        location=(x, 0, 0.7),
        scale=(0.7, 0.7, 0.7),
        material=Material(name=f"CubeMat_{i}", color=color, metallic=0.5, roughness=0.3)
    ))

# Background cylinders
for i in range(5):
    import math
    angle = (math.pi / 4) * i - math.pi / 2
    x = 4 * math.cos(angle)
    y = 4 * math.sin(angle)
    scene.add(Mesh.cylinder(
        name=f"Pillar_{i}",
        location=(x, y, 1.5),
        scale=(0.3, 0.3, 1.5),
        material=Material(name=f"Pillar_{i}", color=(0.4, 0.4, 0.45, 1.0), metallic=0.7, roughness=0.4)
    ))

# Three-point lighting
scene.add(Light.area(name="Key", location=(4, -4, 6), energy=250, color=(1.0, 0.95, 0.9)))
scene.add(Light.area(name="Fill", location=(-3, -2, 4), energy=100, color=(0.8, 0.85, 1.0)))
scene.add(Light.area(name="Rim", location=(0, 5, 3), energy=150))

# Camera
scene.add(Camera(location=(6, -6, 4), target=(0, 0, 0.8), lens=35))

# Render!
scene.render("renders/demo_b3d.png")
