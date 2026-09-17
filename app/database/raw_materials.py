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
    RawMaterial("urea phosphate", 17.0, 44.0),
    RawMaterial("bentonite"),
    RawMaterial("xanthan gum"),
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
    return len(DEFAULT_RAW_MATERIALS)
