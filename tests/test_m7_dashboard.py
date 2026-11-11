from dashboard.api_client import PCMSCApiClient


def test_dashboard_api_client_instantiation():
    client = PCMSCApiClient(base_url="http://localhost:8000/", api_key="demo-admin-key")
    assert client.base_url == "http://localhost:8000"
    assert client._headers() == {"X-API-Key": "demo-admin-key"}

