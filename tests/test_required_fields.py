from json_schema_doctor.validator import get_required_fields

def test_get_required_fields():
    schema = {"type": "object", "required": ["id", "username"]}
    assert get_required_fields(schema) == ["id", "username"]
