"""
2026 Helmut Kudrnovsky

This file is part of a prototype of a GBIF data quality check on the example of Typha minima - part 1
See LICENSE in the project root for full license information.
"""

import datetime
from qgis.core import (
    QgsProject,
    QgsField,
    QgsColorUtils
)
from qgis.PyQt.QtCore import QVariant

# Layer abrufen
layer_name = "Typha minima (GBIF 2026-09-18)"
layers = QgsProject.instance().mapLayersByName(layer_name)

if not layers:
    raise ValueError(f"Layer '{layer_name}' wurde im QGIS-Projekt nicht gefunden!")

layer = layers[0]
provider = layer.dataProvider()

# 1. Neue Felder im Layer definieren
new_fields = [
    QgsField("zeitschnitt", QVariant.String, len=50),
    QgsField("flag_missing_coords", QVariant.Int),
    QgsField("flag_high_uncertainty", QVariant.Int),
    QgsField("flag_zero_coords", QVariant.Int),
    QgsField("flag_imprecise_date", QVariant.Int),
    QgsField("flag_basis_mismatch", QVariant.Int),
    QgsField("flag_institution_centroid", QVariant.Int)
]

# Prüfen, welche Felder noch fehlen, und diese hinzufügen
existing_field_names = layer.fields().names()
fields_to_add = [f for f in new_fields if f.name() not in existing_field_names]

if fields_to_add:
    provider.addAttributes(fields_to_add)
    layer.updateFields()

# Feld-Indizes ermitteln
idx_zeitschnitt = layer.fields().indexOf("zeitschnitt")
idx_flag_missing = layer.fields().indexOf("flag_missing_coords")
idx_flag_uncertain = layer.fields().indexOf("flag_high_uncertainty")
idx_flag_zero = layer.fields().indexOf("flag_zero_coords")
idx_flag_date = layer.fields().indexOf("flag_imprecise_date")
idx_flag_basis = layer.fields().indexOf("flag_basis_mismatch")
idx_flag_centroid = layer.fields().indexOf("flag_institution_centroid")

# GBIF-Quellfeld-Indizes
idx_year = layer.fields().indexOf("year")
idx_uncertainty = layer.fields().indexOf("coordinateUncertaintyInMeters")
idx_basis = layer.fields().indexOf("basisOfRecord")
idx_issues = layer.fields().indexOf("issue")

current_year = datetime.datetime.now().year

layer.startEditing()

for feature in layer.getFeatures():
    geom = feature.geometry()
    
    # Initiale Flag-Werte
    f_missing = 0
    f_uncertain = 0
    f_zero = 0
    f_date = 0
    f_basis = 0
    f_centroid = 0
    
    # A) Geometrie- & Koordinatencheck
    if geom.isEmpty() or geom.isNull():
        f_missing = 1
    else:
        point = geom.asPoint()
        if point.x() == 0.0 and point.y() == 0.0:
            f_zero = 1
            
    # B) Koordinatenunsicherheit (> 10.000 m)
    uncert_val = feature.attribute(idx_uncertainty) if idx_uncertainty != -1 else None
    if uncert_val is not None and uncert_val != NULL:
        try:
            if float(uncert_val) > 10000.0:
                f_uncertain = 1
        except ValueError:
            pass

    # C) Basis-Check (Fossilien, Kultureinträge)
    basis_val = str(feature.attribute(idx_basis)).upper() if idx_basis != -1 else ""
    if basis_val in ["FOSSIL_SPECIMEN", "LIVING_SPECIMEN", "MATERIAL_SAMPLE"]:
        f_basis = 1

    # D) Jahreszahlen & Zeitschnitt-Klassifikation
    year_val = feature.attribute(idx_year) if idx_year != -1 else None
    zeitschnitt_str = "Unbekannt / Ohne Jahr (k.A.)"
    
    if year_val is not None and year_val != NULL:
        try:
            yr = int(year_val)
            if yr < 1700 or yr > current_year:
                f_date = 1
            elif yr >= 2001:
                zeitschnitt_str = "Ab 2001 (Aktuell / Rezent)"
            elif 1981 <= yr <= 2000:
                zeitschnitt_str = "1981-2000 (Älter rezent)"
            elif 1950 <= yr <= 1980:
                zeitschnitt_str = "1950-1980 (Subrezent / Übergang)"
            elif 1900 <= yr <= 1949:
                zeitschnitt_str = "1900-1949 (Historisch)"
            else:
                zeitschnitt_str = "Vor 1900 (Altangabe)"
        except (ValueError, TypeError):
            f_date = 1
    else:
        f_date = 1

    # E) GBIF-Issues auf Zentroid-Flags prüfen
    issues_val = str(feature.attribute(idx_issues)) if idx_issues != -1 else ""
    if "COUNTRY_COORDINATE_MISMATCH" in issues_val or "CENTROID" in issues_val:
        f_centroid = 1

    # Attribute im Feature schreiben
    feature.setAttribute(idx_zeitschnitt, zeitschnitt_str)
    feature.setAttribute(idx_flag_missing, f_missing)
    feature.setAttribute(idx_flag_uncertain, f_uncertain)
    feature.setAttribute(idx_flag_zero, f_zero)
    feature.setAttribute(idx_flag_date, f_date)
    feature.setAttribute(idx_flag_basis, f_basis)
    feature.setAttribute(idx_flag_centroid, f_centroid)
    
    layer.updateFeature(feature)

layer.commitChanges()
print("Quality-Flags und Zeitschnitt-Klassen wurden erfolgreich im GeoPackage ergänzt!")