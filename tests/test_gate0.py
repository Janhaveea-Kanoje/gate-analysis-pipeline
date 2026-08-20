from src.gates.gate0_formulation import (
    ExtractedIngredient, check_form_quality, check_dosage_adequacy,
    check_formulation_logic, check_transparency,
)


def test_magnesium_oxide_rejected():
    ing = ExtractedIngredient(name="Magnesium", form="Oxide", amount=400, unit="mg")
    ok, msg = check_form_quality(ing)
    assert ok is False
    assert "rejected" in msg.lower()


def test_magnesium_bisglycinate_passes():
    ing = ExtractedIngredient(name="Magnesium", form="Bisglycinate", amount=400, unit="mg")
    ok, msg = check_form_quality(ing)
    assert ok is True


def test_fairy_dusting_fails():
    ing = ExtractedIngredient(name="Magnesium", form="Bisglycinate", amount=50, unit="mg")
    ok, msg = check_dosage_adequacy(ing, population="adult")
    assert ok is False
    assert "fairy-dusting" in msg.lower()


def test_adequate_dose_passes():
    ing = ExtractedIngredient(name="Magnesium", form="Bisglycinate", amount=350, unit="mg")
    ok, msg = check_dosage_adequacy(ing, population="adult")
    assert ok is True


def test_fat_soluble_vitamin_without_lipid_fails():
    ing = [ExtractedIngredient(name="Vitamin D", form="Cholecalciferol (D3)", amount=2000, unit="IU")]
    ok, msg = check_formulation_logic(ing, has_lipid_carrier=False)
    assert ok is False
    assert "lipid" in msg.lower()


def test_proprietary_blend_fails_transparency():
    ok, msg = check_transparency(has_proprietary_blend=True, all_amounts_declared=False)
    assert ok is False
