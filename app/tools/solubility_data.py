"""Source-backed aqueous solubility data for the GHALI Virtual Lab.

Basis: grams of solute per 100 g H2O unless noted otherwise.
Rule: interpolate only between supplied points; never extrapolate outside the
source temperature range.  These are single-solute reference equilibria, not
multicomponent fertilizer-solution predictions.
"""

SOURCE_SOLUBILITY_CURVES = {
    "urea": {"points":[(0,67.0),(20,105.0),(40,163.0),(60,246.0),(80,396.0),(100,725.0),(110,1164.0)], "quality":"A - industry handbook", "source":"Fertilizers Europe/Yara guidance (IUPAC-referenced urea curve)", "url":"https://www.fertilizerseurope.com/wp-content/uploads/2007/08/Final-version-Storage-handling-and-transport-of-solid-fertilizers-18112015.pdf"},
    "map": {"points":[(0,22.7),(20,32.8),(25,40.4)], "quality":"A/B - fertilizer handbook + EPA", "source":"Fertilizers Europe at 20 °C; US EPA/NCBI at 25 °C", "url":"https://www.fertilizerseurope.com/wp-content/uploads/2007/08/Final-version-Storage-handling-and-transport-of-solid-fertilizers-18112015.pdf"},
    "dap": {"points":[(0,42.9),(20,58.8),(25,69.5)], "quality":"A/B - fertilizer handbook + EPA", "source":"Fertilizers Europe at 0/20 °C; US EPA/NCBI at 25 °C", "url":"https://www.fertilizerseurope.com/wp-content/uploads/2007/08/Final-version-Storage-handling-and-transport-of-solid-fertilizers-18112015.pdf"},
    "mkp": {"points":[(0,14.8),(10,18.3),(20,22.6),(30,28.0),(40,33.5)], "quality":"A - manufacturer technical data", "source":"Haifa MKP technical solubility table", "url":"https://www.haifa-group.com/haifa-mkp%E2%84%A2-mono-potassium-phosphate-0-52-34"},
    "sop": {"points":[(0,7.4),(10,9.3),(20,11.1),(30,13.0),(40,14.8),(50,16.5),(60,18.2),(70,19.8),(80,21.4),(90,22.9),(100,24.1)], "quality":"A - fertilizer industry reference", "source":"Fertilizers Europe SOP solubility data", "url":"https://www.fertilizerseurope.com/wp-content/uploads/2007/08/Final-version-Storage-handling-and-transport-of-solid-fertilizers-18112015.pdf"},
    "nop": {"points":[(0,13.3),(20,31.6),(40,63.9),(60,110.0),(80,169.0),(100,246.0)], "quality":"A - fertilizer industry reference", "source":"Fertilizers Europe potassium nitrate solubility table", "url":"https://www.fertilizerseurope.com/wp-content/uploads/2007/08/Final-version-Storage-handling-and-transport-of-solid-fertilizers-18112015.pdf"},
    "ammonium_nitrate": {"points":[(20,194.0),(40,274.0),(60,405.0),(80,609.0),(100,1011.0),(120,1786.0),(140,3746.0)], "quality":"A - fertilizer industry reference", "source":"Fertilizers Europe/Yara AN solubility table", "url":"https://www.fertilizerseurope.com/wp-content/uploads/2007/08/Final-version-Storage-handling-and-transport-of-solid-fertilizers-18112015.pdf"},
    "potassium_chloride": {"points":[(0,27.6),(10,31.0),(20,34.0),(30,37.0),(40,40.0),(50,42.6),(60,45.5),(80,51.1),(100,56.7)], "quality":"B - reference table", "source":"Standard aqueous KCl solubility table; ILO/WHO confirms water solubility at 20 °C", "url":"https://inchem.org/documents/icsc/icsc/eics1450.htm"},
    "ammonium_sulfate": {"points":[(10,72.7),(20,75.4),(40,81.2),(60,87.4),(80,94.1),(100,103.3),(125,113.7),(150,124.7)], "quality":"A - fertilizer industry reference", "source":"Fertilizers Europe/Yara ammonium sulfate solubility table", "url":"https://www.fertilizerseurope.com/wp-content/uploads/2007/08/Final-version-Storage-handling-and-transport-of-solid-fertilizers-18112015.pdf"},
    "magnesium_sulfate": {"points":[(20,71.0),(40,91.0)], "quality":"B - hydrate-specific reference", "source":"Magnesium sulfate heptahydrate reference data; hydrate identity matters", "url":"https://pubchem.ncbi.nlm.nih.gov/compound/magnesium-sulfate"},
    "calcium_nitrate": {"points":[(0,102.0),(10,115.0),(20,129.0),(30,152.0),(40,191.0),(80,358.0),(100,363.0)], "quality":"B - hydrate-specific reference", "source":"Calcium nitrate tetrahydrate reference data; values are commonly reported per 100 mL water", "url":"https://www.sciencemadness.org/smwiki/index.php/Calcium_nitrate"},
    "calcium_chloride": {"points":[(20,74.5),(25,81.3)], "quality":"B - reference data", "source":"ICSC/CRC-reported calcium chloride solubility; hydrate form can materially change behavior", "url":"https://pubchem.ncbi.nlm.nih.gov/compound/Calcium-Chloride"},
    "magnesium_nitrate": {"points":[(0,62.1),(10,66.0),(20,69.5),(30,73.6),(40,78.9),(80,91.6),(90,106.0)], "quality":"B - reference table", "source":"Magnesium nitrate aqueous solubility table; hydrate identity must be specified for precision", "url":"https://www.chemicalaid.com/tools/solubility.php?substance=Mg%28NO3%292"},
    "citric_acid": {"points":[(10,54.0),(20,59.2),(30,64.3),(40,68.6),(50,70.9),(60,73.5),(70,76.2),(80,78.8),(90,81.4),(100,84.0)], "quality":"A/B - handbook/HSDB", "source":"Merck/HSDB data reported by PubChem", "url":"https://pubchem.ncbi.nlm.nih.gov/compound/Citric-Acid"},
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
    return {"value_g_per_100g_water":value,"quality":curve["quality"],"source":curve["source"],"url":curve["url"],"temperature_range_c":[curve["points"][0][0],curve["points"][-1][0]],"basis":"g solute / 100 g H2O"}

__all__=["SOURCE_SOLUBILITY_CURVES","aqueous_solubility"]