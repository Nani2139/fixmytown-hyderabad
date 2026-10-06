from wardwatch_api.vision import interpret_classification


def test_banana_is_not_a_street_problem():
    typ, _conf, unrelated = interpret_classification(
        {"relevant": False, "type": None, "confidence": 0.92}
    )
    assert typ is None
    assert unrelated is True


def test_a_real_pothole_can_be_suggested():
    typ, conf, unrelated = interpret_classification(
        {"relevant": True, "type": "pothole", "confidence": 0.8}
    )
    assert typ == "pothole"
    assert conf == 0.8
    assert unrelated is False
