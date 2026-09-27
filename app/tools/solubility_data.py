"""Source-backed aqueous solubility data for the GHALI Virtual Lab.
Basis: grams of solute per 100 g H2O unless noted.
Interpolate only inside supplied temperature ranges; never extrapolate.
Values are single-solute equilibrium references, not mixed-fertilizer equilibria.
"""
SOURCE_SOLUBILITY_CURVES={
"urea":{"points":[(0,67),(20,105),(40,163),(60,246),(80,396),(100,725),(110,1164)],"quality":"A - Fertilizers Europe","source":"Fertilizers Europe/Yara fertilizer handling guidance","url":"https://www.fertilizerseurope.com/wp-content/uploads/2007/08/Final-version-Storage-handling-and-transport-of-solid-fertilizers-18112015.pdf"},
"map":{"points":[(0,22.7),(10,29.5),(20,37.4),(30,46.4),(40,56.7)],"quality":"A - manufacturer technical data","source":"Haifa MAP water-solubility table","url":"https://www.haifa-group.com/haifa-map%E2%84%A2-mono-ammonium-phosphate-12-61-0"},
"dap":{"points":[(0,57.5),(20,68.6),(25,69.5),(40,81.8),(60,97.6)],"quality":"A/B - Merck/NCBI reference tables","source":"Merck solubility table; EPA/NCBI confirms 69.5 g/100 g water at 25 C","url":"https://www.merckmillipore.com/HN/en/support/calculators-and-apps/solubility-table-compounds-water-temperature"},
"mkp":{"points":[(0,14.8),(10,18.3),(20,22.6),(30,28.0),(40,33.5)],"quality":"A - manufacturer technical data","source":"Haifa MKP water-solubility table","url":"https://www.haifa-group.com/haifa-mkp%E2%84%A2-mono-potassium-phosphate-0-52-34"},
"sop":{"points":[(0,7.4),(10,9.3),(20,11.1),(30,13.0),(40,14.8),(50,16.5),(60,18.2),(70,19.8),(80,21.4),(90,22.9),(100,24.1)],"quality":"A - fertilizer industry reference","source":"Fertilizers Europe SOP solubility data","url":"https://www.fertilizerseurope.com/wp-content/uploads/2007/08/Final-version-Storage-handling-and-transport-of-solid-fertilizers-18112015.pdf"},
"nop":{"points":[(0,13.3),(20,31.6),(40,63.9),(60,110),(80,169),(100,246)],"quality":"A - fertilizer industry reference","source":"Fertilizers Europe potassium nitrate table","url":"https://www.fertilizerseurope.com/wp-content/uploads/2007/08/Final-version-Storage-handling-and-transport-of-solid-fertilizers-18112015.pdf"},
"ammonium_nitrate":{"points":[(20,194),(40,274),(60,405),(80,609),(100,1011),(120,1786),(140,3746)],"quality":"A - fertilizer industry reference","source":"Fertilizers Europe ammonium nitrate table","url":"https://www.fertilizerseurope.com/wp-content/uploads/2007/08/Final-version-Storage-handling-and-transport-of-solid-fertilizers-18112015.pdf"},
"ammonium_sulfate":{"points":[(10,72.7),(20,75.4),(40,81.2),(60,87.4),(80,94.1),(100,103.3),(125,113.7),(150,124.7)],"quality":"A - fertilizer industry reference","source":"Fertilizers Europe ammonium sulfate table","url":"https://www.fertilizerseurope.com/wp-content/uploads/2007/08/Final-version-Storage-handling-and-transport-of-solid-fertilizers-18112015.pdf"},
"potassium_chloride":{"points":[(0,27.6),(10,31.0),(20,34.0),(30,37.0),(40,40.0),(50,42.6),(60,45.5),(80,51.1),(100,56.7)],"quality":"A/B - reference tables","source":"Fertilizers/fertigation reference table; Merck/PubChem confirms ~35.5 at 25 C","url":"https://pubchem.ncbi.nlm.nih.gov/compound/Potassium-chloride"},
"magnesium_sulfate":{"points":[(10,30.05),(20,35.6),(40,45.4)],"quality":"A/B - Merck hydrate-specific data","source":"Magnesium sulfate heptahydrate solubility table","url":"https://www.merckmillipore.com/HN/en/support/calculators-and-apps/solubility-table-compounds-water-temperature"},
"calcium_nitrate":{"points":[(0,101.0),(20,129.39),(40,196.0)],"quality":"A/B - Merck hydrate-specific data","source":"Calcium nitrate tetrahydrate solubility table","url":"https://www.merckmillipore.com/HN/en/support/calculators-and-apps/solubility-table-compounds-water-temperature"},
"calcium_chloride":{"points":[(0,59.5),(10,64.7),(20,74.5),(30,100),(40,128),(60,137),(80,147),(100,159)],"quality":"A/B - published aqueous data","source":"Temperature-dependent calcium chloride solubility data","url":"https://pmc.ncbi.nlm.nih.gov/articles/PMC5551734/"},
"magnesium_nitrate":{"points":[(0,63.9),(20,70.07),(40,81.8),(60,93.7)],"quality":"A/B - Merck hydrate-specific data","source":"Magnesium nitrate hexahydrate solubility table","url":"https://www.merckmillipore.com/HN/en/support/calculators-and-apps/solubility-table-compounds-water-temperature"},
"citric_acid":{"points":[(10,54.0),(20,59.2),(30,64.3),(40,68.6),(50,70.9),(60,73.5),(70,76.2),(80,78.8),(90,81.4),(100,84.0)],"quality":"A - Merck/HSDB","source":"Merck Index / HSDB values reproduced by PubChem","url":"https://pubchem.ncbi.nlm.nih.gov/compound/Citric-Acid"},
"urea_phosphate":{"points":[(20,96.0)],"quality":"B - fertilizer technical reference","source":"Approx. 960 g/L at 20 C converted to ~96 g/100 g water; corroborated by fertilizer formulation literature","url":"https://patents.google.com/patent/US8419820B2/en"},
}
def interpolate_curve(curve,temp_c):
    points=curve["points"]
    if temp_c<points[0][0] or temp_c>points[-1][0]: return None
    for (t0,v0),(t1,v1) in zip(points,points[1:]):
        if t0<=temp_c<=t1:
            return float(v0 if t1==t0 else v0+(v1-v0)*(temp_c-t0)/(t1-t0))
    return float(points[-1][1])
def aqueous_solubility(material,temp_c):
    curve=SOURCE_SOLUBILITY_CURVES.get(material)
    if not curve:return None
    value=interpolate_curve(curve,temp_c)
    if value is None:return None
    return {"value_g_per_100g_water":value,"quality":curve["quality"],"source":curve["source"],"url":curve["url"],"temperature_range_c":[curve["points"][0][0],curve["points"][-1][0]],"basis":"g solute / 100 g H2O"}
__all__=["SOURCE_SOLUBILITY_CURVES","aqueous_solubility"]
