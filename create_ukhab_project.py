#!/usr/bin/env python3
"""
Create complete UKHAB QGIS project with form configuration.

Run in QGIS batch mode:
  qgis --code create_ukhab_project.py

Save the project file in QGIS once complete.

"""

import os
import sys

from qgis.core import (
    QgsAttributeEditorContainer,
    QgsAttributeEditorField,
    QgsCategorizedSymbolRenderer,
    QgsCoordinateReferenceSystem,
    QgsDefaultValue,
    QgsEditFormConfig,
    QgsEditorWidgetSetup,
    QgsFieldConstraints,
    QgsFillSymbol,
    QgsProject,
    QgsRectangle,
    QgsReferencedRectangle,
    QgsRendererCategory,
    QgsVectorLayer,
    QgsField,
)
from qgis.PyQt.QtCore import (
    QCoreApplication,
    QVariant,
)

# Add current directory to Python path so config imports work in qgis --code
# Note: __file__ is not available in qgis, so use cwd
cwd = os.getcwd()
if cwd not in sys.path:
    sys.path.insert(0, cwd)


from config import (
    AUTHOR_DEFAULT,
    CONDITION_VALUES,
    CRS,
    DRAWING_LAYERS,
    EXTENT,
    FIELD_CONFIG,
    FORM_TABS,
    GPKG_PATH,
    L2_COLORS,
    PROJECT_PATH,
    SYMBOLOGY_FIELD,
)


def create_l2_symbology(geom_type, is_proposed=False):
    """Create categorized symbology for L2 habitats.

    Args:
        geom_type: Geometry of layer (Area or Line)
        is_proposed: If True, use lighter colors + dashed outline for Proposed layers

    Returns:
        QgsCategorizedSymbolRenderer configured for Code_L2 field
    """
    renderer = QgsCategorizedSymbolRenderer(SYMBOLOGY_FIELD)

    for code, colors in L2_COLORS.items():
        color_key = "proposed" if is_proposed else "baseline"
        r, g, b = colors[color_key]

        # Proposed layers get dashed outline, baseline gets solid
        outline_style = 'dash' if is_proposed else 'solid'

        if geom_type == 'Area':
            symbol = QgsFillSymbol.createSimple({
                'color': f'{r},{g},{b},255',
                'outline_color': f'{r},{g},{b},255',
                'outline_width': '1',
                'outline_style': outline_style,
                'style': 'solid'
            })
        elif geom_type == 'Line':
            symbol = QgsLineSymbol.createSimple({
                'color': f'{r},{g},{b},255',
                'width': '1',
            })

        renderer.addCategory(QgsRendererCategory(code, symbol, code))

    return renderer


def load_layer(gpkg_path, layer_name):
    """Load a vector layer from GeoPackage."""
    uri = f"{gpkg_path}|layername={layer_name}"
    layer = QgsVectorLayer(uri, layer_name, "ogr")
    if not layer.isValid():
        raise ValueError(f"Failed to load layer: {layer_name}")
    return layer


def setup_relation(layer, field, lookup, key_field, value_field, filter_expr):
    """Set up a ValueRelation widget with filter expression.

    Args:
        layer: Target layer
        field: Field name to configure
        lookup: Lookup layer (Primary_Codes or Secondary_Codes)
        key_field: Field to store (e.g., "Code")
        value_field: Field to display (e.g., "Habitat") - MUST be a field name, not expression
        filter_expr: Filter expression for dropdown options
    """
    idx = layer.fields().indexOf(field)

    config = {
        "Layer": lookup.id(),
        # Value stored in field
        "Key": key_field,
        # Value displayed in dropdown
        "Value": value_field,
        "AllowNull": True,
        "OrderByValue": True,
        "FilterExpression": filter_expr,
    }
    layer.setEditorWidgetSetup(idx, QgsEditorWidgetSetup("ValueRelation", config))


def setup_string_list(layer, field, lookup, key_field, value_field, filter_expr):
    """Set up a ValueRelation widget for multi-select with filter."""
    idx = layer.fields().indexOf(field)

    config = {
        "Layer": lookup.id(),
        "Key": key_field,
        "Value": value_field,
        "AllowNull": True,
        "AllowMulti": True,
        "OrderByValue": True,
        "FilterExpression": filter_expr,
    }
    layer.setEditorWidgetSetup(idx, QgsEditorWidgetSetup("ValueRelation", config))


def setup_valuemap(layer, field, value_map):
    """Set up ValueMap widget with list-of-dicts for order preservation."""
    idx = layer.fields().indexOf(field)

    config = {"map": value_map}
    layer.setEditorWidgetSetup(idx, QgsEditorWidgetSetup("ValueMap", config))


def set_default(layer, field, expr, update_on_edit=False):
    """Set default value for a field."""
    idx = layer.fields().indexOf(field)

    default = QgsDefaultValue(expr)
    default.setApplyOnUpdate(update_on_edit)
    layer.setDefaultValueDefinition(idx, default)


def hide_field(layer, field_name):
    """Hide a field in the attribute form (e.g., fid, system fields)."""
    idx = layer.fields().indexOf(field_name)

    layer.setEditorWidgetSetup(idx, QgsEditorWidgetSetup("Hidden", {}))


def setup_form_tabs(layer):
    """Configure form with tabs: Habitat and Metadata."""
    config = layer.editFormConfig()

    config.setLayout(QgsEditFormConfig.TabLayout)
    config.clearTabs()

    for tab_def in FORM_TABS:
        tab = QgsAttributeEditorContainer(tab_def['name'], None)  # No parent for root-level tabs
        tab.setType(Qgis.AttributeEditorContainerType.Tab)

        for field_name in tab_def['fields']:
            idx = layer.fields().indexOf(field_name)
            if idx >= 0:
                field = QgsAttributeEditorField(field_name, idx, tab)
                tab.addChildElement(field)

        config.addTab(tab)

    layer.setEditFormConfig(config)


def configure_layer(layer, primary, secondary, geom_type):
    """Configure form widgets for a drawing layer."""

    # Hide fid field (system field)
    hide_field(layer, "fid")

    # Configure ValueRelation widgets for primary_codes level fields
    for field in ["code_l2", "code_l3", "code_l4", "code_l5"]:
        cfg = FIELD_CONFIG[field]['valuerelation']
        filter_expr = cfg['filter'].format(geometry_type=f"'{geom_type}'")
        setup_relation(layer, field, primary, cfg['key'], cfg['value'], filter_expr)

    # secondary_codes - show if ANY of L2/L3/L4/L5 matches a habitat in the list
    cfg = FIELD_CONFIG['secondary_codes']['valuerelation']
    setup_string_list(layer, "secondary_codes", secondary, cfg['key'], cfg['value'], cfg['filter'])

    # Condition - ValueMap with ordered list-of-dicts
    setup_valuemap(layer, "Condition", CONDITION_VALUES)

    # Virtual fields for area/length (calculated from geometry)
    if geom_type == "Area":
        set_default(layer, "area", "round($area, 2)")
        set_default(layer, "length", "round($perimeter, 2)")
    elif geom_type == "Line":
        set_default(layer, "length", "round($length, 2)")

    set_default(layer, "author", AUTHOR_DEFAULT)
    set_default(layer, "created", "now()")
    set_default(layer, "updated", "now()", update_on_edit=True)

    # NOT NULL constraint on code_l2
    idx = layer.fields().indexOf("code_l2")
    if idx >= 0:
        layer.setFieldConstraint(idx, QgsFieldConstraints.ConstraintNotNull)

    # Set field name aliases (for form display)
    for field_name, field_config in FIELD_CONFIG.items():
        idx = layer.fields().indexOf(field_name)
        if idx >= 0:
            alias = field_config.get('alias', field_name)
            layer.setFieldAlias(idx, alias)

    # Set up form tabs (Habitat, Metadata)
    setup_form_tabs(layer)

def main():

    crs = QgsCoordinateReferenceSystem(CRS)

    if not os.path.exists(GPKG_PATH):
        print(f"Error: {gpkg_path} not found!")
        print("Run: python3 create_gpkg.py first")
        sys.exit(1)

    project = QgsProject.instance()
    project.clear()

    # Set CRS for project
    project.setCrs(crs)

    # Create a CRS-referenced rectangle that covers the CRS
    rect = QgsRectangle(*EXTENT)
    ref_extent = QgsReferencedRectangle(rect, crs)

    # Set the view extent to be this rectangle
    project.viewSettings().setPresetFullExtent(ref_extent)

    primary = load_layer(GPKG_PATH, "Primary_Codes")
    secondary = load_layer(GPKG_PATH, "Secondary_Codes")

    # Add virtual fields to lookup layers for display (Code - Habitat format)
    # Primary_Codes: display_field = "g - Grassland"
    primary.addExpressionField('"code" || \' - \' || "habitat"', QgsField('display_field', QVariant.String))

    # Secondary_Codes: display_field = "10 - Scattered scrub"
    secondary.addExpressionField('"code" || \' - \' || "name"', QgsField('display_field', QVariant.String))

    # Codes layers are just data, not drawing layers - make them read-only
    primary.setReadOnly(True)
    secondary.setReadOnly(True)
    project.addMapLayer(primary, addToLegend=False)
    project.addMapLayer(secondary, addToLegend=False)

    drawing_layers = {}
    for layer_name, geom_type in DRAWING_LAYERS.items():
        layer = load_layer(GPKG_PATH, layer_name)

        # Configure BEFORE adding to project (aliases won't persist otherwise)
        configure_layer(layer, primary, secondary, geom_type)

        # Apply L2 categorized symbology to Area layers only
        if geom_type in ("Area", "Line"):
            layer.setRenderer(create_l2_symbology(geom_type, is_proposed=layer_name.startswith("Proposed")))

        project.addMapLayer(layer, False)
        drawing_layers[layer_name] = (layer, geom_type)

    # Set up layer tree
    root = project.layerTreeRoot()

    # Add groups (Proposed first to overlay on top of Baseline)
    proposed_group = root.addGroup("Proposed")
    baseline_group = root.addGroup("Baseline")

    for layer_name, (layer, geom_type) in drawing_layers.items():
        if layer_name.startswith("Baseline"):
            baseline_group.addLayer(layer)
        else:
            proposed_group.addLayer(layer)

    # Add 'data' layers last to place below map layers in layer list
    root.addLayer(primary)
    root.addLayer(secondary)

    # Signal QGIS to process all outstanding events
    QCoreApplication.processEvents()

    # Save project and mark as clean
    project.setFileName(PROJECT_PATH)
    project.write()


if __name__ == "__main__":
    main()
