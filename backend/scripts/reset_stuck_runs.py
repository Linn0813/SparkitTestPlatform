import asyncio
import sys
sys.path.insert(0, '.')

from app.core.database import async_session_factory
from app.models.ui_automation import UITestRun, UIRunStatus
from sqlalchemy import select, update

async def fix():
    async with async_session_factory() as db:
        # 把所有卡在 running 超过 30 分钟的记录重置为 error
        result = await db.execute(
            select(UITestRun).where(UITestRun.status == UIRunStatus.running)
        )
        runs = result.scalars().all()
        for run in runs:
            print(f"Resetting run {run.id} (started: {run.started_at})")
            run.status = UIRunStatus.error
            run.error_message = "Runner 未正常上报，手动重置"
        await db.commit()
        print(f"Reset {len(runs)} run(s)")

asyncio.run(fix())
