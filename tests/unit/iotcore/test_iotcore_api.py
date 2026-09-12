from unittest.mock import MagicMock, patch
import pytest

from ingestion_engine.iotcore.iotcore_api import IOTCoreAPI


# IOTCoreAPI initialization tests

def test_iotcore_api_init_with_token():
    """Test that IOTCoreAPI initializes with token."""
    api = IOTCoreAPI("http://api.example.com", token="my-token", driver="driver-name")
    
    assert api.iotcore_api_url == "http://api.example.com"
    assert api.token == "my-token"
    assert api.driver == "driver-name"
    assert api.headers["Authorization"] == "Bearer my-token"
    assert api.headers["Content-Type"] == "application/json"


def test_iotcore_api_init_without_token():
    """Test that IOTCoreAPI initializes without token."""
    api = IOTCoreAPI("http://api.example.com")
    
    assert api.iotcore_api_url == "http://api.example.com"
    assert api.token is None
    assert api.headers["Authorization"] == ""
    assert api.headers["Content-Type"] == "application/json"


def test_iotcore_api_init_sets_empty_caches():
    """Test that IOTCoreAPI initializes with empty caches."""
    api = IOTCoreAPI("http://api.example.com")
    
    assert api._tags is None
    assert api._tags_by_name is None


# get_response tests

@patch("ingestion_engine.iotcore.iotcore_api.requests.Session")
def test_get_response_makes_http_get_request(mock_session_cls):
    """Test that get_response makes an HTTP GET request."""
    mock_response = MagicMock()
    mock_session = MagicMock()
    mock_session.get.return_value = mock_response
    mock_session_cls.return_value = mock_session
    
    api = IOTCoreAPI("http://api.example.com", token="token")
    headers = {"Authorization": "Bearer token"}
    
    result = api.get_response("http://api.example.com/tags", headers)
    
    mock_session.get.assert_called_once_with(
        "http://api.example.com/tags",
        verify=True,
        headers=headers,
        params=None,
        timeout=(5, 30)
    )
    assert result == mock_response


@patch("ingestion_engine.iotcore.iotcore_api.requests.Session")
def test_get_response_with_params(mock_session_cls):
    """Test that get_response passes query parameters."""
    mock_response = MagicMock()
    mock_session = MagicMock()
    mock_session.get.return_value = mock_response
    mock_session_cls.return_value = mock_session
    
    api = IOTCoreAPI("http://api.example.com")
    headers = {"Content-Type": "application/json"}
    params = {"driver": "driver-name", "limit": 10}
    
    result = api.get_response("http://api.example.com/tags", headers, params=params)
    
    mock_session.get.assert_called_once_with(
        "http://api.example.com/tags",
        verify=True,
        headers=headers,
        params=params,
        timeout=(5, 30)
    )


@patch("ingestion_engine.iotcore.iotcore_api.requests.Session")
def test_get_response_uses_request_timeout(mock_session_cls):
    """Test that get_response uses the correct timeout."""
    mock_response = MagicMock()
    mock_session = MagicMock()
    mock_session.get.return_value = mock_response
    mock_session_cls.return_value = mock_session
    
    api = IOTCoreAPI("http://api.example.com")
    
    api.get_response("http://api.example.com/tags", {})
    
    call_kwargs = mock_session.get.call_args[1]
    assert call_kwargs["timeout"] == (5, 30)


# _catalogue_tags_by_name tests

def test_catalogue_tags_by_name_builds_mapping():
    """Test that _catalogue_tags_by_name builds name-to-uid mapping."""
    api = IOTCoreAPI("http://api.example.com")
    
    # Mock the _catalogue_tags method on the instance
    api._catalogue_tags = MagicMock(return_value=[
        {"name": "tag1", "uid": "uid1"},
        {"name": "tag2", "uid": "uid2"},
        {"name": "tag3", "uid": "uid3"},
    ])
    
    result = api._catalogue_tags_by_name()
    
    assert result == {
        "tag1": ["uid1"],
        "tag2": ["uid2"],
        "tag3": ["uid3"],
    }


def test_catalogue_tags_by_name_handles_duplicate_names():
    """Test that _catalogue_tags_by_name handles tags with the same name."""
    api = IOTCoreAPI("http://api.example.com")
    
    # Mock the _catalogue_tags method on the instance
    api._catalogue_tags = MagicMock(return_value=[
        {"name": "tag1", "uid": "uid1"},
        {"name": "tag1", "uid": "uid2"},
        {"name": "tag2", "uid": "uid3"},
    ])
    
    result = api._catalogue_tags_by_name()
    
    assert result == {
        "tag1": ["uid1", "uid2"],
        "tag2": ["uid3"],
    }


def test_catalogue_tags_by_name_ignores_missing_name_or_uid():
    """Test that _catalogue_tags_by_name ignores tags with missing name or uid."""
    api = IOTCoreAPI("http://api.example.com")
    
    # Mock the _catalogue_tags method on the instance
    api._catalogue_tags = MagicMock(return_value=[
        {"name": "tag1", "uid": "uid1"},
        {"name": "tag2"},  # missing uid
        {"uid": "uid3"},  # missing name
        {"name": "tag4", "uid": "uid4"},
    ])
    
    result = api._catalogue_tags_by_name()
    
    assert result == {
        "tag1": ["uid1"],
        "tag4": ["uid4"],
    }


def test_catalogue_tags_by_name_caches_result():
    """Test that _catalogue_tags_by_name caches the result."""
    api = IOTCoreAPI("http://api.example.com")
    
    # Mock the _catalogue_tags method on the instance
    mock_catalogue_tags = MagicMock(return_value=[{"name": "tag1", "uid": "uid1"}])
    api._catalogue_tags = mock_catalogue_tags
    
    # Call twice
    result1 = api._catalogue_tags_by_name()
    result2 = api._catalogue_tags_by_name()
    
    # _catalogue_tags should only be called once
    mock_catalogue_tags.assert_called_once()
    assert result1 == result2


# get_uids_from_tag_name tests

def test_get_uids_from_tag_name_returns_uids():
    """Test that get_uids_from_tag_name returns UIDs for a tag."""
    api = IOTCoreAPI("http://api.example.com")
    
    # Set up the cached tags mapping
    api._tags_by_name = {
        "tag1": ["uid1", "uid2"],
        "tag2": ["uid3"],
    }
    
    result = api.get_uids_from_tag_name("tag1")
    
    assert result == ["uid1", "uid2"]


def test_get_uids_from_tag_name_returns_empty_list_for_unknown_tag():
    """Test that get_uids_from_tag_name returns empty list for unknown tag."""
    api = IOTCoreAPI("http://api.example.com")
    
    # Set up the cached tags mapping
    api._tags_by_name = {
        "tag1": ["uid1"],
    }
    
    result = api.get_uids_from_tag_name("unknown_tag")
    
    assert result == []


def test_get_uids_from_tag_name_is_case_sensitive():
    """Test that get_uids_from_tag_name is case-sensitive."""
    api = IOTCoreAPI("http://api.example.com")
    
    # Set up the cached tags mapping
    api._tags_by_name = {
        "Tag1": ["uid1"],
    }
    
    # Exact match
    assert api.get_uids_from_tag_name("Tag1") == ["uid1"]
    
    # Different case doesn't match
    assert api.get_uids_from_tag_name("tag1") == []
