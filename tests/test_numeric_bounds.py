from json_schema_doctor.validator import check_numeric_bounds_coherence

def test_numeric_bounds_coherence():
    bad_schema = {"properties": {"age": {"minimum": 100, "maximum": 10}}}
    issues = check_numeric_bounds_coherence(bad_schema)
    assert len(issues) == 1
    good_schema = {"properties": {"age": {"minimum": 10, "maximum": 100}}}
    assert len(check_numeric_bounds_coherence(good_schema)) == 0
