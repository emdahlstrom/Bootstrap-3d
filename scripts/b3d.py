"""
b3d - Bootstrap 3D rendering utilities

A lightweight headless Blender rendering library inspired by blenderless.
Defines scenes declaratively in Python, renders via Blender in a subprocess
with a virtual framebuffer (xvfb).

Usage from Python:
    from b3d import Scene, Mesh, Camera, Light, Material

    scene = Scene(samples=64, resolution=(1920, 1080))
    scene.add(Mesh.cube(location=(0, 0, 0), material=Material(color=(0.2, 0.5, 0.8))))
    scene.add(Camera(location=(5, -5, 3), target=(0, 0, 0)))
    scene.add(Light.area(location=(3, -3, 5), energy=200))
    scene.render("output.png")

Usage as CLI:
    python3 b3d.py render scene_script.py --output output.png

The scene_script.py should define a `build_scene()` function that returns a Scene.
"""

import json
import os
import subprocess
import sys
import tempfile
import math
from dataclasses import dataclass, field, asdict
from typing import Optional


# ─── Data classes (define scene without touching bpy) ───

@dataclass
class Material:
    name: str = "Default"
    color: tuple = (0.8, 0.8, 0.8, 1.0)
    metallic: float = 0.0
    roughness: float = 0.5
    emission_color: Optional[tuple] = None
    emission_strength: float = 0.0

    def to_dict(self):
        d = asdict(self)
        return d


@dataclass
class Mesh:
    primitive: str = "cube"  # cube, sphere, cylinder, plane, cone, torus
    name: str = "Object"
    location: tuple = (0, 0, 0)
    rotation: tuple = (0, 0, 0)
    scale: tuple = (1, 1, 1)
    material: Optional[Material] = None
    # For loading external meshes
    file_path: Optional[str] = None
    # Primitive-specific params
    segments: int = 32
    ring_count: int = 16
    depth: float = 1.0
    radius: float = 1.0

    @classmethod
    def cube(cls, **kwargs):
        return cls(primitive="cube", **kwargs)

    @classmethod
    def sphere(cls, **kwargs):
        return cls(primitive="sphere", **kwargs)

    @classmethod
    def cylinder(cls, **kwargs):
        return cls(primitive="cylinder", **kwargs)

    @classmethod
    def plane(cls, **kwargs):
        return cls(primitive="plane", **kwargs)

    @classmethod
    def cone(cls, **kwargs):
        return cls(primitive="cone", **kwargs)

    @classmethod
    def from_file(cls, path, **kwargs):
        return cls(primitive="file", file_path=path, **kwargs)

    def to_dict(self):
        d = asdict(self)
        if self.material:
            d['material'] = self.material.to_dict()
        return d


@dataclass
class Camera:
    location: tuple = (5, -5, 3)
    target: tuple = (0, 0, 0)
    lens: float = 50
    name: str = "Camera"

    @classmethod
    def spherical(cls, azimuth=45, elevation=30, distance=5, target=(0, 0, 0), **kwargs):
        """Create camera from spherical coordinates (degrees)."""
        az = math.radians(azimuth)
        el = math.radians(elevation)
        x = distance * math.cos(el) * math.cos(az)
        y = distance * math.cos(el) * math.sin(az)
        z = distance * math.sin(el)
        return cls(location=(x, y, z), target=target, **kwargs)

    def to_dict(self):
        return asdict(self)


@dataclass
class Light:
    light_type: str = "AREA"  # AREA, POINT, SUN, SPOT
    name: str = "Light"
    location: tuple = (3, -3, 5)
    energy: float = 200
    size: float = 2.0
    color: tuple = (1.0, 1.0, 1.0)

    @classmethod
    def area(cls, **kwargs):
        return cls(light_type="AREA", **kwargs)

    @classmethod
    def point(cls, **kwargs):
        return cls(light_type="POINT", **kwargs)

    @classmethod
    def sun(cls, **kwargs):
        return cls(light_type="SUN", **kwargs)

    def to_dict(self):
        return asdict(self)


@dataclass
class World:
    color: tuple = (0.05, 0.05, 0.1, 1.0)
    strength: float = 0.5

    def to_dict(self):
        return asdict(self)


class Scene:
    """Declarative scene builder. Call render() to execute via headless Blender."""

    def __init__(self, samples=64, resolution=(1920, 1080), engine='CYCLES',
                 transparent=False, world=None):
        self.samples = samples
        self.resolution = resolution
        self.engine = engine
        self.transparent = transparent
        self.world = world or World()
        self.objects = []
        self.cameras = []
        self.lights = []

    def add(self, obj):
        if isinstance(obj, Mesh):
            self.objects.append(obj)
        elif isinstance(obj, Camera):
            self.cameras.append(obj)
        elif isinstance(obj, Light):
            self.lights.append(obj)
        return self

    def to_dict(self):
        return {
            'samples': self.samples,
            'resolution': list(self.resolution),
            'engine': self.engine,
            'transparent': self.transparent,
            'world': self.world.to_dict(),
            'objects': [o.to_dict() for o in self.objects],
            'cameras': [c.to_dict() for c in self.cameras],
            'lights': [l.to_dict() for l in self.lights],
        }

    def render(self, output_path, blend_path=None):
        """Render the scene via headless Blender in a subprocess."""
        output_path = os.path.abspath(output_path)
        os.makedirs(os.path.dirname(output_path), exist_ok=True)

        # Write scene definition to temp JSON
        scene_data = self.to_dict()
        scene_data['output_path'] = output_path
        if blend_path:
            scene_data['blend_path'] = os.path.abspath(blend_path)

        with tempfile.NamedTemporaryFile(mode='w', suffix='.json', delete=False) as f:
            json.dump(scene_data, f)
            scene_file = f.name

        # Run the Blender executor
        executor = os.path.join(os.path.dirname(os.path.abspath(__file__)), '_b3d_executor.py')
        cmd = [
            'xvfb-run', '-a',
            'blender', '--background', '--python', executor,
            '--', scene_file
        ]

        print(f"[b3d] Rendering {output_path}...")
        result = subprocess.run(cmd, capture_output=True, text=True, timeout=600)

        # Clean up
        os.unlink(scene_file)

        if result.returncode != 0:
            print(f"[b3d] STDERR:\n{result.stderr[-2000:]}")
            raise RuntimeError(f"Blender render failed (exit {result.returncode})")

        print(f"[b3d] Done: {output_path}")
        return output_path

    def render_turntable(self, output_dir, frames=36, elevation=30, distance=5,
                         target=(0, 0, 0)):
        """Render a turntable sequence (multiple angles around the object)."""
        os.makedirs(output_dir, exist_ok=True)
        paths = []
        for i in range(frames):
            azimuth = (360 / frames) * i
            self.cameras = [Camera.spherical(azimuth=azimuth, elevation=elevation,
                                             distance=distance, target=target)]
            path = os.path.join(output_dir, f"frame_{i:04d}.png")
            self.render(path)
            paths.append(path)
        return paths
