from app.main import app


def test_openapi_exposes_bearer_auth_for_protected_routes():
    schema = app.openapi()
    lesson_operation = schema["paths"]["/api/v1/lessons"]["get"]

    assert schema["components"]["securitySchemes"]["BearerAuth"] == {
        "type": "http",
        "description": "Enter the access token only. Swagger adds the Bearer prefix.",
        "scheme": "bearer",
        "bearerFormat": "JWT",
    }
    assert {"BearerAuth": []} in lesson_operation["security"]
    assert any(
        parameter["name"] == "token" and parameter["in"] == "header"
        for parameter in lesson_operation["parameters"]
    )
    assert "security" not in schema["paths"]["/api/v1/token/access"]["post"]
