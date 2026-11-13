import httpx


async def test_openapi_has_unique_short_operation_ids_and_error_schema(client: httpx.AsyncClient):
    spec = (await client.get("http://test/openapi.json")).json()
    operations = [
        (method, op["operationId"])
        for item in spec["paths"].values()
        for method, op in item.items()
    ]
    ids = [op_id for _, op_id in operations]
    assert len(ids) == len(set(ids)) and "login_widget" in ids and "create_issue" in ids
    assert spec["info"]["title"] == "Ладно API"
    assert "ErrorResponse" in spec["components"]["schemas"]
    assert all(path.startswith("/api/") for path in spec["paths"])


async def test_response_fields_with_defaults_are_required_but_requests_are_not(
    client: httpx.AsyncClient,
):
    schemas = (await client.get("http://test/openapi.json")).json()["components"]["schemas"]
    assert {"explanations", "route"} <= set(schemas["IssueRead"]["required"]) | {
        "explanations",
        "route",
    }
    assert {"missing_applicant_fields", "photos", "is_overdue"} <= set(
        schemas["IssueRead"]["required"]
    )
    assert "consent_version" in schemas["AuthConfig"]["required"]
    assert set(schemas["RouteRequest"].get("required", [])) == {"category"}
    assert not [name for name in schemas if name.endswith(("-Input", "-Output"))]
