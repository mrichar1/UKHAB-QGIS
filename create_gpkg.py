#!/usr/bin/env python3
"""
Create UKHAB GeoPackage for QGIS.

Generates a GeoPackage file containing:
- Primary Codes lookup table (non-spatial)
- Secondary Codes lookup table (non-spatial)
- Baseline drawing layers (Areas, Lines, Points)
- Proposed drawing layers (Areas, Lines, Points)
"""

import csv
import os

from osgeo import gdal, ogr, osr

from config import (
    CRS,
    DRAWING_FIELDS,
    DRAWING_LAYERS,
    GPKG_PATH,
    PRIMARY_CSV,
    SECONDARY_CSV,
)

# Enable exceptions for better error handling (GDAL 4.0+ compatibility)
gdal.UseExceptions()

# Map generic type names to GDAL/OGR types
TYPE_MAP = {
    "string": ogr.OFTString,
    "string_list": ogr.OFTStringList,
    "integer": ogr.OFTInteger,
    "real": ogr.OFTReal,
    "datetime": ogr.OFTDateTime,
}

# Map UKHAB geometry names to GDAL geometry types
GEOM_TYPE_MAP = {
    "Area": ogr.wkbPolygon,
    "Line": ogr.wkbLineString,
    "Point": ogr.wkbPoint,
}

def create_gpkg(output_path: str) -> ogr.DataSource:
    """Create a new GeoPackage file."""
    driver = ogr.GetDriverByName("GPKG")
    if os.path.exists(output_path):
        driver.DeleteDataSource(output_path)
    return driver.CreateDataSource(output_path)


def create_lookup_table(
    ds: ogr.DataSource,
    table_name: str,
    field_defs: list[dict],
    csv_path: str,
):
    """Create a non-spatial lookup table from CSV."""
    layer = ds.CreateLayer(table_name, geom_type=ogr.wkbNone)

    # Add fields
    for field_def in field_defs:
        field = ogr.FieldDefn(field_def["name"], field_def["type"])
        if "width" in field_def:
            field.SetWidth(field_def["width"])
        layer.CreateField(field)

    # Load data from CSV (comma is default delimiter)
    layer_defn = layer.GetLayerDefn()
    with open(csv_path, newline="", encoding="utf-8") as csvfile:
        reader = csv.DictReader(csvfile)
        for row in reader:
            feature = ogr.Feature(layer_defn)
            for field_def in field_defs:
                field_name = field_def["name"]
                field_idx = layer_defn.GetFieldIndex(field_name)
                value = row.get(field_name, "")

                # Handle different field types
                if field_def["type"] == ogr.OFTStringList:
                    if value:
                        value_list = [v.strip() for v in value.split(",")]
                        feature.SetFieldStringList(field_idx, value_list)
                    else:
                        feature.SetFieldStringList(field_idx, [])
                else:
                    # Handle scalar types (Integer, Real, String)
                    if field_def["type"] == ogr.OFTInteger:
                        value = int(value) if value else 0
                    elif field_def["type"] == ogr.OFTReal:
                        value = float(value) if value else 0.0
                    # OFTString keeps value as-is

                    feature.SetField(field_idx, value)
            layer.CreateFeature(feature)

def create_drawing_layer(
    ds: ogr.DataSource,
    layer_name: str,
    geom_type: int,
):
    """Create a drawing layer with geometry and attribute fields."""

    # Create layer with CRS from config
    srs = osr.SpatialReference()
    srs.ImportFromEPSG(int(CRS.split(':')[1]))
    layer = ds.CreateLayer(layer_name, srs=srs, geom_type=geom_type)

    # Add fields
    for field_def in DRAWING_FIELDS:
        field_type = TYPE_MAP.get(field_def["type"], ogr.OFTString)
        field = ogr.FieldDefn(field_def["name"], field_type)
        if "width" in field_def:
            field.SetWidth(field_def["width"])
        layer.CreateField(field)

def main():
    """Main entry point."""

    # Create the GeoPackage
    ds = create_gpkg(GPKG_PATH)

    # Create Primary Codes lookup table
    # Note: geometry stored as plain string (not StringList) for compatibility
    primary_fields = [
        {"name": "code", "type": ogr.OFTString, "width": 50},
        {"name": "habitat", "type": ogr.OFTString, "width": 200},
        {"name": "level", "type": ogr.OFTInteger},
        {"name": "geometry", "type": ogr.OFTString, "width": 100},
    ]
    create_lookup_table(ds, "Primary_Codes", primary_fields, PRIMARY_CSV)

    # Create Secondary Codes lookup table
    # Note: habitats and geometry stored as plain strings for string_to_array() compatibility
    secondary_fields = [
        {"name": "code", "type": ogr.OFTString, "width": 50},
        {"name": "name", "type": ogr.OFTString, "width": 200},
        {"name": "habitats", "type": ogr.OFTString, "width": 200},
        {"name": "geometry", "type": ogr.OFTString, "width": 100},
    ]
    create_lookup_table(ds, "Secondary_Codes", secondary_fields, SECONDARY_CSV)

    # Create drawing layers
    for layer_name, geom in DRAWING_LAYERS.items():
        create_drawing_layer(ds, layer_name, GEOM_TYPE_MAP[geom])

    print(f"\nGeoPackage created successfully: {GPKG_PATH}")


if __name__ == "__main__":
    main()
