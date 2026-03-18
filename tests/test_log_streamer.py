import pytest
from services.log_streamer import LogStreamer


@pytest.mark.asyncio
async def test_stream_log_emits_log_entry():
    streamer = LogStreamer()
    assert streamer.is_active is True
    # Should not raise
    await streamer.stream_log("task-123", "Processing stage", "INFO")


@pytest.mark.asyncio
async def test_stream_log_handles_warning_level():
    streamer = LogStreamer()
    await streamer.stream_log("task-456", "Soft limit reached", "WARNING")
