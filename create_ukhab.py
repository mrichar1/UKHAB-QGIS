#!/usr/bin/env python3
"""
Create UKHAB GeoPackage and linked QGIS project.

Run in QGIS batch mode:
  qgis --minimal --code ukhab_create.py

"""

import csv
import os
import sys

from osgeo import gdal, ogr, osr

from qgis.core import (
    QgsAttributeEditorContainer,
    QgsAttributeEditorField,
    QgsCategorizedSymbolRenderer,
    QgsCoordinateReferenceSystem,
    QgsDefaultValue,
    QgsEditFormConfig,
    QgsEditorWidgetSetup,
    QgsField,
    QgsFieldConstraints,
    QgsFillSymbol,
    QgsLineSymbol,
    QgsProject,
    QgsSingleSymbolRenderer,
    QgsRectangle,
    QgsReferencedRectangle,
    QgsRendererCategory,
    QgsVectorLayer,
    Qgis,
)
from qgis.PyQt.QtCore import QCoreApplication, QVariant

# Add current directory to Python path for qgis --code mode
cwd = os.getcwd()
if cwd not in sys.path:
    sys.path.insert(0, cwd)

from config import (
    AUTHOR_DEFAULT,
    PROJECT_FIELD_CONFIG,
    PROJECT_FIELDS,
    PROJECT_FORM_TABS,
    PROJECT_LAYERS,
    CONDITION_VALUES,
    CRS,
    DRAWING_FIELDS,
    DRAWING_LAYERS,
    EXTENT,
    FIELD_CONFIG,
    FORM_TABS,
    GPKG_PATH,
    L2_COLORS,
    PRIMARY_CSV,
    PRIMARY_FIELDS,
    PROJECT_PATH,
    SECONDARY_CSV,
    SECONDARY_FIELDS,
    SYMBOLOGY_FIELD,
)

# Enable GDAL exceptions
gdal.UseExceptions()


def _create_layer_with_fields(ds, layer_name, geom_type, field_defs):
    """Create a layer with the specified geometry type and fields."""
    srs = osr.SpatialReference()
    srs.ImportFromEPSG(int(CRS.split(':')[1]))
    layer = ds.CreateLayer(layer_name, srs=srs, geom_type=geom_type)
    for field_def in field_defs:
        field = ogr.FieldDefn(field_def["name"], field_def["type"])
        if "width" in field_def:
            field.SetWidth(field_def["width"])
        layer.CreateField(field)
    return layer


def _apply_field_defaults(layer, field_config, geom_type=None):
    """Apply field aliases and default values from config."""
    for field_name, config in field_config.items():
        idx = layer.fields().indexOf(field_name)
        if idx < 0:
            continue

        # Set alias
        layer.setFieldAlias(idx, config.get('alias', field_name))

        # Set default value if defined
        if 'default' in config:
            default_expr = config['default']
            # For Area geometry, length field should use perimeter
            if field_name == 'length' and geom_type == 'Area':
                default_expr = 'round($perimeter, 2)'
                layer.setFieldAlias(idx, 'Perimeter (m)')

            default = QgsDefaultValue(default_expr)
            if config.get('apply_on_update'):
                default.setApplyOnUpdate(True)
            layer.setDefaultValueDefinition(idx, default)


def _create_lookup_table(ds, table_name, field_defs, csv_path):
    """Create a non-spatial lookup table from CSV."""
    layer = ds.CreateLayer(table_name, geom_type=ogr.wkbNone)
    for field_def in field_defs:
        field = ogr.FieldDefn(field_def["name"], field_def["type"])
        if "width" in field_def:
            field.SetWidth(field_def["width"])
        layer.CreateField(field)

    layer_defn = layer.GetLayerDefn()
    with open(csv_path, newline="", encoding="utf-8") as csvfile:
        reader = csv.DictReader(csvfile)
        for row in reader:
            feature = ogr.Feature(layer_defn)
            for i in range(layer_defn.GetFieldCount()):
                field_def = layer_defn.GetFieldDefn(i)
                field_idx = layer_defn.GetFieldIndex(field_def.name)
                value = row.get(field_def.name, "")
                if field_def.type == ogr.OFTInteger:
                    value = int(value) if value else 0
                feature.SetField(field_idx, value)
            layer.CreateFeature(feature)


def create_gpkg():
    """Create GeoPackage with lookup tables and drawing layers."""
    driver = ogr.GetDriverByName("GPKG")
    if os.path.exists(GPKG_PATH):
        driver.DeleteDataSource(GPKG_PATH)
    ds = driver.CreateDataSource(GPKG_PATH)

    # Create lookup tables
    _create_lookup_table(ds, "Primary_Codes", PRIMARY_FIELDS, PRIMARY_CSV)
    _create_lookup_table(ds, "Secondary_Codes", SECONDARY_FIELDS, SECONDARY_CSV)

    # Create UKHAB drawing layers (with attribute fields)
    for layer_name, geom_info in DRAWING_LAYERS.items():
        _create_layer_with_fields(ds, layer_name, geom_info["ogr"], DRAWING_FIELDS)

    # Create project layers (with minimal metadata fields)
    for layer_name, geom_type in PROJECT_LAYERS.items():
        _create_layer_with_fields(ds, layer_name, geom_type, PROJECT_FIELDS)


def create_qgis_project():
    """Create QGIS project with configured layers and symbology."""
    crs = QgsCoordinateReferenceSystem(CRS)
    project = QgsProject.instance()
    project.clear()
    project.setCrs(crs)

    # Set project extent to CRS bounds
    rect = QgsRectangle(*EXTENT)
    project.viewSettings().setPresetFullExtent(QgsReferencedRectangle(rect, crs))

    # Load lookup layers
    def load_layer(name):
        uri = f"{GPKG_PATH}|layername={name}"
        layer = QgsVectorLayer(uri, name, "ogr")
        if not layer.isValid():
            raise ValueError(f"Failed to load layer: {name}")
        return layer

    primary = load_layer("Primary_Codes")
    secondary = load_layer("Secondary_Codes")

    # Add display field virtual columns
    primary.addExpressionField('"code" || \' - \' || "habitat"',
                                QgsField('display_field', QVariant.String))
    secondary.addExpressionField('"code" || \' - \' || "name"',
                                  QgsField('display_field', QVariant.String))

    # Lookup layers are data-only, not for editing
    primary.setReadOnly(True)
    secondary.setReadOnly(True)
    project.addMapLayer(primary, addToLegend=False)
    project.addMapLayer(secondary, addToLegend=False)

    # Create and configure ukhab drawing layers
    drawing_layers = {}
    for layer_name, geom_info in DRAWING_LAYERS.items():
        geom_type = geom_info["ukhab"]
        layer = load_layer(layer_name)

        # Hide fid field
        idx = layer.fields().indexOf("fid")
        layer.setEditorWidgetSetup(idx, QgsEditorWidgetSetup("Hidden", {}))

        # Configure ValueRelation widgets for primary code fields
        for field in ["code_l2", "code_l3", "code_l4", "code_l5"]:
            cfg = FIELD_CONFIG[field]['valuerelation']
            filter_expr = cfg['filter'].format(geometry_type=f"'{geom_type}'")
            field_idx = layer.fields().indexOf(field)
            config = {
                "Layer": primary.id(),
                "Key": cfg['key'],
                "Value": cfg['value'],
                "AllowNull": True,
                "OrderByValue": True,
                "FilterExpression": filter_expr,
            }
            layer.setEditorWidgetSetup(field_idx, QgsEditorWidgetSetup("ValueRelation", config))

        # Secondary codes multi-select
        cfg = FIELD_CONFIG['secondary_codes']['valuerelation']
        field_idx = layer.fields().indexOf("secondary_codes")
        config = {
            "Layer": secondary.id(),
            "Key": cfg['key'],
            "Value": cfg['value'],
            "AllowNull": True,
            "AllowMulti": True,
            "OrderByValue": True,
            "FilterExpression": cfg['filter'],
        }
        layer.setEditorWidgetSetup(field_idx, QgsEditorWidgetSetup("ValueRelation", config))

        # Condition dropdown
        field_idx = layer.fields().indexOf("condition")
        layer.setEditorWidgetSetup(field_idx, QgsEditorWidgetSetup("ValueMap", {"map": CONDITION_VALUES}))

        # Apply field aliases and default values
        _apply_field_defaults(layer, FIELD_CONFIG, geom_type)

        # Set NOT NULL constraint on required fields
        for field_name, field_config in FIELD_CONFIG.items():
            if field_config.get('required'):
                idx = layer.fields().indexOf(field_name)
                if idx >= 0:
                    layer.setFieldConstraint(idx, QgsFieldConstraints.ConstraintNotNull)

        # Form tabs
        config = layer.editFormConfig()
        config.setLayout(QgsEditFormConfig.TabLayout)
        config.clearTabs()
        for tab_def in FORM_TABS:
            tab = QgsAttributeEditorContainer(tab_def['name'], None)
            tab.setType(Qgis.AttributeEditorContainerType.Tab)
            for field_name in tab_def['fields']:
                idx = layer.fields().indexOf(field_name)
                if idx >= 0:
                    field = QgsAttributeEditorField(field_name, idx, tab)
                    tab.addChildElement(field)
            config.addTab(tab)
        layer.setEditFormConfig(config)

        # Apply ukhab symbology
        if geom_type in ("Area", "Line"):
            is_proposed = layer_name.startswith("Proposed")
            renderer = QgsCategorizedSymbolRenderer(SYMBOLOGY_FIELD)
            for code, colors in L2_COLORS.items():
                color_key = "proposed" if is_proposed else "baseline"
                r, g, b = colors[color_key]
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
            layer.setRenderer(renderer)

        project.addMapLayer(layer, False)
        drawing_layers[layer_name] = (layer, geom_info)

    # Load and configure project (non-ukhab) layers
    project_layers = []
    for layer_name in PROJECT_LAYERS:
        layer = load_layer(layer_name)

        # Hide fid field
        idx = layer.fields().indexOf("fid")
        layer.setEditorWidgetSetup(idx, QgsEditorWidgetSetup("Hidden", {}))

        # Apply field aliases and default values
        _apply_field_defaults(layer, PROJECT_FIELD_CONFIG)

        # Apply symbology (red outline for Boundary_line only)
        if layer_name == "Boundary_line":
            layer.setRenderer(QgsSingleSymbolRenderer(
                QgsFillSymbol.createSimple({
                    'color': '0,0,0,0',  # Transparent fill
                    'outline_color': '255,0,0,255',  # Red outline
                    'outline_width': '1.5'
                })
            ))

        # Form configuration
        config = layer.editFormConfig()
        config.setLayout(QgsEditFormConfig.TabLayout)
        config.clearTabs()
        for tab_def in PROJECT_FORM_TABS:
            tab = QgsAttributeEditorContainer(tab_def['name'], None)
            tab.setType(Qgis.AttributeEditorContainerType.Tab)
            for field_name in tab_def['fields']:
                idx = layer.fields().indexOf(field_name)
                if idx >= 0:
                    field = QgsAttributeEditorField(field_name, idx, tab)
                    tab.addChildElement(field)
            config.addTab(tab)
        layer.setEditFormConfig(config)

        project.addMapLayer(layer, False)
        project_layers.append(layer)

    # Build layer tree
    root = project.layerTreeRoot()

    # Add project-specific layers (non-UKHAB)
    project_group = root.addGroup("Project")
    for layer in project_layers:
        project_group.addLayer(layer)

    # Add UKHAB layers
    proposed_group = root.addGroup("Proposed")
    baseline_group = root.addGroup("Baseline")

    for layer_name, (layer, _) in drawing_layers.items():
        if layer_name.startswith("Baseline"):
            node = baseline_group.addLayer(layer)
        else:
            node = proposed_group.addLayer(layer)
        # Collapse sub-layers (categorized symbology etc) by default
        node.setExpanded(False)

    # Add lookup layers to legend (below drawing layers)
    root.addLayer(primary)
    root.addLayer(secondary)

    # Process events and save
    QCoreApplication.processEvents()
    project.setFileName(PROJECT_PATH)
    project.write()


def main():
    """Create GeoPackage and QGIS project."""
    create_gpkg()
    create_qgis_project()


if __name__ == "__main__":
    main()
