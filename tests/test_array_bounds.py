from json_schema_doctor.validator import check_array_bounds_coherence

def test_array_bounds_coherence():
    bad_schema = {"properties": {"tags": {"minItems": 10, "maxItems": 2}}}
    issues = check_array_bounds_coherence(bad_schema)
    assert len(issues) == 1
    good_schema = {"properties": {"tags": {"minItems": 1, "maxItems": 5}}}
    assert len(check_array_bounds_coherence(good_schema)) == 0
