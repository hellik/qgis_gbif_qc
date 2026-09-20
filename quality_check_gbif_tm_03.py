"""
2026 Helmut Kudrnovsky

This file is part of a prototype of a GBIF data quality check on the example of Typha minima - part 3
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

# 1. Felder für Positiv-Checks prüfen / anlegen
new_fields = [
    QgsField("flag_native_ecoregion", QVariant.Int),
    QgsField("flag_riparian_keyword", QVariant.Int),
    QgsField("flag_elevation_valid", QVariant.Int),
    QgsField("flag_river_corridor_box", QVariant.Int),
    QgsField("flag_high_confidence_native", QVariant.Int)
]

existing_field_names = layer.fields().names()
fields_to_add = [f for f in new_fields if f.name() not in existing_field_names]

if fields_to_add:
    provider.addAttributes(fields_to_add)
    layer.updateFields()

# Indizes abrufen
idx_ecoregion = layer.fields().indexOf("flag_native_ecoregion")
idx_keyword = layer.fields().indexOf("flag_riparian_keyword")
idx_elevation = layer.fields().indexOf("flag_elevation_valid")
idx_corridor = layer.fields().indexOf("flag_river_corridor_box")
idx_high_conf = layer.fields().indexOf("flag_high_confidence_native")

# Quellspalten
idx_habitat = layer.fields().indexOf("habitat")
idx_locality = layer.fields().indexOf("locality")
idx_occ_remarks = layer.fields().indexOf("occurrenceRemarks")
idx_event_remarks = layer.fields().indexOf("eventRemarks")
idx_min_elev = layer.fields().indexOf("minimumElevationInMeters")
idx_max_elev = layer.fields().indexOf("maximumElevationInMeters")
idx_outside = layer.fields().indexOf("flag_outside_native_range")

# Mehrsprachige Fluss- & Auenbegriffe inkl. BALKAN-Systemen
riparian_keywords = [
    # Allgemeine Fachbegriffe
    "fluss", "aue", "kies", "sand", "ufer", "wildfluss", "schotter", "umlagerung", 
    "river", "floodplain", "gravel", "sandbar", "riparian", "alluvial", "stream",
    "rivière", "grève", "alluvion", "lit", "torrent", "berge",
    "fiume", "grave", "fiumara", "alveo", "gretto", "reka", "rijeka", "reka",
    
    # Alpen- & Mitteleuropa-Korridore
    "lech", "rhein", "inn", "isar", "drau", "salzach", "rhone", "rhône", "durance", 
    "isère", "tagliamento", "piave", "brenta", "po", "enns", "mur",
    
    # BALKAN- & SÜDOSTEUROPA-Korridore
    "sava", "savus", "drina", "neretva", "vjosa", "aoos", "vardar", "axios", 
    "struma", "strymon", "mesta", "nestos", "morava", "una", "vrbas", "morača", 
    "moraca", "dunav", "danube", "balkan", "dinaric", "pindus", "rhodope",
    
    # Kaukasus & Anatolien
    "kaukasus", "caucasus", "terek", "rioni", "kura"
]

# Räumliche Bounding Boxen inkl. BALKAN (WGS84: Lon_Min, Lat_Min, Lon_Max, Lat_Max)
river_corridors = {
    "Alpenflüsse_West_Zentral": (5.5, 43.5, 12.0, 48.5),    # Rhône, Durance, Isère, Rhein, Inn, Lech, Isar
    "Alpenflüsse_Ost_Süd": (11.5, 45.5, 16.5, 48.0),         # Tagliamento, Piave, Drau, Salzach, Enns
    "Balkan_Dinariden_Aegaeis": (13.0, 37.0, 26.5, 46.0),    # Sava, Drina, Neretva, Vjosa, Vardar, Struma, Morava
    "Kaukasus_Anatolien": (27.0, 37.0, 50.0, 44.5),          # Kaukasische & Nord-Anatolische Flussläufe
    "Pyrenäen_Ebro": (-2.5, 41.5, 3.0, 43.5)                 # Pyrenäenvorland & Ebro-Einzugsgebiet
}

layer.startEditing()

for feature in layer.getFeatures():
    f_ecoregion = 0
    f_keyword = 0
    f_elevation = 0
    f_corridor = 0
    
    geom = feature.geometry()
    
    # CHECK A: Text-Mining über Freitextfelder (inkl. Balkan-Keywords)
    text_content = ""
    for idx in [idx_habitat, idx_locality, idx_occ_remarks, idx_event_remarks]:
        if idx != -1 and feature.attribute(idx) is not None:
            text_content += " " + str(feature.attribute(idx)).lower()
            
    if any(kw in text_content for kw in riparian_keywords):
        f_keyword = 1

    # CHECK B: Höhenstufen-Plausibilität (100 m - 1600 m)
    elev_val = None
    if idx_min_elev != -1 and feature.attribute(idx_min_elev) is not None:
        elev_val = feature.attribute(idx_min_elev)
    elif idx_max_elev != -1 and feature.attribute(idx_max_elev) is not None:
        elev_val = feature.attribute(idx_max_elev)
        
    if elev_val is not None:
        try:
            e = float(elev_val)
            if 100.0 <= e <= 1600.0:
                f_elevation = 1
        except (ValueError, TypeError):
            pass

    # CHECK C: Bounding-Boxen & Ecoregionen (Südgrenze erweitert auf 37° N für den Balkan)
    if geom and not geom.isEmpty():
        pt = geom.asPoint()
        lon, lat = pt.x(), pt.y()
        
        # Makro-Ecoregion eurasischer Gebirge (Südgrenze auf 37.0° N angepasst)
        if (5.0 <= lon <= 50.0 and 37.0 <= lat <= 49.0) or (-2.5 <= lon <= 3.0 and 41.5 <= lat <= 43.5):
            f_ecoregion = 1
            
        # Schlüssel-Flusskorridore
        for c_name, (xmin, ymin, xmax, ymax) in river_corridors.items():
            if xmin <= lon <= xmax and ymin <= lat <= ymax:
                f_corridor = 1
                break

    # CHECK D: High-Confidence Native Status
    out_range = feature.attribute(idx_outside) if idx_outside != -1 else 0
    out_val = int(out_range) if (out_range is not None and str(out_range).isdigit()) else 0
    
    score = f_ecoregion + f_keyword + f_elevation + f_corridor
    f_high_conf = 1 if (out_val == 0 and score >= 2) else 0

    # Werte schreiben
    feature.setAttribute(idx_ecoregion, f_ecoregion)
    feature.setAttribute(idx_keyword, f_keyword)
    feature.setAttribute(idx_elevation, f_elevation)
    feature.setAttribute(idx_corridor, f_corridor)
    feature.setAttribute(idx_high_conf, f_high_conf)
    
    layer.updateFeature(feature)

layer.commitChanges()
print("Skript fehlerfrei ausgeführt: Balkan-Vorkommen und Dinarische Flusssysteme voll integriert!")