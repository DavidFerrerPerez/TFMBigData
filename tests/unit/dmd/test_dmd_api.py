from unittest.mock import MagicMock, patch
import json
import pytest

from ingestion_engine.dmd.dmd_api import DMDApi


# DMDApi initialization tests

def test_dmd_api_init_with_token():
    """Test that DMDApi initializes with token."""
    api = DMDApi("http://api.example.com", token="my-token")
    
    assert api.dmd_api_url == "http://api.example.com"
    assert api.token == "my-token"
    assert api.headers["Authorization"] == "Bearer my-token"
    assert api.headers["Content-Type"] == "application/json"


def test_dmd_api_init_without_token():
    """Test that DMDApi initializes without token."""
    api = DMDApi("http://api.example.com")
    
    assert api.dmd_api_url == "http://api.example.com"
    assert api.token is None
    assert api.headers["Authorization"] == ""


def test_dmd_api_init_sets_empty_caches():
    """Test that DMDApi initializes with empty caches."""
    api = DMDApi("http://api.example.com")
    
    assert api._templates is None
    assert api._maindata is None
    assert api._maindata_by_code is None


# get_response tests

@patch("ingestion_engine.dmd.dmd_api.requests.get")
def test_get_response_makes_http_get_request(mock_requests_get):
    """Test that get_response makes an HTTP GET request."""
    mock_response = MagicMock()
    mock_requests_get.return_value = mock_response
    
    api = DMDApi("http://api.example.com", token="token")
    headers = {"Authorization": "Bearer token"}
    
    result = api.get_response("http://api.example.com/template", headers)
    
    mock_requests_get.assert_called_once_with(
        "http://api.example.com/template",
        verify=True,
        headers=headers,
        params=None,
        timeout=(5, 30)
    )
    assert result == mock_response


@patch("ingestion_engine.dmd.dmd_api.requests.get")
def test_get_response_with_params(mock_requests_get):
    """Test that get_response passes query parameters."""
    mock_response = MagicMock()
    mock_requests_get.return_value = mock_response
    
    api = DMDApi("http://api.example.com")
    headers = {"Content-Type": "application/json"}
    params = {"code": "PUMP", "limit": 20}
    
    result = api.get_response("http://api.example.com/template", headers, params=params)
    
    mock_requests_get.assert_called_once_with(
        "http://api.example.com/template",
        verify=True,
        headers=headers,
        params=params,
        timeout=(5, 30)
    )


# post_response tests

@patch("ingestion_engine.dmd.dmd_api.requests.post")
def test_post_response_makes_http_post_request(mock_requests_post):
    """Test that post_response makes an HTTP POST request."""
    mock_response = MagicMock()
    mock_requests_post.return_value = mock_response
    
    api = DMDApi("http://api.example.com", token="token")
    headers = {"Authorization": "Bearer token"}
    body = json.dumps({"name": "Asset1"})
    
    result = api.post_response("http://api.example.com/assets", body, headers)
    
    mock_requests_post.assert_called_once_with(
        "http://api.example.com/assets",
        verify=True,
        params=None,
        headers=headers,
        data=body,
        timeout=(5, 30)
    )
    assert result == mock_response


@patch("ingestion_engine.dmd.dmd_api.requests.post")
def test_post_response_with_params(mock_requests_post):
    """Test that post_response passes query parameters."""
    mock_response = MagicMock()
    mock_requests_post.return_value = mock_response
    
    api = DMDApi("http://api.example.com")
    headers = {"Content-Type": "application/json"}
    body = '{"data": "value"}'
    params = {"action": "create"}
    
    result = api.post_response("http://api.example.com/assets", body, headers, params=params)
    
    mock_requests_post.assert_called_once_with(
        "http://api.example.com/assets",
        verify=True,
        params=params,
        headers=headers,
        data=body,
        timeout=(5, 30)
    )


# _get_templates tests

@patch("ingestion_engine.dmd.dmd_api.DMDApi.get_response")
def test_get_templates_fetches_from_api(mock_get_response):
    """Test that _get_templates fetches templates from API."""
    mock_response = MagicMock()
    templates = [
        {"id": 1, "code": "PUMP", "name": "Pump"},
        {"id": 2, "code": "VALVE", "name": "Valve"},
    ]
    mock_response.json.return_value = templates
    mock_get_response.return_value = mock_response
    
    api = DMDApi("http://api.example.com", token="token")
    result = api._get_templates()
    
    assert result == templates
    mock_get_response.assert_called_once_with(
        "http://api.example.com/api/v2/template/",
        headers=api.headers
    )


@patch("ingestion_engine.dmd.dmd_api.DMDApi.get_response")
def test_get_templates_caches_result(mock_get_response):
    """Test that _get_templates caches the result."""
    mock_response = MagicMock()
    mock_response.json.return_value = [{"id": 1, "code": "PUMP"}]
    mock_get_response.return_value = mock_response
    
    api = DMDApi("http://api.example.com")
    
    # Call twice
    result1 = api._get_templates()
    result2 = api._get_templates()
    
    # get_response should only be called once
    mock_get_response.assert_called_once()
    assert result1 == result2


@patch("ingestion_engine.dmd.dmd_api.DMDApi.get_response")
def test_get_templates_raises_on_error(mock_get_response):
    """Test that _get_templates raises HTTPError on API error."""
    mock_response = MagicMock()
    mock_response.raise_for_status.side_effect = Exception("404 Not Found")
    mock_get_response.return_value = mock_response
    
    api = DMDApi("http://api.example.com")
    
    with pytest.raises(Exception):
        api._get_templates()


# get_template_metadata tests

@patch("ingestion_engine.dmd.dmd_api.DMDApi._get_templates")
def test_get_template_metadata_returns_template_data(mock_get_templates):
    """Test that get_template_metadata returns template metadata."""
    mock_get_templates.return_value = [
        {
            "id": 1,
            "code": "PUMP",
            "name": "Pump Asset",
            "isDeleted": False,
            "isEnabled": True,
            "geometryType": "Point",
        }
    ]
    
    api = DMDApi("http://api.example.com")
    result = api.get_template_metadata("PUMP")
    
    expected = {
        "id": 1,
        "code": "PUMP",
        "name": "Pump Asset",
        "is_deleted": False,
        "is_enabled": True,
        "geometry_type": "Point",
    }
    assert result == expected


@patch("ingestion_engine.dmd.dmd_api.DMDApi._get_templates")
def test_get_template_metadata_raises_for_unknown_code(mock_get_templates):
    """Test that get_template_metadata raises ValueError for unknown code."""
    mock_get_templates.return_value = [
        {"id": 1, "code": "PUMP"},
    ]
    
    api = DMDApi("http://api.example.com")
    
    with pytest.raises(ValueError) as exc_info:
        api.get_template_metadata("UNKNOWN")
    
    assert "Template with code 'UNKNOWN' not found" in str(exc_info.value)


@patch("ingestion_engine.dmd.dmd_api.DMDApi._get_templates")
def test_get_template_metadata_handles_missing_fields(mock_get_templates):
    """Test that get_template_metadata handles missing optional fields."""
    mock_get_templates.return_value = [
        {
            "id": 1,
            "code": "PUMP",
            # Missing other fields
        }
    ]
    
    api = DMDApi("http://api.example.com")
    result = api.get_template_metadata("PUMP")
    
    assert result["id"] == 1
    assert result["code"] == "PUMP"
    assert result["name"] is None
    assert result["is_deleted"] is None


# get_template_schema_by_id tests

@patch("ingestion_engine.dmd.dmd_api.DMDApi.get_response")
def test_get_template_schema_by_id_returns_characteristics(mock_get_response):
    """Test that get_template_schema_by_id returns template characteristics."""
    mock_response = MagicMock()
    characteristics = [
        {"name": "name", "type": "String"},
        {"name": "type", "type": "String"},
    ]
    mock_response.json.return_value = {"characteristics": characteristics}
    mock_get_response.return_value = mock_response
    
    api = DMDApi("http://api.example.com")
    result = api.get_template_schema_by_id(1)
    
    assert result == characteristics
    mock_get_response.assert_called_once_with(
        "http://api.example.com/api/v2/template/description/1",
        headers=api.headers,
    )


@patch("ingestion_engine.dmd.dmd_api.DMDApi.get_response")
def test_get_template_schema_by_id_returns_empty_list_if_no_characteristics(mock_get_response):
    """Test that get_template_schema_by_id returns empty list if no characteristics."""
    mock_response = MagicMock()
    mock_response.json.return_value = {}  # No characteristics key
    mock_get_response.return_value = mock_response
    
    api = DMDApi("http://api.example.com")
    result = api.get_template_schema_by_id(1)
    
    assert result == []


# _get_maindata_values tests

@patch("ingestion_engine.dmd.dmd_api.DMDApi.get_response")
def test_get_maindata_values_fetches_from_api(mock_get_response):
    """Test that _get_maindata_values fetches maindata from API."""
    mock_response = MagicMock()
    maindata = [
        {"code": "STATUS", "relations": [{"name": "Active", "id": 1}]},
        {"code": "TYPE", "relations": [{"name": "Type1", "id": 10}]},
    ]
    mock_response.json.return_value = maindata
    mock_get_response.return_value = mock_response
    
    api = DMDApi("http://api.example.com")
    result = api._get_maindata_values()
    
    assert result == maindata


@patch("ingestion_engine.dmd.dmd_api.DMDApi.get_response")
def test_get_maindata_values_caches_result(mock_get_response):
    """Test that _get_maindata_values caches the result."""
    mock_response = MagicMock()
    mock_response.json.return_value = []
    mock_get_response.return_value = mock_response
    
    api = DMDApi("http://api.example.com")
    
    # Call twice
    result1 = api._get_maindata_values()
    result2 = api._get_maindata_values()
    
    # get_response should only be called once
    mock_get_response.assert_called_once()
    assert result1 == result2


# get_maindata_values_by_code tests

@patch("ingestion_engine.dmd.dmd_api.DMDApi._get_maindata_values")
def test_get_maindata_values_by_code_returns_mapping(mock_get_maindata):
    """Test that get_maindata_values_by_code returns value-to-ID mapping."""
    mock_get_maindata.return_value = [
        {
            "code": "STATUS",
            "name": "Status Maindata",
            "relations": [
                {"name": "Active", "id": 1},
                {"name": "Inactive", "id": 2},
            ]
        },
        {
            "code": "TYPE",
            "name": "Type Maindata",
            "relations": [
                {"name": "TypeA", "id": 10},
            ]
        }
    ]
    
    api = DMDApi("http://api.example.com")
    result = api.get_maindata_values_by_code("STATUS")
    
    expected = {
        "Active": 1,
        "Inactive": 2,
    }
    assert result == expected


@patch("ingestion_engine.dmd.dmd_api.DMDApi._get_maindata_values")
def test_get_maindata_values_by_code_by_name(mock_get_maindata):
    """Test that get_maindata_values_by_code works with name as well as code."""
    mock_get_maindata.return_value = [
        {
            "code": "STATUS",
            "name": "Status Maindata",
            "relations": [{"name": "Active", "id": 1}]
        }
    ]
    
    api = DMDApi("http://api.example.com")
    
    # Both code and name should work
    result_by_code = api.get_maindata_values_by_code("STATUS")
    result_by_name = api.get_maindata_values_by_code("Status Maindata")
    
    assert result_by_code == {"Active": 1}
    assert result_by_name == {"Active": 1}


@patch("ingestion_engine.dmd.dmd_api.DMDApi._get_maindata_values")
def test_get_maindata_values_by_code_returns_empty_for_unknown(mock_get_maindata):
    """Test that get_maindata_values_by_code returns empty dict for unknown code."""
    mock_get_maindata.return_value = [
        {
            "code": "STATUS",
            "relations": [{"name": "Active", "id": 1}]
        }
    ]
    
    api = DMDApi("http://api.example.com")
    result = api.get_maindata_values_by_code("UNKNOWN")
    
    assert result == {}


@patch("ingestion_engine.dmd.dmd_api.DMDApi._get_maindata_values")
def test_get_maindata_values_by_code_caches_result(mock_get_maindata):
    """Test that get_maindata_values_by_code caches the result."""
    mock_get_maindata.return_value = [
        {
            "code": "STATUS",
            "relations": [{"name": "Active", "id": 1}]
        }
    ]
    
    api = DMDApi("http://api.example.com")
    
    # Call twice with different codes
    result1 = api.get_maindata_values_by_code("STATUS")
    result2 = api.get_maindata_values_by_code("UNKNOWN")
    
    # _get_maindata_values should only be called once
    mock_get_maindata.assert_called_once()


# create_assets tests

@patch("ingestion_engine.dmd.dmd_api.DMDApi.post_response")
def test_create_assets_posts_to_api(mock_post_response):
    """Test that create_assets posts assets to API."""
    mock_response = MagicMock()
    mock_post_response.return_value = mock_response
    
    api = DMDApi("http://api.example.com", token="token")
    assets = [
        {"name": "Asset1", "code": "ASSET1"},
        {"name": "Asset2", "code": "ASSET2"},
    ]
    
    result = api.create_assets(assets)
    
    mock_post_response.assert_called_once()
    call_args = mock_post_response.call_args
    
    assert call_args[1]["url"] == "http://api.example.com/api/v2/assets/"
    assert call_args[1]["body"] == json.dumps(assets)
    assert call_args[1]["headers"] == api.headers
    assert result == mock_response


@patch("ingestion_engine.dmd.dmd_api.DMDApi.post_response")
def test_create_assets_handles_empty_list(mock_post_response):
    """Test that create_assets handles empty asset list."""
    mock_response = MagicMock()
    mock_post_response.return_value = mock_response
    
    api = DMDApi("http://api.example.com")
    
    result = api.create_assets([])
    
    mock_post_response.assert_called_once()
    call_args = mock_post_response.call_args
    assert call_args[1]["body"] == json.dumps([])
