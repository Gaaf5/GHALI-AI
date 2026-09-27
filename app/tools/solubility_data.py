"""Source-backed aqueous solubility data for the GHALI virtual lab.
Basis: grams of solute per 100 g H2O unless explicitly noted.
Only interpolation between supplied reference points is allowed.
"""

SOURCE_SOLUBILITY_CURVES = {
    "urea": {"points":[(0,67.0),(20,105.0),(40,163.0),(60,246.0),(80,396.0),(100,725.0)], "quality":"industrial reference", "source":"Fertilizers Europe / Yara solid mineral fertilizer guidance", "url":"https://www.fertilizerseurope.com/wp-content/uploads/2007/08/Final-version-Storage-handling-and-transport-of-solid-fertilizers-18112015.pdf"},
    "map": {"points":[(0,22.7),(10,29.5),(20,37.1),(30,46.4),(40,56.7)], "quality":"fertilizer product data", "source":"Haifa MAP water-solubility data", "url":"https://www.haifa-group.com/haifa-map%E2%84%A2-mono-ammonium-phosphate-12-61"},
    "dap": {"points":[(0,42.9),(20,58.8),(25,69.5)], "quality":"industrial reference + handbook", "source":"Fertilizers Europe; PubChem/CRC at 25 °C", "url":"https://www.fertilizerseurope.com/wp-content/uploads/2007/08/Final-version-Storage-handling-and-transport-of-solid-fertilizers-18112015.pdf"},
    "mkp": {"points":[(0,14.8),(10,18.3),(20,22.6),(30,28.0),(40,33.5)], "quality":"fertilizer product data", "source":"Haifa MKP water-solubility data", "url":"https://www.haifa-group.com/haifa-mkp%E2%84%A2-mono-potassium-phosphate-0-52-34"},
    "sop": {"points":[(0,7.4),(10,9.3),(20,11.1),(30,13.0),(40,14.8),(60,18.2),(80,21.4),(90,22.9),(100,24.1)], "quality":"handbook/reference", "source":"Potassium sulfate solubility tables; PubChem confirms 12 g/100 mL at 25 °C", "url":"https://pubchem.ncbi.nlm.nih.gov/compound/Potassium-sulfate"},
    "nop": {"points":[(0,13.3),(10,21.0),(20,31.6),(30,45.8),(40,63.9),(50,85.5),(60,110.0),(80,169.0),(100,246.0)], "quality":"industrial reference", "source":"Fertilizers Europe potassium nitrate data", "url":"https://www.fertilizerseurope.com/wp-content/uploads/2007/08/Final-version-Storage-handling-and-transport-of-solid-fertilizers-18112015.pdf"},
    "ammonium_nitrate": {"points":[(20,194.0),(40,274.0),(60,405.0),(80,609.0),(100,1011.0)], "quality":"industrial reference", "source":"Fertilizers Europe AN solubility table", "url":"https://www.fertilizerseurope.com/wp-content/uploads/2007/08/Final-version-Storage-handling-and-transport-of-solid-fertilizers-18112015.pdf"},
    "potassium_chloride": {"points":[(0,27.6),(10,31.0),(20,34.0),(30,37.0),(40,40.0),(50,42.6),(60,45.5),(80,51.1),(100,56.7)], "quality":"reference table", "source":"Standard KCl solubility table", "url":"https://zpe.gov.pl/a/solubility-of-substances---solubility-and-solubility-curves/D1FmD3Itj"},
    "ammonium_sulfate": {"points":[(0,70.6),(10,72.7),(20,75.4),(30,78.1),(40,81.2),(50,84.3),(60,87.4),(80,94.1),(100,103.3)], "quality":"industrial reference", "source":"Fertilizers Europe ammonium sulfate solubility table", "url":"https://www.fertilizerseurope.com/wp-content/uploads/2007/08/Final-version-Storage-handling-and-transport-of-solid-fertilizers-18112015.pdf"},
    "magnesium_sulfate": {"points":[(20,71.0),(40,91.0)], "quality":"hydrate-specific reference", "source":"Magnesium sulfate heptahydrate reference data; hydrate identity matters", "url":"https://pubchem.ncbi.nlm.nih.gov/compound/magnesium-sulfate"},
    "calcium_nitrate": {"points":[(0,105.0),(20,129.0),(100,363.0)], "quality":"hydrate-specific reference", "source":"Calcium nitrate tetrahydrate reference data", "url":"https://www.sciencemadness.org/smwiki/index.php/Calcium_nitrate"},
    "calcium_chloride": {"points":[(20,74.5),(25,81.3)], "quality":"reference data", "source":"ICSC/CRC values; hydrate form can materially change solubility", "url":"https://pubchem.ncbi.nlm.nih.gov/compound/Calcium-Chloride"},
    "magnesium_nitrate": {"points":[(25,71.2)], "quality":"reference data", "source":"PubChem reference for magnesium nitrate; hydrate form must be specified for precision", "url":"https://pubchem.ncbi.nlm.nih.gov/compound/Magnesium-nitrate"},
    "citric_acid": {"points":[(10,54.0),(20,59.2),(30,64.3),(40,68.6),(50,70.9),(60,73.5),(70,76.2),(80,78.8),(90,81.4),(100,84.0)], "quality":"handbook reference", "source":"Merck/HSDB data reported by PubChem", "url":"https://pubchem.ncbi.nlm.nih.gov/compound/Citric-Acid"},
}


def interpolate_curve(curve: dict, temp_c: float):
    points=curve["points"]
    if temp_c < points[0][0] or temp_c > points[-1][0]:
        return None
    for (t0,v0),(t1,v1) in zip(points,points[1:]):
        if t0 <= temp_c <= t1:
            if t1 == t0:
                return float(v0)
            f=(temp_c-t0)/(t1-t0)
            return float(v0+(v1-v0)*f)
    return float(points[-1][1])


def aqueous_solubility(material: str, temp_c: float):
    curve=SOURCE_SOLUBILITY_CURVES.get(material)
    if not curve:
        return None
    value=interpolate_curve(curve,temp_c)
    if value is None:
        return None
    return {"value_g_per_100g_water":value,"quality":curve["quality"],"source":curve["source"],"url":curve["url"],"temperature_range_c":[curve["points"][0][0],curve["points"][-1][0]]}

__all__=["SOURCE_SOLUBILITY_CURVES","aqueous_solubility"]
