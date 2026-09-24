#!/usr/bin/env python3
"""
Configuration for UKHAB QGIS project.

This file contains constants and structure definitions used by create_ukhab.py

Usage:
    from config import DRAWING_LAYERS, DRAWING_FIELDS, AUTHOR_DEFAULT
"""

from os import path
from osgeo import ogr

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
EXTENT = (0, 0, 700000, 1200000)
AUTHOR_DEFAULT = "@user_full_name"  # QGIS variable (no quotes)

# ============================================================================
# Layer Structure
# ============================================================================

# Drawing layers with their geometry types (ukhab name and ogr type)
DRAWING_LAYERS = {
    "Baseline_Areas": {"ukhab": "Area", "ogr": ogr.wkbPolygon},
    "Baseline_Lines": {"ukhab": "Line", "ogr": ogr.wkbLineString},
    "Baseline_Points": {"ukhab": "Point", "ogr": ogr.wkbPoint},
    "Proposed_Areas": {"ukhab": "Area", "ogr": ogr.wkbPolygon},
    "Proposed_Lines": {"ukhab": "Line", "ogr": ogr.wkbLineString},
    "Proposed_Points": {"ukhab": "Point", "ogr": ogr.wkbPoint},
}

# Project-specific layers (non-UKHAB)
PROJECT_LAYERS = {
    "Boundary_line": ogr.wkbPolygon,
}

# Shared Metadata Fields (used by all spatial layers)
METADATA_FIELDS = [
    {"name": "author", "type": ogr.OFTString, "width": 100},
    {"name": "created", "type": ogr.OFTDateTime},
    {"name": "updated", "type": ogr.OFTDateTime},
    {"name": "area", "type": ogr.OFTReal},
    {"name": "length", "type": ogr.OFTReal},
]

METADATA_FIELD_CONFIG = {
    'author': {
        'alias': 'Author',
        'default': AUTHOR_DEFAULT,
    },
    'created': {
        'alias': 'Created',
        'default': 'now()',
    },
    'updated': {
        'alias': 'Updated',
        'default': 'now()',
        'apply_on_update': True,
    },
    'area': {
        'alias': 'Area (m²)',
        'default': 'round($area, 2)',
    },
    'length': {
        'alias': 'Length (m)',
        # Default for Line geometry; overridden to $perimeter for Area geometry in code
        'default': 'round($length, 2)',
    },
}

# Shared Metadata form tab
METADATA_TAB = {
    'name': 'Metadata',
    'fields': ['author', 'created', 'updated', 'area', 'length'],
}

# UKHAB-Specific Fields and Configuration
UKHAB_SPECIFIC_FIELDS = [
    {"name": "code_l2", "type": ogr.OFTString, "width": 50, "required": True},
    {"name": "code_l3", "type": ogr.OFTString, "width": 50},
    {"name": "code_l4", "type": ogr.OFTString, "width": 50},
    {"name": "code_l5", "type": ogr.OFTString, "width": 50},
    {"name": "secondary_codes", "type": ogr.OFTStringList},
    {"name": "condition", "type": ogr.OFTString, "width": 20},
]

# Compose full field list: UKHAB-specific + shared metadata
DRAWING_FIELDS = UKHAB_SPECIFIC_FIELDS + METADATA_FIELDS

UKHAB_SPECIFIC_FIELD_CONFIG = {
    'code_l2': {
        'alias': 'Habitat L2',
        'required': True,
        'valuerelation': {
            'layer': 'Primary_Codes',
            'key': 'code',
            'value': 'display_field',
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
            'value': 'display_field',
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
}

# Merge UKHAB-specific + shared metadata config
FIELD_CONFIG = {**UKHAB_SPECIFIC_FIELD_CONFIG, **METADATA_FIELD_CONFIG}

# Note: ValueRelation 'value' must be a field name, NOT an expression
# Virtual field 'display_field' shows "Code - Habitat" format (e.g., "g - Grassland")

# UKHAB form tabs: Habitat + shared Metadata tab
# Tabs are shown in the order listed
FORM_TABS = [
    {
        'name': 'Habitat',
        'fields': ['code_l2', 'code_l3', 'code_l4', 'code_l5', 'secondary_codes', 'condition'],
    },
    METADATA_TAB,
]

# ============================================================================
# Project-Specific Fields and Configuration
# ============================================================================

# Project-specific fields (in addition to shared metadata)
PROJECT_SPECIFIC_FIELDS = [
    {"name": "comment", "type": ogr.OFTString, "width": 255},
]

# Compose full field list: Project-specific + shared metadata
PROJECT_FIELDS = PROJECT_SPECIFIC_FIELDS + METADATA_FIELDS

PROJECT_SPECIFIC_FIELD_CONFIG = {
    'comment': {
        'alias': 'Comment',
    },
}

# Merge project-specific + shared metadata config
PROJECT_FIELD_CONFIG = {**PROJECT_SPECIFIC_FIELD_CONFIG, **METADATA_FIELD_CONFIG}

# Project form tabs: layer-specific + shared Metadata tab
PROJECT_FORM_TABS = [
    {
        'name': 'Boundary',
        'fields': ['comment'],
    },
    METADATA_TAB,
]

# Fields to mao to primary_codes csv columns
PRIMARY_FIELDS = [
    {"name": "code", "type": ogr.OFTString, "width": 50},
    {"name": "habitat", "type": ogr.OFTString, "width": 200},
    {"name": "level", "type": ogr.OFTInteger},
    {"name": "geometry", "type": ogr.OFTString, "width": 100},
]

# Fields to mao to secondary_codes csv columns
SECONDARY_FIELDS = [
    {"name": "code", "type": ogr.OFTString, "width": 50},
    {"name": "name", "type": ogr.OFTString, "width": 200},
    {"name": "habitats", "type": ogr.OFTString, "width": 200},
    {"name": "geometry", "type": ogr.OFTString, "width": 100},
]

# L2 habitat colors - keyed by code
# Format: {"baseline": (R, G, B), "proposed": (R, G, B)}
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

# ValueMap for Condition field - ordered list preserves dropdown order
CONDITION_VALUES = [
    {"": ""},
    {"Good": "Good"},
    {"Fairly good": "Fairly good"},
    {"Moderate": "Moderate"},
    {"Fairly Poor": "Fairly Poor"},
    {"Poor": "Poor"},
]
