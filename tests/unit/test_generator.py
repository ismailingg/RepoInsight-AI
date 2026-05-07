from backend.core.generator import validate_citations, calculate_confidence, is_out_of_scope

def test_validate_citations_hallucination():
    valid_files = ["main.py", "utils/helper.py"]
    answer = "Check main.py and fake_file.py"
    
    validated = validate_citations(answer, valid_files)
    
    assert "main.py" in validated
    assert "fake_file.py" in validated
    assert "⚠️ Note: The following files were cited but could not be verified" in validated
    assert "fake_file.py" in validated.split("verified in the indexed codebase:")[1]

def test_validate_citations_no_hallucination():
    valid_files = ["main.py", "utils/helper.py"]
    answer = "Check main.py and utils/helper.py"
    
    validated = validate_citations(answer, valid_files)
    
    assert "⚠️ Note" not in validated

def test_calculate_confidence_base():
    chunks = [{"similarity": 0.5}, {"similarity": 0.7}]
    confidence = calculate_confidence(chunks)
    # avg = 0.6, bonus = 0.02 (coverage)
    assert 0.6 < confidence < 0.7

def test_is_out_of_scope():
    chunks = [{"similarity": 0.1}, {"similarity": 0.15}]
    assert is_out_of_scope(chunks) is True
    
    chunks = [{"similarity": 0.1}, {"similarity": 0.3}]
    assert is_out_of_scope(chunks) is False
