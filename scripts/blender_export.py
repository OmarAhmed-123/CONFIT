"""
Blender Export Script for glTF Models
=====================================
Automates export of 3D garments to glTF with Draco compression.

Usage in Blender:
    1. Open Blender with your garment model
    2. Run: bpy.ops.script.python_file_run(filepath="blender_export.py")
    
Or via command line:
    blender -b garment.blend --python blender_export.py
"""

import bpy
import sys
import os
from pathlib import Path

# ===========================================
# Configuration
# ===========================================

CONFIG = {
    # Output settings
    'output_dir': './output',
    'format': 'GLB',  # GLB or GLTF_SEPARATE
    
    # Mesh settings
    'apply_modifiers': True,
    'triangulate': True,
    
    # Compression
    'draco_compression': True,
    'draco_compression_level': 6,  # 0-10
    
    # Transform
    'y_up': True,
    'scale': 1.0,
    
    # Materials
    'export_materials': 'EXPORT',
    'export_textures': True,
    
    # Animation
    'export_animations': False,
}

# ===========================================
# Export Functions
# ===========================================

def prepare_model():
    """Prepare model for export."""
    # Select all mesh objects
    bpy.ops.object.select_all(action='DESELECT')
    
    for obj in bpy.data.objects:
        if obj.type == 'MESH':
            obj.select_set(True)
            bpy.context.view_layer.objects.active = obj
            
            # Apply modifiers
            if CONFIG['apply_modifiers']:
                for modifier in obj.modifiers:
                    if modifier.type in ['SUBSURF', 'MIRROR', 'SOLIDIFY', 'BEVEL']:
                        # Apply specific modifiers
                        bpy.ops.object.modifier_apply(modifier=modifier.name)
    
    # Triangulate if needed
    if CONFIG['triangulate']:
        for obj in bpy.context.selected_objects:
            if obj.type == 'MESH':
                bpy.context.view_layer.objects.active = obj
                bpy.ops.object.mode_set(mode='EDIT')
                bpy.ops.mesh.select_all(action='SELECT')
                bpy.ops.mesh.quads_convert_to_tris()
                bpy.ops.object.mode_set(mode='OBJECT')
    
    # Apply transforms
    bpy.ops.object.transform_apply(location=True, rotation=True, scale=True)
    
    # Center model
    if len(bpy.context.selected_objects) > 0:
        # Calculate center
        center_x = sum(obj.location.x for obj in bpy.context.selected_objects) / len(bpy.context.selected_objects)
        center_y = sum(obj.location.y for obj in bpy.context.selected_objects) / len(bpy.context.selected_objects)
        
        # Move to center
        for obj in bpy.context.selected_objects:
            obj.location.x -= center_x
            obj.location.y -= center_y


def export_gltf(output_path: str):
    """Export to glTF format."""
    # Ensure output directory exists
    os.makedirs(os.path.dirname(output_path), exist_ok=True)
    
    # Export settings
    export_settings = {
        'filepath': output_path,
        'check_existing': False,
        'export_format': CONFIG['format'],
        'export_apply': CONFIG['apply_modifiers'],
        'export_yup': CONFIG['y_up'],
        'export_materials': CONFIG['export_materials'],
        'export_textures': CONFIG['export_textures'],
        'export_animations': CONFIG['export_animations'],
        'export_extras': True,
        'export_cameras': False,
        'export_lights': False,
    }
    
    # Draco compression (requires glTF-Blender-IO-Draco addon)
    if CONFIG['draco_compression']:
        try:
            export_settings['export_draco_mesh_compression_enable'] = True
            export_settings['export_draco_mesh_compression_level'] = CONFIG['draco_compression_level']
        except TypeError:
            print("Warning: Draco compression not available. Install glTF-Blender-IO-Draco addon.")
    
    # Export
    bpy.ops.export_scene.gltf(**export_settings)
    print(f"Exported: {output_path}")


def generate_lod_variants(base_path: str):
    """Generate LOD variants using decimation."""
    import bmesh
    
    base_name = Path(base_path).stem
    output_dir = Path(base_path).parent
    
    lod_levels = [
        ('lod0', 1.0),    # Full quality
        ('lod1', 0.5),    # 50%
        ('lod2', 0.2),    # 20%
    ]
    
    for lod_name, decimate_ratio in lod_levels:
        if decimate_ratio == 1.0:
            # Already exported as base
            continue
        
        # Apply decimation modifier
        for obj in bpy.context.selected_objects:
            if obj.type == 'MESH':
                # Add decimation modifier
                decimate = obj.modifiers.new(name="Decimate", type='DECIMATE')
                decimate.ratio = decimate_ratio
                
                # Apply modifier
                bpy.context.view_layer.objects.active = obj
                bpy.ops.object.modifier_apply(modifier=decimate.name)
        
        # Export LOD variant
        lod_path = str(output_dir / f"{base_name}-{lod_name}.glb")
        export_gltf(lod_path)
        
        # Undo decimation for next iteration
        bpy.ops.ed.undo()


def batch_export(input_dir: str, output_dir: str):
    """Batch export all .blend files in directory."""
    input_path = Path(input_dir)
    output_path = Path(output_dir)
    
    for blend_file in input_path.glob('**/*.blend'):
        print(f"\nProcessing: {blend_file}")
        
        # Open file
        bpy.ops.wm.open_mainfile(filepath=str(blend_file))
        
        # Prepare and export
        prepare_model()
        
        output_name = blend_file.stem + '.glb'
        export_gltf(str(output_path / output_name))


# ===========================================
# Main Execution
# ===========================================

def main():
    """Main export function."""
    import argparse
    
    parser = argparse.ArgumentParser(description='Export Blender models to glTF')
    parser.add_argument('--output', '-o', type=str, default='./output/model.glb',
                        help='Output path for glTF file')
    parser.add_argument('--lod', action='store_true',
                        help='Generate LOD variants')
    parser.add_argument('--batch', type=str, default=None,
                        help='Batch process directory')
    
    args = parser.parse_args(sys.argv[sys.argv.index('--') + 1:] if '--' in sys.argv else [])
    
    if args.batch:
        batch_export(args.batch, args.output)
    else:
        prepare_model()
        export_gltf(args.output)
        
        if args.lod:
            generate_lod_variants(args.output)
    
    print("\nExport complete!")


# Run if executed directly
if __name__ == "__main__":
    main()
