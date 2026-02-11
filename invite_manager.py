from __future__ import annotations

from datetime import datetime, timedelta
from typing import Optional

import discord
from discord.ext import tasks

from party_embeds import party_invite_embed
from party_views import PartyInviteView
from utils import now_utc


class InviteManager:
    def __init__(self, bot) -> None:
        self.bot = bot

    def start(self) -> None:
        if not self.check_party_invites.is_running():
            self.check_party_invites.start()

    @tasks.loop(minutes=60)
    async def check_party_invites(self) -> None:
        pending = await self.bot.db.list_pending_invites()
        for invite in pending:
            expiry_raw = invite.get("Expiry Date", "")
            try:
                expiry = datetime.fromisoformat(expiry_raw)
            except ValueError:
                continue
            if now_utc() >= expiry:
                await self.bot.db.update_invite_fields(invite.get("Invite ID", ""), {"Status": "Expired", "Response Date": now_utc().isoformat()})

    async def send_party_invite(self, party_id: str, target: discord.User, invited_by: discord.User) -> Optional[str]:
        party = await self.bot.db.get_party_by_id(party_id)
        if not party:
            return None
        invited_date = now_utc()
        expiry_date = invited_date + timedelta(hours=self.bot.config.party_invite_expiry_hours)
        await self.bot.db.create_invite(
            party_id,
            party.get("Party Name", ""),
            target.name,
            str(target.id),
            invited_by.name,
            invited_date.isoformat(),
            expiry_date.isoformat(),
        )
        invite_id = await self._latest_invite_id()
        if not invite_id:
            return None
        members = (party.get("Members", "") or "").split(",")
        member_list = []
        for raw in members:
            raw = raw.strip()
            if raw:
                member_list.append(raw)
        embed = party_invite_embed(
            self.bot.config,
            party.get("Party Name", ""),
            party.get("Leader Username", ""),
            party.get("Rank", ""),
            party.get("Completed Quests #", "0"),
            member_list,
            self.bot.config.party_invite_expiry_hours,
        )
        view = PartyInviteView(self.bot, invite_id, target.id)
        await target.send(embed=embed, view=view)
        return invite_id

    async def process_invite_response(self, invite_id: str, accepted: bool) -> str:
        invite = await self.bot.db.get_invite_by_id(invite_id)
        if not invite:
            return "Invite not found."
        if invite.get("Status") != "Pending":
            return "Invite is no longer active."
        status = "Accepted" if accepted else "Declined"
        await self.bot.db.update_invite_fields(invite_id, {"Status": status, "Response Date": now_utc().isoformat()})
        if not accepted:
            return "Invite declined."
        target_user = await self.bot.db.get_user_by_discord_id(str(invite.get("Invited Discord ID", "")))
        if target_user and target_user.get("Party") not in {"", "None"}:
            return "You are already in a party."
        party_id = invite.get("Party ID", "")
        party = await self.bot.db.get_party_by_id(party_id)
        if not party:
            return "Party not found."
        members = []
        for raw in (party.get("Members", "") or "").split(","):
            raw = raw.strip()
            if raw:
                members.append(raw)
        if str(invite.get("Invited Discord ID", "")) in members:
            return "You are already in the party."
        members.append(str(invite.get("Invited Discord ID", "")))
        await self.bot.db.set_party_members(party_id, members)
        await self.bot.db.update_user_fields(str(invite.get("Invited Discord ID", "")), {"Party": party_id, "Party Role": "Member"})
        return "Invite accepted."

    async def _latest_invite_id(self) -> Optional[str]:
        rows = await self.bot.db.sheets.get_rows_as_dicts(self.bot.config.party_invites_sheet_name)
        if not rows:
            return None
        last = rows[-1]
        return last.get("Invite ID")
