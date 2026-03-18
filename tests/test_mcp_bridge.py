from unittest.mock import patch

from services.mcp_bridge_server import MCPBridgeServer
from services.mcp_tools import GitHubTools, JiraTools


def test_mcp_bridge_lists_tools():
    server = MCPBridgeServer()
    response = server.handle({"jsonrpc": "2.0", "id": 1, "method": "tools/list", "params": {}})
    assert response["result"]["tools"]
    assert "jira.get_issue_details" in response["result"]["tools"]


def test_mcp_bridge_jira_issue_details_call():
    server = MCPBridgeServer()
    with patch.object(server, "jira") as jira:
        jira.get_issue.return_value = {
            "key": "SCRUM-1",
            "fields": {"summary": "Test", "description": "Desc"},
        }
        response = server.handle(
            {
                "jsonrpc": "2.0",
                "id": 2,
                "method": "tools/call",
                "params": {"name": "jira.get_issue_details", "arguments": {"issue_key": "SCRUM-1"}},
            }
        )
    assert response["result"]["issue_key"] == "SCRUM-1"
    assert response["result"]["summary"] == "Test"


def test_mcp_tools_delegate_to_client():
    with patch("services.mcp_tools._mcp_client") as mock_client:
        mock_client.call_tool.return_value = {
            "issue_key": "SCRUM-2",
            "summary": "S",
            "description": "D",
        }
        output = JiraTools.get_issue_details("SCRUM-2")
        assert "Issue: SCRUM-2" in output
        mock_client.call_tool.assert_called_once()

    with patch("services.mcp_tools._mcp_client") as mock_client:
        mock_client.call_tool.return_value = {
            "items": [{"repo": "TeaSui/swarmforge", "path": "services/orchestrator.py"}]
        }
        output = GitHubTools.search_code("orchestrator")
        assert "TeaSui/swarmforge" in output
