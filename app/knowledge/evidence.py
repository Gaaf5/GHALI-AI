"""Evidence registry for the GHALI Chemical Intelligence Laboratory.

Numbers used by the lab should carry provenance: source, URL, evidence class,
temperature/range, basis, and any product-grade limitations.
"""
from __future__ import annotations
from urllib.parse import urlparse

SOURCE_REGISTRY = {
    "IUPAC_NIST_SDS": {"name":"IUPAC-NIST Solubility Data Series","class":"primary_critical","confidence":"HIGH","scope":"critically evaluated solubility literature and multicomponent systems","url":"https://srdata.nist.gov/solubility/intro.aspx"},
    "NIST_WEBBOOK": {"name":"NIST Chemistry WebBook","class":"primary_reference","confidence":"HIGH","scope":"thermochemical and thermophysical reference data","url":"https://webbook.nist.gov/chemistry/"},
    "NIST_GAMPHI": {"name":"NIST GAMPHI","class":"primary_reference","confidence":"HIGH","scope":"activity and osmotic coefficients for aqueous electrolyte solutions","url":"https://www.nist.gov/publications/gamphi-database-activity-and-osmotic-coefficients-aqueous-electrolyte-solutions"},
    "USGS_PHREEQC": {"name":"USGS PHREEQC Version 3","class":"validated_model","confidence":"HIGH","scope":"speciation, saturation, batch reactions, SIT and Pitzer activity models","url":"https://www.usgs.gov/software/phreeqc-version-3"},
    "PUBCHEM": {"name":"PubChem","class":"curated_reference","confidence":"HIGH","scope":"chemical identity and compiled physical/solubility properties","url":"https://pubchem.ncbi.nlm.nih.gov/"},
    "MANUFACTURER_TDS": {"name":"Manufacturer technical data","class":"product_specific","confidence":"MEDIUM","scope":"product-grade solubility/composition; must match exact grade","url":""},
    "FERTILIZERS_EUROPE": {"name":"Fertilizers Europe technical guidance","class":"industry_reference","confidence":"MEDIUM_HIGH","scope":"fertilizer solubility and handling data","url":"https://www.fertilizerseurope.com/"},
    "HAIFA": {"name":"Haifa Group technical data","class":"manufacturer_industry","confidence":"MEDIUM_HIGH","scope":"fertilizer product solubility and compatibility guidance","url":"https://www.haifa-group.com/"},
    "OTHER_PUBLISHED": {"name":"Published/compiled reference","class":"secondary_reference","confidence":"MEDIUM","scope":"published data requiring source-specific review","url":""},
}

DOMAIN_SOURCE = {
    "srdata.nist.gov":"IUPAC_NIST_SDS",
    "webbook.nist.gov":"NIST_WEBBOOK",
    "water.usgs.gov":"USGS_PHREEQC",
    "usgs.gov":"USGS_PHREEQC",
    "nist.gov":"NIST_GAMPHI",
    "pubchem.ncbi.nlm.nih.gov":"PUBCHEM",
    "fertilizerseurope.com":"FERTILIZERS_EUROPE",
    "haifa-group.com":"HAIFA",
}

def source_id_for_url(url: str | None, product_specific: bool = False) -> str | None:
    if product_specific:
        return "MANUFACTURER_TDS"
    if not url:
        return None
    host=urlparse(url).netloc.lower().split(":",1)[0]
    for domain, source_id in DOMAIN_SOURCE.items():
        if host == domain or host.endswith("."+domain):
            return source_id
    return "OTHER_PUBLISHED"

def evidence_for(url: str | None, *, quality: str | None = None,
                 basis: str | None = None, temperature_c: float | None = None,
                 temperature_range_c=None, product_specific: bool = False,
                 limitation: str | None = None) -> dict:
    sid=source_id_for_url(url, product_specific=product_specific)
    src=dict(SOURCE_REGISTRY.get(sid or "OTHER_PUBLISHED", SOURCE_REGISTRY["OTHER_PUBLISHED"]))
    if url: src["url"]=url
    out={"source_id":sid,"source_name":src["name"],"evidence_class":src["class"],
         "confidence":src["confidence"],"source_url":src.get("url","")}
    if quality: out["quality"]=quality
    if basis: out["basis"]=basis
    if temperature_c is not None: out["temperature_c"]=temperature_c
    if temperature_range_c is not None: out["temperature_range_c"]=list(temperature_range_c)
    if limitation: out["limitation"]=limitation
    return out


def registry() -> list[dict]:
    return [{"id":k,**v} for k,v in SOURCE_REGISTRY.items()]
