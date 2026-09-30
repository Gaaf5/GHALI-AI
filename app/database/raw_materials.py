from .database import Database
from .models import RawMaterial


DEFAULT_RAW_MATERIALS = (
    RawMaterial("urea", 46.0),
    RawMaterial("map", 12.0, 61.0),
    RawMaterial("mkp", 0.0, 52.0, 34.0),
    RawMaterial("sop", 0.0, 0.0, 50.0),
    RawMaterial("nop", 13.5, 0.0, 46.0),
    RawMaterial("potassium nitrate", 13.5, 0.0, 46.0),
    RawMaterial("ammonium nitrate", 34.0),
    RawMaterial("ammonium sulfate", 21.0),
    RawMaterial("ammonium sulfite", 0.0),
    RawMaterial("urea phosphate", 17.0, 44.0),
    RawMaterial("bentonite"),
    RawMaterial("xanthan gum"),
    RawMaterial("TE-MIX"),
)

ALIASES = {
    "urea": ["يوريا", "اليوريا"], "map": ["ماب", "اماب"],
    "mkp": ["ام كي بي", "MKP"], "sop": ["سوب", "كبريتات البوتاسيوم", "كبريتات بوتاسيوم"],
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
        "nop": {"n_nitrate_pct":13.5},
        "potassium nitrate": {"n_nitrate_pct":13.5},
        "ammonium nitrate": {"n_nitrate_pct":17.0,"n_ammoniacal_pct":17.0},
        "ammonium sulfate": {"n_ammoniacal_pct":21.0,"s_pct":23.5},
        "ammonium sulfite": {"s_pct":24.0},
        "urea phosphate": {"n_urea_pct":17.0},
        "TE-MIX": {},
    }
    for name,meta in forms.items():
        row=db.resolve_raw_material(name)
        if row:
            db.upsert_raw_material(
                name,row["n_pct"],row["p2o5_pct"],row["k2o_pct"],
                row.get("moisture_pct"),row.get("assay_pct"),row.get("source","project"),
                bool(row.get("active",1)),**meta
            )
    return len(DEFAULT_RAW_MATERIALS)

def ensure_extended_nutrient_metadata(db: Database) -> None:
    """Add nutrient-form materials/metadata without overwriting user NPK data."""
    db.create_tables()
    for name in ("ammonium sulfite", "TE-MIX"):
        if not db.get_raw_material(name):
            db.upsert_raw_material(name, source="project")
    metadata={
        "urea":(0,0,46.0,0),
        "map":(0,12.0,0,0),
        "sop":(0,0,0,18.0),
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
    db.connection.commit()
