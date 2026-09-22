#!/usr/bin/env python3
"""
Shared configuration for UKHAB QGIS project.

This file contains shared constants and structure definitions.
Both create_gpkg.py and create_ukhab_project.py import from here.

Usage:
    from config import DRAWING_LAYERS, DRAWING_FIELDS, AUTHOR_DEFAULT
"""

from os import path

# ============================================================================
# File Paths
# ============================================================================

# Change this to build a different schema version
SCHEMA_VERSION = "2.1"
GPKG_PATH = path.join(SCHEMA_VERSION, "ukhab.gpkg")
PROJECT_PATH = path.join(SCHEMA_VERSION, "ukhab_template.qgz")
PRIMARY_CSV = path.join(SCHEMA_VERSION, "primary_codes.csv")
SECONDARY_CSV = path.join(SCHEMA_VERSION, "secondary_codes.csv")

# ============================================================================
# Project Settings
# ============================================================================

CRS = "EPSG:27700"  # British National Grid
# The extent of the project map should default to that of the CRS
EXTENT = (0, 0, 70000, 120000)
AUTHOR_DEFAULT = "@user_full_name"  # QGIS variable (no quotes)

# ============================================================================
# Layer Structure
# ============================================================================

# Drawing layers with their geometry types
# Used by both create_gpkg.py (to create layers) and create_ukhab_project.py (to configure)
# Geometry types use UKHAB naming (Area, Line, Point) for filter expressions
DRAWING_LAYERS = {
    "Baseline_Areas": "Area",
    "Baseline_Lines": "Line",
    "Baseline_Points": "Point",
    "Proposed_Areas": "Area",
    "Proposed_Lines": "Line",
    "Proposed_Points": "Point",
}

# Field definitions for all drawing layers
# Type names are generic - each script maps to its own type system (GDAL vs QGIS)
DRAWING_FIELDS = [
    {"name": "code_l2", "type": "string", "width": 50, "required": True},
    {"name": "code_l3", "type": "string", "width": 50},
    {"name": "code_l4", "type": "string", "width": 50},
    {"name": "code_l5", "type": "string", "width": 50},
    {"name": "secondary_codes", "type": "string_list"},
    {"name": "condition", "type": "string", "width": 20},
    {"name": "author", "type": "string", "width": 100},
    {"name": "created", "type": "datetime"},
    {"name": "updated", "type": "datetime"},
    {"name": "area", "type": "real"},
    {"name": "length", "type": "real"},
]

# ============================================================================
# Field Configuration (Form Widgets)
# ============================================================================

# Field aliases (display names in forms) and ValueRelation configuration
# Note: ValueRelation 'value' must be a field name, NOT an expression
# Virtual field 'display_field' shows "Code - Habitat" format (e.g., "g - Grassland")
FIELD_CONFIG = {
    'code_l2': {
        'alias': 'Habitat L2',
        'valuerelation': {
            'layer': 'Primary_Codes',
            'key': 'code',
            'value': 'display_field',  # Virtual field: "Code - Habitat"
            'filter': '"level" = 2 AND array_contains(string_to_array("geometry", \',\'), {geometry_type})',
        }
    },
    'code_l3': {
        'alias': 'Habitat L3',
        'valuerelation': {
            'layer': 'Primary_Codes',
            'key': 'code',
            'value': 'display_field',
            'filter': '"level" = 3 AND left("code", length(current_value(\'code_l2\'))) = current_value(\'code_l2\') AND array_contains(string_to_array("geometry", \',\'), {geometry_type})',
        }
    },
    'code_l4': {
        'alias': 'Habitat L4',
        'valuerelation': {
            'layer': 'Primary_Codes',
            'key': 'code',
            'value': 'display_field',
            'filter': '"level" = 4 AND left("code", length(current_value(\'code_l3\'))) = current_value(\'code_l3\') AND array_contains(string_to_array("geometry", \',\'), {geometry_type})',
        }
    },
    'code_l5': {
        'alias': 'Habitat L5',
        'valuerelation': {
            'layer': 'Primary_Codes',
            'key': 'code',
            'value': 'display_field',
            'filter': '"level" = 5 AND left("code", length(current_value(\'code_l4\'))) = current_value(\'code_l4\') AND array_contains(string_to_array("geometry", \',\'), {geometry_type})',
        }
    },
    'secondary_codes': {
        'alias': 'Secondary Codes',
        'valuerelation': {
            'layer': 'Secondary_Codes',
            'key': 'code',
            'value': 'display_field',  # Virtual field: "code - name"
            'filter': (
                'array_contains(string_to_array("habitats", \',\'), current_value(\'code_l2\')) OR '
                'array_contains(string_to_array("habitats", \',\'), current_value(\'code_l3\')) OR '
                'array_contains(string_to_array("habitats", \',\'), current_value(\'code_l4\')) OR '
                'array_contains(string_to_array("habitats", \',\'), current_value(\'code_l5\'))'
            ),
        }
    },
    'condition': {
        'alias': 'Condition',
    },
    'author': {
        'alias': 'Author',
    },
    'created': {
        'alias': 'Created',
    },
    'updated': {
        'alias': 'Updated',
    },
    'area': {
        'alias': 'Area (m²)',
    },
    'length': {
        'alias': 'Length (m)',
    },
}

# ValueMap for Condition field - ordered list preserves dropdown order
CONDITION_VALUES = [
    {"": ""},
    {"Good": "Good"},
    {"Fairly good": "Fairly good"},
    {"Moderate": "Moderate"},
    {"Fairly Poor": "Fairly Poor"},
    {"Poor": "Poor"},
]

# ============================================================================
# Symbology
# ============================================================================

# L2 habitat colors - keyed by code (what's stored in Code_L2 field)
# Format: (Baseline RGB, Proposed RGB - lighter version)
L2_COLORS = {
    "g": {"baseline": (0, 252, 4), "proposed": (128, 255, 130)},        # Grassland
    "w": {"baseline": (51, 160, 44), "proposed": (153, 204, 150)},      # Woodland and Forest
    "h": {"baseline": (130, 104, 214), "proposed": (179, 159, 230)},    # Heathland and Scrub
    "f": {"baseline": (253, 123, 238), "proposed": (255, 180, 245)},    # Wetland
    "c": {"baseline": (255, 127, 0), "proposed": (255, 180, 100)},      # Cropland
    "u": {"baseline": (236, 34, 68), "proposed": (245, 120, 140)},      # Urban
    "s": {"baseline": (168, 168, 164), "proposed": (200, 200, 198)},    # Sparsely Vegetated Land
    "r": {"baseline": (39, 237, 245), "proposed": (130, 245, 250)},     # Rivers and Lakes
    "t": {"baseline": (0, 0, 255), "proposed": (100, 100, 255)},        # Marine Inlets
}

# Symbology field - which field to use for categorized rendering
SYMBOLOGY_FIELD = "code_l2"

# ============================================================================
# Form Configuration
# ============================================================================

# Form tab structure - defines which fields appear in each tab
# Tabs are shown in the order listed
FORM_TABS = [
    {
        'name': 'Habitat',
        'fields': ['code_l2', 'code_l3', 'code_l4', 'code_l5', 'secondary_codes', 'condition'],
    },
    {
        'name': 'Metadata',
        'fields': ['author', 'created', 'updated', 'area', 'length'],
    },
]


