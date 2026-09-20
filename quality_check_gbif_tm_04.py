"""
2026 Helmut Kudrnovsky

This file is part of a prototype of a GBIF data quality check on the example of Typha minima - part 4
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

# 1. Neue Spalten definieren
new_fields = [
    QgsField("flag_asia_native_region", QVariant.Int),
    QgsField("flag_east_limit_valid", QVariant.Int),
    QgsField("asia_distribution_source", QVariant.String, len=150),
    QgsField("flag_disjunct_or_doubtful", QVariant.Int)
]

existing_field_names = layer.fields().names()
fields_to_add = [f for f in new_fields if f.name() not in existing_field_names]

if fields_to_add:
    provider.addAttributes(fields_to_add)
    layer.updateFields()

# Indizes abrufen
idx_asia_native = layer.fields().indexOf("flag_asia_native_region")
idx_east_valid = layer.fields().indexOf("flag_east_limit_valid")
idx_source_note = layer.fields().indexOf("asia_distribution_source")
idx_disjunct = layer.fields().indexOf("flag_disjunct_or_doubtful")

# Quellspalten
idx_country = layer.fields().indexOf("countryCode")
idx_outside_eur = layer.fields().indexOf("flag_outside_native_range")

# Ländercodes nach asiatischen Florenregionen
asia_central_iso = {"KZ", "UZ", "KG", "TJ", "TM", "MN"}
asia_east_iso = {"CN"}
asia_south_west_iso = {"TR", "GE", "AM", "AZ", "IR", "AF", "PK", "IN"}
russia_iso = {"RU"}

layer.startEditing()

for feature in layer.getFeatures():
    f_asia_native = 0
    f_east_valid = 0
    f_disjunct = 0
    source_str = "Euro+Med / Flora Europaea (Westpaläarktis)"
    
    country = str(feature.attribute(idx_country)).upper().strip() if idx_country != -1 else ""
    geom = feature.geometry()
    
    if geom and not geom.isEmpty():
        pt = geom.asPoint()
        lon, lat = pt.x(), pt.y()
        
        # A) Prüfe allgemeine eurasische Gültigkeitsbox (-10° W bis 135° E / 20° N bis 65° N)
        if -10.0 <= lon <= 135.0 and 20.0 <= lat <= 65.0:
            f_east_valid = 1
            
        # B) Asiatische Areal-Regionen & Quellen-Zuordnung
        
        # 1. China (Flora of China / POWO)
        if country in asia_east_iso or (73.0 <= lon <= 135.0 and 20.0 <= lat <= 53.0):
            f_asia_native = 1
            source_str = "Flora of China (Xinjiang, Gansu, Heilongjiang) / POWO"
            
        # 2. Russland Ost / Sibirien / Amur (Flora of the USSR / POWO)
        elif country in russia_iso and lon >= 60.0:
            f_asia_native = 1
            source_str = "Flora of the USSR / Siberian & Amur Corridors (POWO)"
            
        # 3. Zentralasien & Mongolei (POWO / IUCN)
        elif country in asia_central_iso or (50.0 <= lon <= 120.0 and 35.0 <= lat <= 55.0 and country not in russia_iso):
            f_asia_native = 1
            source_str = "POWO / Central Asian Riparian Flora"
            
        # 4. Vorderasien, Kaukasus & Himalaya (Flora Iranica / POWO)
        elif country in asia_south_west_iso or (26.0 <= lon <= 85.0 and 25.0 <= lat <= 42.0):
            f_asia_native = 1
            source_str = "POWO / Flora Iranica & Caucasian Corridors"
            
        # C) Disjunkt / Zweifelhaft
        # Weder im europäischen Indigenat noch im belegten asiatischen Areal
        out_eur = feature.attribute(idx_outside_eur) if idx_outside_eur != -1 else 0
        out_eur_val = int(out_eur) if (out_eur is not None and str(out_eur).isdigit()) else 0
        
        if out_eur_val == 1 and f_asia_native == 0:
            f_disjunct = 1
            source_str = "Extralimital / Zweifelhaft (Kein Nachweis in POWO/Flora of China)"

    # Werte zurückschreiben
    feature.setAttribute(idx_asia_native, f_asia_native)
    feature.setAttribute(idx_east_valid, f_east_valid)
    feature.setAttribute(idx_source_note, source_str)
    feature.setAttribute(idx_disjunct, f_disjunct)
    
    layer.updateFeature(feature)

layer.commitChanges()
print("Asien-Expansion und Quellen-Flags (POWO, Flora of China, Flora USSR) erfolgreich ergänzt!")