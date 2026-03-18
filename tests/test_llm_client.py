import pytest
from unittest.mock import patch, AsyncMock
from langchain_core.messages import HumanMessage, AIMessage
from services.llm_client import LLMClient

@pytest.mark.asyncio
async def test_llm_client_primary_success():
    client = LLMClient()
    messages = [HumanMessage(content="Hello")]
    expected_response = AIMessage(
        content="Hi there!", 
        usage_metadata={"input_tokens": 50, "output_tokens": 50, "total_tokens": 100}
    )
    
    with patch("services.llm_client.ChatAnthropic.ainvoke", new_callable=AsyncMock) as mock_primary, \
         patch("services.llm_client.ChatBedrock.ainvoke", new_callable=AsyncMock) as mock_fallback:
        
        mock_primary.return_value = expected_response
        
        response = await client.chat(messages)
        
        assert response.content == "Hi there!"
        mock_primary.assert_called_once()
        mock_fallback.assert_not_called()

@pytest.mark.asyncio
async def test_llm_client_failover_success():
    client = LLMClient()
    messages = [HumanMessage(content="Hello")]
    expected_response = AIMessage(
        content="Hi from Bedrock!", 
        usage_metadata={"input_tokens": 20, "output_tokens": 30, "total_tokens": 50}
    )
    
    with patch("services.llm_client.ChatAnthropic.ainvoke", new_callable=AsyncMock) as mock_primary, \
         patch("services.llm_client.ChatBedrock.ainvoke", new_callable=AsyncMock) as mock_fallback:
        
        mock_primary.side_effect = Exception("Anthropic Down")
        mock_fallback.return_value = expected_response
        
        response = await client.chat(messages)
        
        assert response.content == "Hi from Bedrock!"
        mock_primary.assert_called_once()
        mock_fallback.assert_called_once()

@pytest.mark.asyncio
async def test_llm_client_both_fail():
    client = LLMClient()
    messages = [HumanMessage(content="Hello")]
    
    with patch("services.llm_client.ChatAnthropic.ainvoke", new_callable=AsyncMock) as mock_primary, \
         patch("services.llm_client.ChatBedrock.ainvoke", new_callable=AsyncMock) as mock_fallback:
        
        mock_primary.side_effect = Exception("Anthropic Down")
        mock_fallback.side_effect = Exception("Bedrock Down")
        
        with pytest.raises(Exception) as excinfo:
            await client.chat(messages)
        
        assert "Bedrock Down" in str(excinfo.value)
