from app.agent.research_tools import TOOL_SCHEMAS


def test_anthropic_tool_schemas():
    assert {x["name"] for x in TOOL_SCHEMAS} == {
        "search_pubmed", "search_openfda_label", "search_clinical_trials"
    }
    for schema in TOOL_SCHEMAS:
        assert schema["input_schema"]["type"] == "object"
        assert isinstance(schema["input_schema"]["properties"], dict)
