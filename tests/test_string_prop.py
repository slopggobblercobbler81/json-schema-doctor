from json_schema_doctor.validator import is_string_property

def test_is_string_property():
    assert is_string_property({"type": "string"}) is True
    assert is_string_property({"type": "number"}) is False
