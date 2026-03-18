import pytest
from services.budget_manager import BudgetManager, BudgetExceededError

@pytest.mark.asyncio
async def test_budget_manager_under_limits():
    bm = BudgetManager()
    bm.token_hard = 1000
    bm.usd_hard = 1.0

    # Should not raise
    await bm.add_usage(500, 0.5)
    assert bm.current_tokens == 500
    assert bm.current_usd == 0.5

@pytest.mark.asyncio
async def test_budget_manager_token_exceeded():
    bm = BudgetManager()
    bm.token_hard = 1000

    with pytest.raises(BudgetExceededError) as exc:
        await bm.add_usage(1001, 0.1)
    assert "Token hard limit exceeded" in str(exc.value)

@pytest.mark.asyncio
async def test_budget_manager_usd_exceeded():
    bm = BudgetManager()
    bm.usd_hard = 1.0

    with pytest.raises(BudgetExceededError) as exc:
        await bm.add_usage(100, 1.1)
    assert "USD hard limit exceeded" in str(exc.value)

@pytest.mark.asyncio
async def test_budget_manager_reset():
    bm = BudgetManager()
    await bm.add_usage(100, 0.1)
    await bm.reset()
    assert bm.current_tokens == 0
    assert bm.current_usd == 0.0
