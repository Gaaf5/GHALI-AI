from app.brain.brain import Brain


def test_percent_of_quantity_is_not_misreported_as_mass_percent():
    brain = Brain.__new__(Brain)
    assert brain._try_tool("mass_percent", "what is 5% of 200 kg") is None


def test_date_question_is_not_sent_to_mass_percent_parser():
    brain = Brain.__new__(Brain)
    assert brain._try_tool("mass_percent", "what happened on 2026-10-13") is None
