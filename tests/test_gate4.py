from src.gates.gate0_formulation import ExtractedIngredient, _FORM_TIERS
from src.gates.gate4_medical import MedicalInputs, check_evidence_alignment, check_interactions


def _inputs(ingredients, claim):
    return MedicalInputs(ingredients=ingredients, population="adult", claimed_benefit=claim,
                         cited_study_dose={}, cited_study_form={})


ZINC_PICOLINATE = ExtractedIngredient(name="Zinc", form="Picolinate", amount=15, unit="mg")
MG_CITRATE_FORM = "Clearly dosed magnesium citrate with declared elemental magnesium"


def _first_listed_use_case(ingredient, form):
    row = next(r for r in _FORM_TIERS
               if r["ingredient"].lower() == ingredient.lower() and r["form"].lower() == form.lower())
    return row["use_case"].split(";")[0].strip()


def test_no_claim_passes():
    ok, msg = check_evidence_alignment(_inputs([ZINC_PICOLINATE], ""))
    assert ok is True
    assert "no specific benefit" in msg.lower()


def test_general_is_treated_as_no_specific_claim():
    ok, _ = check_evidence_alignment(_inputs([ZINC_PICOLINATE], "general"))
    assert ok is True


def test_claim_listed_in_evidence_file_passes_even_though_word_is_not_in_ingredient_name():
    # Regression: the old check required 'immunity' to appear inside the name 'Zinc'.
    ok, msg = check_evidence_alignment(_inputs([ZINC_PICOLINATE], "immunity"))
    assert ok is True
    assert "Zinc" in msg


def test_claim_not_listed_in_evidence_file_fails():
    ok, msg = check_evidence_alignment(_inputs([ZINC_PICOLINATE], "hair growth"))
    assert ok is False
    assert "evidence file" in msg.lower()


def test_unknown_form_cannot_support_a_claim():
    unknown = ExtractedIngredient(name="Zinc", form="Not a real form", amount=15, unit="mg")
    ok, _ = check_evidence_alignment(_inputs([unknown], "immunity"))
    assert ok is False


def test_one_supporting_ingredient_is_enough():
    other = ExtractedIngredient(name="Magnesium", form="Oxide", amount=100, unit="mg")
    ok, msg = check_evidence_alignment(_inputs([other, ZINC_PICOLINATE], "immunity"))
    assert ok is True
    assert "Zinc" in msg


def test_drug_interaction_still_fails_independently_of_claim_alignment():
    ing = ExtractedIngredient(name="Magnesium Citrate", form=MG_CITRATE_FORM, amount=300, unit="mg")
    claim = _first_listed_use_case("Magnesium Citrate", MG_CITRATE_FORM)
    inputs = _inputs([ing], claim)
    assert check_evidence_alignment(inputs)[0] is True
    interaction_ok, interaction_msg = check_interactions(inputs)
    assert interaction_ok is False
    assert "dolutegravir" in interaction_msg.lower()
