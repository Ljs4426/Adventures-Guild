from __future__ import annotations

from datetime import datetime
from typing import Dict, List, Optional

from utils import join_csv, now_utc, split_csv


class PartyManager:
    def __init__(self, bot) -> None:
        self.bot = bot

    async def check_party_permission(self, user_id: int, party_id: str, permission_type: str) -> bool:
        party = await self.bot.db.get_party_by_id(party_id)
        if not party:
            return False
        leader_id = party.get("Leader Discord ID", "")
        if str(user_id) == str(leader_id):
            return True
        setting_map = {
            "quest_accept": "Quest Accept Perm",
            "quest_complete": "Quest Complete Perm",
            "quest_abandon": "Quest Abandon Perm",
            "invite": "Invite Perm",
        }
        setting_field = setting_map.get(permission_type)
        if not setting_field:
            return False
        return party.get(setting_field, "Leader Only") == "All Members"

    async def is_party_leader(self, user_id: int, party_id: str) -> bool:
        party = await self.bot.db.get_party_by_id(party_id)
        if not party:
            return False
        return str(party.get("Leader Discord ID", "")) == str(user_id)

    async def get_party_leader(self, party_id: str) -> Optional[str]:
        party = await self.bot.db.get_party_by_id(party_id)
        if not party:
            return None
        return party.get("Leader Discord ID", "")

    async def transfer_party_leadership(self, party_id: str, old_leader_id: str, new_leader_id: str, new_leader_name: str) -> bool:
        party = await self.bot.db.get_party_by_id(party_id)
        if not party:
            return False
        members = split_csv(party.get("Members", ""))
        if new_leader_id not in members:
            return False
        new_members = []
        for member in members:
            if member != new_leader_id:
                new_members.append(member)
        members = new_members
        if old_leader_id:
            members.append(old_leader_id)
        await self.bot.db.update_party_fields(
            party_id,
            {
                "Leader Discord ID": new_leader_id,
                "Leader Username": new_leader_name,
                "Last Settings Update": datetime.utcnow().strftime("%Y-%m-%d %H:%M:%S"),
                "Settings Updated By": new_leader_name,
                "Members": join_csv(members),
                "Member Count": str(len(members)),
            },
        )
        await self.bot.db.update_user_fields(old_leader_id, {"Party Role": "Member"})
        await self.bot.db.update_user_fields(new_leader_id, {"Party Role": "Leader"})
        return True

    async def update_party_setting(self, party_id: str, setting_name: str, value: str, updated_by: str) -> bool:
        return await self.bot.db.update_party_fields(
            party_id,
            {
                setting_name: value,
                "Last Settings Update": datetime.utcnow().strftime("%Y-%m-%d %H:%M:%S"),
                "Settings Updated By": updated_by,
            },
        )

    async def kick_party_member(self, party_id: str, member_id: str) -> bool:
        party = await self.bot.db.get_party_by_id(party_id)
        if not party:
            return False
        members = split_csv(party.get("Members", ""))
        if member_id not in members:
            return False
        new_members = []
        for mid in members:
            if mid != member_id:
                new_members.append(mid)
        members = new_members
        await self.bot.db.set_party_members(party_id, members)
        await self.bot.db.update_user_fields(member_id, {"Party": "None", "Party Role": "None"})
        return True

    async def disband_party(self, party_id: str, disbanded_by: str, reason: str) -> bool:
        party = await self.bot.db.get_party_by_id(party_id)
        if not party:
            return False
        members = split_csv(party.get("Members", ""))
        leader_id = party.get("Leader Discord ID", "")
        for member_id in members:
            await self.bot.db.update_user_fields(member_id, {"Party": "None", "Party Role": "None"})
        if leader_id:
            await self.bot.db.update_user_fields(leader_id, {"Party": "None", "Party Role": "None"})
        await self.archive_party(party_id, reason, disbanded_by)
        return True

    async def archive_party(self, party_id: str, reason: str, disbanded_by: str) -> None:
        party = await self.bot.db.get_party_by_id(party_id)
        if not party:
            return
        row = [
            party.get("Party ID", ""),
            party.get("Party Name", ""),
            party.get("Leader Username", ""),
            party.get("Members", ""),
            party.get("Rank", ""),
            party.get("Rank Points", ""),
            party.get("Completed Quest IDs", ""),
            party.get("Created Date", ""),
            now_utc().strftime("%Y-%m-%d %H:%M:%S"),
            disbanded_by,
            reason,
        ]
        await self.bot.db.sheets.append_row(self.bot.config.archived_parties_sheet_name, row)
        await self.bot.db.update_party_fields(party_id, {"Members": "", "Member Count": "0"})
