from json_schema_doctor.validator import is_boolean_property

def test_is_boolean_property():
    assert is_boolean_property({"type": "boolean"}) is True
    assert is_boolean_property({"type": "array"}) is False
