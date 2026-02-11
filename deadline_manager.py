from __future__ import annotations

from datetime import datetime, timedelta

from discord.ext import tasks

from utils import now_utc


class DeadlineManager:
    def __init__(self, bot) -> None:
        self.bot = bot

    def start(self) -> None:
        if not self.check_quest_deadlines.is_running():
            self.check_quest_deadlines.start()

    @tasks.loop(minutes=60)
    async def check_quest_deadlines(self) -> None:
        quests = await self.bot.db.list_quests_by_status("In Progress")
        for quest in quests:
            deadline_raw = quest.get("Deadline", "")
            quest_id = quest.get("Quest ID", "")
            if not deadline_raw:
                continue
            try:
                deadline = datetime.fromisoformat(deadline_raw)
            except ValueError:
                continue
            # Warn close to the deadline, then mark overdue.
            now = now_utc()
            warning_time = deadline - timedelta(hours=self.bot.config.deadline_warning_hours)
            if warning_time <= now < deadline:
                await self.bot.db.update_quest_fields(quest_id, {"Last Notified": now.isoformat()})
            if now >= deadline:
                await self.bot.db.update_quest_fields(quest_id, {"Status": "Overdue"})
