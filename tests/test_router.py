from app.brain.router import classify
from app.tools.registry import load_defaults


load_defaults()


def test_tool_routes():
    assert classify("calculate molar mass of H2O").tool_name == "molar_mass"
    assert classify("calculate NPK for this fertilizer").tool_name == "npk_grade_from_compounds"
    assert classify("what is dilution C1 V1 V2?").tool_name == "dilution_c1v1_to_v2"


def test_chat_route():
    assert classify("explain why urea is widely used").kind == "chat"
