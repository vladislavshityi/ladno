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
