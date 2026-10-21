from json_schema_doctor.validator import is_numeric_property

def test_is_numeric_property():
    assert is_numeric_property({"type": "integer"}) is True
    assert is_numeric_property({"type": "number"}) is True
    assert is_numeric_property({"type": "string"}) is False
