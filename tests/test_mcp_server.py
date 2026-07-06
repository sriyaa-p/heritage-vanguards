import pytest
import json
from unittest.mock import patch, AsyncMock
from mcp_server import mcp

@pytest.mark.asyncio
async def test_list_submissions():
    with patch("mcp_server._get", new_callable=AsyncMock) as mock_get:
        mock_get.return_value = {"items": [], "total": 0, "page": 1, "page_size": 20}
        
        # Test default arguments
        content = await mcp.call_tool("list_submissions", {})
        result = json.loads(content[0].text)
        assert result == {"items": [], "total": 0, "page": 1, "page_size": 20}
        mock_get.assert_called_once_with("/submissions", params={"page": 1, "page_size": 20})
        
        mock_get.reset_mock()
        
        # Test custom arguments
        content = await mcp.call_tool("list_submissions", {"page": 2, "page_size": 10, "status": "approved"})
        result = json.loads(content[0].text)
        assert result == {"items": [], "total": 0, "page": 1, "page_size": 20}
        mock_get.assert_called_once_with("/submissions", params={"page": 2, "page_size": 10, "status": "approved"})

@pytest.mark.asyncio
async def test_get_submission():
    with patch("mcp_server._get", new_callable=AsyncMock) as mock_get:
        mock_get.return_value = {"submission_id": "SUB-123", "status": "pending"}
        
        content = await mcp.call_tool("get_submission", {"submission_id": "SUB-123"})
        result = json.loads(content[0].text)
        assert result == {"submission_id": "SUB-123", "status": "pending"}
        mock_get.assert_called_once_with("/submissions/SUB-123")

@pytest.mark.asyncio
async def test_search_unesco_sites():
    with patch("mcp_server._get", new_callable=AsyncMock) as mock_get:
        mock_get.return_value = {"results": []}
        
        content = await mcp.call_tool("search_unesco_sites", {"query": "Taj Mahal", "limit": 5})
        result = json.loads(content[0].text)
        assert result == {"results": []}
        mock_get.assert_called_once_with("/submissions/search/unesco", params={"q": "Taj Mahal", "limit": 5})

@pytest.mark.asyncio
async def test_get_scoring_criteria():
    content = await mcp.call_tool("get_scoring_criteria", {})
    result = json.loads(content[0].text)
    assert isinstance(result, dict)
    assert "categories" in result
    assert "historic_features" in result["categories"]

@pytest.mark.asyncio
async def test_submit_candidate_site():
    with patch("mcp_server._post", new_callable=AsyncMock) as mock_post:
        mock_post.return_value = {"submission_id": "SUB-123", "status": "pending", "message": "Success"}
        
        content = await mcp.call_tool("submit_candidate_site", {
            "location_name": "Test Site",
            "country": "India",
            "description": "Ancient temple",
            "submitted_by": "test-user"
        })
        result = json.loads(content[0].text)
        assert result == {"submission_id": "SUB-123", "status": "pending", "message": "Success"}
        mock_post.assert_called_once_with("/submissions", {
            "location_name": "Test Site",
            "country": "India",
            "description": "Ancient temple",
            "submitted_by": "test-user"
        })

@pytest.mark.asyncio
async def test_record_review_decision_valid():
    with patch("mcp_server._patch", new_callable=AsyncMock) as mock_patch:
        mock_patch.return_value = {"status": "approved"}
        
        content = await mcp.call_tool("record_review_decision", {
            "submission_id": "SUB-123",
            "decision": "approved",
            "notes": "Good site",
            "reviewer_id": "reviewer-1"
        })
        result = json.loads(content[0].text)
        assert result == {"status": "approved"}
        mock_patch.assert_called_once_with("/submissions/SUB-123/review", {
            "decision": "approved",
            "notes": "Good site",
            "reviewer_id": "reviewer-1"
        })

@pytest.mark.asyncio
async def test_record_review_decision_invalid():
    with patch("mcp_server._patch", new_callable=AsyncMock) as mock_patch:
        content = await mcp.call_tool("record_review_decision", {
            "submission_id": "SUB-123",
            "decision": "invalid-decision",
            "notes": "Good site",
            "reviewer_id": "reviewer-1"
        })
        result = json.loads(content[0].text)
        assert "error" in result
        mock_patch.assert_not_called()
