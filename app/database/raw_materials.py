import json

from .database import Database
from .models import RawMaterial


DEFAULT_RAW_MATERIALS = (
    RawMaterial("urea", 46.0),
    RawMaterial("map", 12.0, 61.0),
    RawMaterial("mkp", 0.0, 52.0, 34.0),
    RawMaterial("sop", 0.0, 0.0, 50.0),
    RawMaterial("KCl (0-0-60)", 0.0, 0.0, 60.0),
    RawMaterial("Magnesium 33%", 0.0, 0.0, 0.0),
    RawMaterial("nop", 13.5, 0.0, 46.0),
    RawMaterial("potassium nitrate", 13.5, 0.0, 46.0),
    RawMaterial("ammonium nitrate", 34.0),
    RawMaterial("ammonium sulfate", 21.0),
    RawMaterial("urea phosphate", 17.0, 44.0),
    RawMaterial("TE-MIX"),
    # Inert functional ingredients used in suspension/paste formulations.
    RawMaterial("bentonite", source="project"),
    RawMaterial("xanthan gum", source="project"),
)

ALIASES = {
    "urea": ["يوريا", "اليوريا"], "map": ["ماب", "اماب"],
    "mkp": ["ام كي بي", "MKP"], "sop": ["سوب", "كبريتات البوتاسيوم", "كبريتات بوتاسيوم"],
    "KCl (0-0-60)": ["KCl", "كلوريد البوتاسيوم", "كلوريد بوتاسيوم", "MOP"],
    "Magnesium 33%": ["مغنيسيوم 33%", "Magnesium 33"],
    "nop": ["نوب"], "potassium nitrate": ["kno3", "نترات البوتاسيوم", "نترات بوتاسيوم"],
    "ammonium nitrate": ["نترات الأمونيوم", "نترات الامونيوم"],
    "ammonium sulfate": ["(nh4)2so4", "كبريتات الأمونيوم", "كبريتات الامونيوم"],
    "urea phosphate": ["فوسفات اليوريا", "يوريا فوسفيت"],
    "bentonite": ["بنتونايت", "بنتونيت"],
    "xanthan gum": ["زانثان", "صمغ الزانثان"],
}


def seed_default_raw_materials(db: Database) -> int:
    db.create_tables()
    for material in DEFAULT_RAW_MATERIALS:
        # Seed only missing records. Re-running startup must never reset a user's
        # edited nutrient analysis, assay, moisture, active flag, or source.
        if not db.get_raw_material(material.name):
            db.upsert_raw_material(
                material.name, material.n_pct, material.p2o5_pct, material.k2o_pct,
                material.moisture_pct, material.assay_pct, material.source, material.active
            )
        for alias in ALIASES.get(material.name, []):
            db.add_raw_material_alias(material.name, alias)
    # Nutrient-form metadata is stored as absolute product percentages of N.
    # Thus 13.5% nitrate-N in KNO3 means all 13.5% of product N is nitrate-N.
    forms = {
        "urea": {"n_urea_pct":46.0},
        "map": {"n_ammoniacal_pct":12.0},
        "mkp": {},
        "sop": {"s_pct":18.0},
        "KCl (0-0-60)": {"chlorine_pct":47.3},
        "Magnesium 33%": {"mg_pct":33.0,"s_pct":18.5},
        "nop": {"n_nitrate_pct":13.5},
        "potassium nitrate": {"n_nitrate_pct":13.5},
        "ammonium nitrate": {"n_nitrate_pct":17.0,"n_ammoniacal_pct":17.0},
        "ammonium sulfate": {"n_ammoniacal_pct":21.0,"s_pct":23.5},
        "ammonium sulfite": {"s_pct":24.0},
        "urea phosphate": {"n_urea_pct":17.0},
        # Trace-element composition is stored exactly as supplied by the project,
        # expressed as % of TE-MIX product. Therefore 1 kg TE-MIX contains:
        # B 0.80 g, Cu 2.60 g, Fe 5.10 g, Mn 2.60 g, Zn 2.60 g, Mo 0.05 g.
        "TE-MIX": {
            "trace_elements": {
                "B": 0.080,
                "Cu-EDTA": 0.260,
                "Fe-EDTA": 0.510,
                "Mn-EDTA": 0.260,
                "Zn-EDTA": 0.260,
                "Mo": 0.005,
            }
        },
    }
    for name,meta in forms.items():
        row=db.resolve_raw_material(name)
        if row:
            # Fill missing nutrient-form metadata only. Existing non-zero values,
            # assay, moisture and user-defined trace analysis take precedence.
            safe_meta={}
            for field,value in meta.items():
                if field=="trace_elements":
                    try:
                        existing=json.loads(row.get("trace_elements_json") or "{}")
                    except (TypeError,ValueError):
                        existing={}
                    safe_meta[field]=existing if existing else value
                else:
                    current=row.get(field)
                    safe_meta[field]=current if current not in (None,0,0.0) else value
            db.upsert_raw_material(
                name,row["n_pct"],row["p2o5_pct"],row["k2o_pct"],
                row.get("moisture_pct"),row.get("assay_pct"),row.get("source","project"),
                bool(row.get("active",1)),
                s_pct=safe_meta.get("s_pct",row.get("s_pct",0)) or 0,
                n_nitrate_pct=safe_meta.get("n_nitrate_pct",row.get("n_nitrate_pct",0)) or 0,
                n_ammoniacal_pct=safe_meta.get("n_ammoniacal_pct",row.get("n_ammoniacal_pct",0)) or 0,
                n_urea_pct=safe_meta.get("n_urea_pct",row.get("n_urea_pct",0)) or 0,
                trace_elements=safe_meta.get("trace_elements",{}),
                mg_pct=safe_meta.get("mg_pct",row.get("mg_pct",0)) or 0,
                chlorine_pct=safe_meta.get("chlorine_pct",row.get("chlorine_pct",0)) or 0,
            )
    return len(DEFAULT_RAW_MATERIALS)

def ensure_extended_nutrient_metadata(db: Database) -> None:
    """Add nutrient-form materials/metadata without overwriting user NPK data."""
    db.create_tables()
    # Startup metadata maintenance must be additive: never delete user-managed
    # raw materials or aliases during application startup.
    # Restore functional suspension aids on existing databases where an older
    # startup migration may have removed them. These are inert, not nutrient sources.
    for name in ("bentonite", "xanthan gum"):
        if not db.get_raw_material(name):
            db.upsert_raw_material(name, 0, 0, 0, source="project")
            for alias in ALIASES.get(name, []):
                db.add_raw_material_alias(name, alias)

    if not db.get_raw_material("TE-MIX"):
        db.upsert_raw_material("TE-MIX", source="project")
    if not db.get_raw_material("KCl (0-0-60)"):
        db.upsert_raw_material("KCl (0-0-60)", 0, 0, 60, source="project", chlorine_pct=47.3)
        for alias in ALIASES["KCl (0-0-60)"]:
            db.add_raw_material_alias("KCl (0-0-60)", alias)
    if not db.get_raw_material("Magnesium 33%"):
        db.upsert_raw_material("Magnesium 33%", 0, 0, 0, source="project", s_pct=18.5, mg_pct=33.0)
        for alias in ALIASES["Magnesium 33%"]:
            db.add_raw_material_alias("Magnesium 33%", alias)
    if not db.get_raw_material("potassium nitrate"):
        db.upsert_raw_material("potassium nitrate", 13.5, 0, 46.0, source="project", n_nitrate_pct=13.5)
        for alias in ALIASES["potassium nitrate"]:
            db.add_raw_material_alias("potassium nitrate", alias)
    metadata={
        "urea":(0,0,46.0,0),
        "map":(0,12.0,0,0),
        "sop":(0,0,0,18.0),
        "KCl (0-0-60)":(0,0,0,0),
        "Magnesium 33%":(0,0,0,18.5),
        "nop":(13.5,0,0,0),
        "potassium nitrate":(13.5,0,0,0),
        "ammonium nitrate":(17.0,17.0,0,0),
        "ammonium sulfate":(0,21.0,0,23.5),
        "ammonium sulfite":(0,0,0,24.0),
        "urea phosphate":(0,0,17.0,0),
    }
    for name,(nn,na,nu,s) in metadata.items():
        row=db.get_raw_material(name)
        if not row: continue
        db.cursor.execute(
            """UPDATE raw_materials SET
               n_nitrate_pct=CASE WHEN n_nitrate_pct=0 THEN ? ELSE n_nitrate_pct END,
               n_ammoniacal_pct=CASE WHEN n_ammoniacal_pct=0 THEN ? ELSE n_ammoniacal_pct END,
               n_urea_pct=CASE WHEN n_urea_pct=0 THEN ? ELSE n_urea_pct END,
               s_pct=CASE WHEN s_pct=0 THEN ? ELSE s_pct END
               WHERE id=?""",
            (nn,na,nu,s,row["id"])
        )

    # Legacy rows may need missing defaults restored. Never replace non-zero
    # user-entered assay values during startup.
    kcl=db.get_raw_material("KCl (0-0-60)")
    if kcl:
        db.cursor.execute("""UPDATE raw_materials SET
            k2o_pct=CASE WHEN k2o_pct=0 THEN 60 ELSE k2o_pct END,
            chlorine_pct=CASE WHEN chlorine_pct=0 THEN 47.3 ELSE chlorine_pct END
            WHERE id=?""", (kcl["id"],))
    mg=db.get_raw_material("Magnesium 33%")
    if mg:
        db.cursor.execute("""UPDATE raw_materials SET
            s_pct=CASE WHEN s_pct=0 THEN 18.5 ELSE s_pct END,
            mg_pct=CASE WHEN mg_pct=0 THEN 33.0 ELSE mg_pct END
            WHERE id=?""", (mg["id"],))
    kno3=db.get_raw_material("potassium nitrate")
    if kno3:
        db.cursor.execute("""UPDATE raw_materials SET
            n_pct=CASE WHEN n_pct=0 THEN 13.5 ELSE n_pct END,
            k2o_pct=CASE WHEN k2o_pct=0 THEN 46 ELSE k2o_pct END,
            n_nitrate_pct=CASE WHEN n_nitrate_pct=0 THEN 13.5 ELSE n_nitrate_pct END
            WHERE id=?""", (kno3["id"],))
    # Project-supplied TE-MIX trace analysis. Keep the percentages exactly as
    # provided; they are elemental/product percentages, not ppm replacements.
    te_mix=db.get_raw_material("TE-MIX")
    if te_mix:
        db.cursor.execute(
            """UPDATE raw_materials SET trace_elements_json=?
               WHERE id=? AND (trace_elements_json IS NULL OR trace_elements_json='' OR trace_elements_json='{}')""",
            (json.dumps({
                "B":0.080,
                "Cu-EDTA":0.260,
                "Fe-EDTA":0.510,
                "Mn-EDTA":0.260,
                "Zn-EDTA":0.260,
                "Mo":0.005,
            }, ensure_ascii=False), te_mix["id"])
        )
    db.connection.commit()
