#!/bin/bash
# Render a Blender Python scene script headlessly
# Usage: ./render_scene.sh <script.py> [output_path]

SCRIPT="${1:?Usage: render_scene.sh <script.py> [output_path]}"
OUTPUT="${2:-renders/output.png}"

xvfb-run -a blender --background --python "$SCRIPT" -- --output "$OUTPUT"
