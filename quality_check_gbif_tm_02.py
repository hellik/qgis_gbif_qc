"""
2026 Helmut Kudrnovsky

This file is part of a prototype of a GBIF data quality check on the example of Typha minima - part 2
See LICENSE in the project root for full license information.
"""

from qgis.core import (
    QgsProject,
    QgsField
)
from qgis.PyQt.QtCore import QVariant

# Layer abrufen
layer_name = "Typha minima (GBIF 2026-09-18)"
layers = QgsProject.instance().mapLayersByName(layer_name)

if not layers:
    raise ValueError(f"Layer '{layer_name}' wurde im QGIS-Projekt nicht gefunden!")

layer = layers[0]
provider = layer.dataProvider()

# 1. Neue Felder für die Areal-Qualitätsprüfung definieren
new_fields = [
    QgsField("flag_outside_native_range", QVariant.Int),
    QgsField("native_status_note", QVariant.String, len=150)
]

existing_field_names = layer.fields().names()
fields_to_add = [f for f in new_fields if f.name() not in existing_field_names]

if fields_to_add:
    provider.addAttributes(fields_to_add)
    layer.updateFields()

# Indizes der neuen und benötigten Spalten abrufen
idx_flag_range = layer.fields().indexOf("flag_outside_native_range")
idx_note_range = layer.fields().indexOf("native_status_note")

idx_country = layer.fields().indexOf("countryCode")
idx_lat = layer.fields().indexOf("decimalLatitude")
idx_lon = layer.fields().indexOf("decimalLongitude")
idx_establishment = layer.fields().indexOf("establishmentMeans")

# ISO-Codes von Ländern mit nachgewiesen nicht-natürlichen Vorkommen 
# (laut GRIIS, Euro+Med und Catalogue of Life: Neophyten, Synanthrop, Ansalbung, Ex-situ)
non_native_iso = {
    "GB", "NL", "BE", "DK", "SE", "NO", "FI", "PL", 
    "IE", "EE", "LV", "LT", "US", "CA", "NZ", "AU"
}

layer.startEditing()

for feature in layer.getFeatures():
    flag_val = 0
    note_val = "Indigen / Natürliches Areal"
    
    # Attributwerte auslesen
    country = str(feature.attribute(idx_country)).upper().strip() if idx_country != -1 else ""
    est = str(feature.attribute(idx_establishment)).upper() if idx_establishment != -1 else ""
    geom = feature.geometry()
    
    # CHECK 1: Prüfung nach ISO-Ländercodes (Katalogisierung neophytischer Räume)
    if country in non_native_iso:
        flag_val = 1
        note_val = f"Arealfremd (Land {country}: Neophyt/Adventiv/Ansalbung)"
        
    # CHECK 2: Metadaten-Check auf Ansalbung / Invasiv-Status in GBIF
    elif "INTRODUCED" in est or "MANAGED" in est or "INVASIVE" in est or "NATURALISED" in est:
        flag_val = 1
        note_val = f"GBIF establishmentMeans: {est}"
        
    # CHECK 3: Geografische Schwellenwert-Prüfung (Nordeuropäisches Tiefland & extralimital)
    elif geom and not geom.isEmpty():
        point = geom.asPoint()
        p_lat = point.y()
        p_lon = point.x()
        
        # Nord-Mitteleuropa (> 51.5° N westlich von 17° E, z. B. Norddeutschland/Nordfrankreich)
        if p_lat > 51.5 and p_lon < 17.0:
            flag_val = 1
            note_val = "Außerhalb Wildflussareal (Tiefland > 51.5° N)"
            
        # Extralimitale Koordinaten außerhalb des eurasischen Wildflussgürtels
        elif p_lon < -10.0 or p_lon > 100.0 or p_lat < 30.0 or p_lat > 65.0:
            flag_val = 1
            note_val = "Extralimital (Außerhalb eurasischem Korridor)"

    # Werte zurückschreiben
    feature.setAttribute(idx_flag_range, flag_val)
    feature.setAttribute(idx_note_range, note_val)
    
    layer.updateFeature(feature)

layer.commitChanges()
print("Arealfremde Vorkommen (GB, NL, BE, Nordtiefland etc.) wurden fehlerfrei geflaggt!")