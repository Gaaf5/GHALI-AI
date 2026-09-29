from app.tools.model_selector import select_activity_model, water_analysis_to_molal

def test_activity_model_selection():
    assert select_activity_model(0.01,True)["activity_model"]=="PHREEQC ion-association"
    assert select_activity_model(0.2,True)["activity_model"]=="SIT"
    assert select_activity_model(0.8,True)["activity_model"]=="Pitzer"
    assert select_activity_model(0.8,False)["engine"]=="screening_shared_solution"

def test_water_analysis_conversion():
    x=water_analysis_to_molal({"Ca":400,"SO4":960})
    assert abs(x["Ca"]-0.0099805)<1e-5
    assert abs(x["SO4"]-0.009994)<1e-5
