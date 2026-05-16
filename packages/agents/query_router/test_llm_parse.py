from query_router.llm_parse import (
    is_out_of_scope_output,
    out_of_scope_router_output,
    parse_router_json,
)


def test_parse_empty_json_as_out_of_scope() -> None:
    output = parse_router_json("{}")
    assert is_out_of_scope_output(output)
    assert output.intent == "unsupported"


def test_parse_valid_json() -> None:
    output = parse_router_json(
        '{"intent":"count","filters":{},"aggregation":"count","domain":"customers"}'
    )
    assert output.intent == "count"
    assert not is_out_of_scope_output(output)


def test_parse_coerces_compound_without_top_level_fields() -> None:
    output = parse_router_json(
        '{"complexity":"compound","mentioned_companies":["Acme Retail","NordLogistics"],'
        '"sub_queries":[{"intent":"count","filters":{"region":"Italy"},'
        '"aggregation":"count","domain":"customers"},'
        '{"intent":"count","filters":{"region":"Italy"},'
        '"aggregation":"count","domain":"logistics_shipments"}]}'
    )
    assert output.intent == "compare"
    assert output.complexity == "compound"
    assert len(output.sub_queries) == 2
    assert not is_out_of_scope_output(output)
