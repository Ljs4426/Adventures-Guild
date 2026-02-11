from __future__ import annotations

import discord

from embeds import quest_details_embed
from utils import add_days, can_accept_rank, format_dt, now_utc, rank_points, split_csv


class QuestReviewView(discord.ui.View):
    def __init__(self, bot, quest_id: str):
        super().__init__(timeout=None)
        self.bot = bot
        self.quest_id = quest_id

    async def _delete_review_message(self, channel_id: int, message_id: int) -> None:
        review_channel = self.bot.get_channel(channel_id)
        if not review_channel:
            return
        try:
            message = await review_channel.fetch_message(message_id)
            await message.delete()
        except (discord.NotFound, discord.Forbidden, discord.HTTPException):
            pass

    async def _approve(self, interaction: discord.Interaction, rank: str, channel_id: int, message_id: int) -> str:
        db = self.bot.db
        # Set rank and make the quest active.
        await db.update_quest_fields(self.quest_id, {"Quest Rank": rank, "Status": "Active", "Assigned By": interaction.user.name})
        quest = await db.get_quest_by_id(self.quest_id)
        if quest:
            board_channel = self.bot.get_channel(self.bot.config.quest_board_channel_id)
            if board_channel:
                embed = quest_details_embed(self.bot.config, quest)
                view = QuestBoardView(self.bot, self.quest_id)
                message = await board_channel.send(embed=embed, view=view)
                await db.update_quest_fields(self.quest_id, {"Board Message ID": str(message.id)})
        await self._delete_review_message(channel_id, message_id)
        return "Quest approved and posted to the quest board."

    async def _deny(self, interaction: discord.Interaction, channel_id: int, message_id: int) -> str:
        db = self.bot.db
        # Deny and clean up the review post.
        await db.update_quest_fields(self.quest_id, {"Status": "Denied", "Assigned By": interaction.user.name})
        await self._delete_review_message(channel_id, message_id)
        return "Quest denied."

    async def _send_confirmation(self, interaction: discord.Interaction, action: str, rank: str | None = None) -> None:
        if not interaction.message:
            await interaction.response.send_message("Unable to confirm this action.", ephemeral=True)
            return
        # Ask for a second click to confirm.
        view = QuestReviewConfirmView(
            self,
            action,
            rank,
            interaction.channel_id,
            interaction.message.id,
        )
        label = "approve" if action == "approve" else "deny"
        suffix = f" as {rank}" if rank else ""
        await interaction.response.send_message(f"Confirm {label} quest{suffix}?", ephemeral=True, view=view)

    @discord.ui.button(label="Approve F", style=discord.ButtonStyle.success)
    async def approve_f(self, interaction: discord.Interaction, button: discord.ui.Button):
        await self._send_confirmation(interaction, "approve", "F")

    @discord.ui.button(label="Approve E", style=discord.ButtonStyle.success)
    async def approve_e(self, interaction: discord.Interaction, button: discord.ui.Button):
        await self._send_confirmation(interaction, "approve", "E")

    @discord.ui.button(label="Approve D", style=discord.ButtonStyle.success)
    async def approve_d(self, interaction: discord.Interaction, button: discord.ui.Button):
        await self._send_confirmation(interaction, "approve", "D")

    @discord.ui.button(label="Approve C", style=discord.ButtonStyle.success)
    async def approve_c(self, interaction: discord.Interaction, button: discord.ui.Button):
        await self._send_confirmation(interaction, "approve", "C")

    @discord.ui.button(label="Approve B", style=discord.ButtonStyle.success)
    async def approve_b(self, interaction: discord.Interaction, button: discord.ui.Button):
        await self._send_confirmation(interaction, "approve", "B")

    @discord.ui.button(label="Approve A", style=discord.ButtonStyle.success)
    async def approve_a(self, interaction: discord.Interaction, button: discord.ui.Button):
        await self._send_confirmation(interaction, "approve", "A")

    @discord.ui.button(label="Deny", style=discord.ButtonStyle.danger)
    async def deny(self, interaction: discord.Interaction, button: discord.ui.Button):
        await self._send_confirmation(interaction, "deny")


class QuestReviewConfirmView(discord.ui.View):
    def __init__(
        self,
        review_view: QuestReviewView,
        action: str,
        rank: str | None,
        channel_id: int,
        message_id: int,
    ) -> None:
        super().__init__(timeout=60)
        self.review_view = review_view
        self.action = action
        self.rank = rank
        self.channel_id = channel_id
        self.message_id = message_id

    @discord.ui.button(label="Confirm", style=discord.ButtonStyle.success)
    async def confirm(self, interaction: discord.Interaction, button: discord.ui.Button) -> None:
        if self.action == "approve" and self.rank:
            message = await self.review_view._approve(interaction, self.rank, self.channel_id, self.message_id)
        else:
            message = await self.review_view._deny(interaction, self.channel_id, self.message_id)
        await interaction.response.edit_message(content=message, view=None)

    @discord.ui.button(label="Cancel", style=discord.ButtonStyle.secondary)
    async def cancel(self, interaction: discord.Interaction, button: discord.ui.Button) -> None:
        await interaction.response.edit_message(content="Action canceled.", view=None)


class QuestCompletionReviewView(discord.ui.View):
    def __init__(self, bot, quest_id: str):
        super().__init__(timeout=None)
        self.bot = bot
        self.quest_id = quest_id

    @discord.ui.button(label="Approve Completion", style=discord.ButtonStyle.success)
    async def approve(self, interaction: discord.Interaction, button: discord.ui.Button):
        # Mark as completed and do rewards.
        await self.bot.db.update_quest_fields(self.quest_id, {"Status": "Completed"})
        quest = await self.bot.db.get_quest_by_id(self.quest_id)
        if quest:
            completion_channel = self.bot.get_channel(self.bot.config.quest_completion_channel_id)
            if completion_channel:
                await completion_channel.send(embed=quest_details_embed(self.bot.config, quest))
            board_message_id = quest.get("Board Message ID", "")
            if board_message_id:
                board_channel = self.bot.get_channel(self.bot.config.quest_board_channel_id)
                if board_channel:
                    try:
                        message = await board_channel.fetch_message(int(board_message_id))
                        await message.delete()
                    except (discord.NotFound, discord.Forbidden, discord.HTTPException):
                        pass
            points = rank_points(self.bot.config, quest.get("Quest Rank", ""))
            accepted_as = quest.get("Accepted As", "")
            if accepted_as.startswith("Party:"):
                party_id = accepted_as.split(":", 1)[1].strip()
                party = await self.bot.db.get_party_by_id(party_id)
                if party:
                    members = split_csv(party.get("Members", ""))
                    for member_id in members:
                        user = await self.bot.db.get_user_by_discord_id(member_id)
                        if not user:
                            continue
                        current_points = int(user.get("Rank Points", "0") or 0)
                        await self.bot.db.update_user_fields(member_id, {"Rank Points": str(current_points + points)})
                    party_points = int(party.get("Rank Points", "0") or 0)
                    await self.bot.db.update_party_fields(party_id, {"Rank Points": str(party_points + points)})
            else:
                completed_by = quest.get("Completed By", "")
                if completed_by.isdigit():
                    user = await self.bot.db.get_user_by_discord_id(completed_by)
                else:
                    user = await self.bot.db.get_user_by_username(completed_by) if completed_by else None
                if user:
                    current_points = int(user.get("Rank Points", "0") or 0)
                    await self.bot.db.update_user_fields(user.get("Discord ID", ""), {"Rank Points": str(current_points + points)})
        await interaction.response.send_message("Quest completion approved.", ephemeral=True)

    @discord.ui.button(label="Deny Completion", style=discord.ButtonStyle.danger)
    async def deny(self, interaction: discord.Interaction, button: discord.ui.Button):
        await self.bot.db.update_quest_fields(
            self.quest_id,
            {
                "Status": "In Progress",
                "Completion Date": "",
                "Completed By": "",
            },
        )
        await interaction.response.send_message("Quest completion denied.", ephemeral=True)


class QuestBoardView(discord.ui.View):
    def __init__(self, bot, quest_id: str):
        super().__init__(timeout=None)
        self.bot = bot
        self.quest_id = quest_id

    async def _update_board_message(self, quest: dict) -> None:
        board_message_id = quest.get("Board Message ID", "")
        if not board_message_id:
            return
        board_channel = self.bot.get_channel(self.bot.config.quest_board_channel_id)
        if not board_channel:
            return
        try:
            message = await board_channel.fetch_message(int(board_message_id))
            await message.edit(embed=quest_details_embed(self.bot.config, quest))
        except (discord.NotFound, discord.Forbidden, discord.HTTPException, ValueError):
            pass

    @discord.ui.button(label="Accept Solo", style=discord.ButtonStyle.primary)
    async def accept_solo(self, interaction: discord.Interaction, button: discord.ui.Button):
        db = self.bot.db
        quest = await db.get_quest_by_id(self.quest_id)
        if not quest or quest.get("Status") != "Active":
            await interaction.response.send_message("Quest is not available.", ephemeral=True)
            return
        user = await db.get_user_by_discord_id(str(interaction.user.id))
        if not user:
            await interaction.response.send_message("You must /signup before accepting quests.", ephemeral=True)
            return
        quest_rank = quest.get("Quest Rank", "")
        if not can_accept_rank(user.get("Rank", ""), quest_rank):
            await interaction.response.send_message(
                "You can only accept quests at your rank or one rank above.",
                ephemeral=True,
            )
            return
        await db.update_quest_fields(
            self.quest_id,
            {
                "Status": "In Progress",
                "Accepted By": interaction.user.name,
                "Accepted As": "Solo",
                "Acceptance Date": "=NOW()",
            },
        )
        quest = await db.get_quest_by_id(self.quest_id)
        if quest:
            await self._update_board_message(quest)
        deadline = add_days(now_utc(), self.bot.config.quest_deadline_days)
        try:
            await interaction.user.send(f"Quest accepted. Deadline: {format_dt(deadline)}")
        except discord.HTTPException:
            pass
        await interaction.response.send_message("Quest accepted.", ephemeral=True)

    @discord.ui.button(label="Accept as Party", style=discord.ButtonStyle.primary)
    async def accept_party(self, interaction: discord.Interaction, button: discord.ui.Button):
        db = self.bot.db
        quest = await db.get_quest_by_id(self.quest_id)
        if not quest or quest.get("Status") != "Active":
            await interaction.response.send_message("Quest is not available.", ephemeral=True)
            return
        user = await db.get_user_by_discord_id(str(interaction.user.id))
        if not user or user.get("Party") in {"", "None"}:
            await interaction.response.send_message("You must be in a party to accept as a group.", ephemeral=True)
            return
        party = await db.get_party_by_name(user.get("Party", ""))
        if not party:
            await interaction.response.send_message("Party not found.", ephemeral=True)
            return
        if hasattr(self.bot, "party_manager"):
            allowed = await self.bot.party_manager.check_party_permission(
                interaction.user.id, party.get("Party ID", ""), "quest_accept"
            )
            if not allowed:
                await interaction.response.send_message("You do not have permission to accept party quests.", ephemeral=True)
                return
        quest_rank = quest.get("Quest Rank", "")
        if not can_accept_rank(party.get("Rank", ""), quest_rank):
            await interaction.response.send_message(
                "Your party can only accept quests at its rank or one rank above.",
                ephemeral=True,
            )
            return
        await db.update_quest_fields(
            self.quest_id,
            {
                "Status": "In Progress",
                "Accepted By": party.get("Party Name", ""),
                "Accepted As": f"Party: {party.get('Party ID', '')}",
                "Acceptance Date": "=NOW()",
            },
        )
        quest = await db.get_quest_by_id(self.quest_id)
        if quest:
            await self._update_board_message(quest)
        deadline = add_days(now_utc(), self.bot.config.quest_deadline_days)
        members = split_csv(party.get("Members", ""))
        for member_id in members:
            try:
                member = self.bot.get_user(int(member_id))
                if member is None:
                    member = await self.bot.fetch_user(int(member_id))
                await member.send(f"Party quest accepted. Deadline: {format_dt(deadline)}")
            except (discord.HTTPException, discord.NotFound, discord.Forbidden, ValueError):
                continue
        await interaction.response.send_message("Quest accepted by your party.", ephemeral=True)

    @discord.ui.button(label="Details", style=discord.ButtonStyle.secondary)
    async def details(self, interaction: discord.Interaction, button: discord.ui.Button):
        db = self.bot.db
        quest = await db.get_quest_by_id(self.quest_id)
        if not quest:
            await interaction.response.send_message("Quest not found.", ephemeral=True)
            return
        embed = quest_details_embed(self.bot.config, quest)
        await interaction.response.send_message(embed=embed, ephemeral=True)


class AbandonQuestConfirmView(discord.ui.View):
    def __init__(self, bot, quest_id: str, reason: str, requester_id: int) -> None:
        super().__init__(timeout=60)
        self.bot = bot
        self.quest_id = quest_id
        self.reason = reason
        self.requester_id = requester_id

    async def _update_board_message(self, quest: dict) -> None:
        board_message_id = quest.get("Board Message ID", "")
        if not board_message_id:
            return
        board_channel = self.bot.get_channel(self.bot.config.quest_board_channel_id)
        if not board_channel:
            return
        try:
            message = await board_channel.fetch_message(int(board_message_id))
            await message.edit(embed=quest_details_embed(self.bot.config, quest))
        except (discord.NotFound, discord.Forbidden, discord.HTTPException, ValueError):
            pass

    @discord.ui.button(label="Confirm", style=discord.ButtonStyle.danger)
    async def confirm(self, interaction: discord.Interaction, button: discord.ui.Button) -> None:
        if interaction.user.id != self.requester_id:
            await interaction.response.send_message("Only the requester can confirm this action.", ephemeral=True)
            return
        # Double check status before we reset it.
        quest = await self.bot.db.get_quest_by_id(self.quest_id)
        if not quest or quest.get("Status") != "In Progress":
            await interaction.response.edit_message(content="Quest is no longer in progress.", view=None)
            return
        await self.bot.db.update_quest_fields(
            self.quest_id,
            {
                "Status": "Active",
                "Accepted By": "",
                "Accepted As": "",
                "Acceptance Date": "",
                "Deadline": "",
                "Abandon Reason": self.reason,
                "Abandoned By": interaction.user.name,
                "Abandon Date": format_dt(now_utc()),
            },
        )
        quest = await self.bot.db.get_quest_by_id(self.quest_id)
        if quest:
            await self._update_board_message(quest)
        await interaction.response.edit_message(content="Quest abandoned.", view=None)

    @discord.ui.button(label="Cancel", style=discord.ButtonStyle.secondary)
    async def cancel(self, interaction: discord.Interaction, button: discord.ui.Button) -> None:
        if interaction.user.id != self.requester_id:
            await interaction.response.send_message("Only the requester can cancel this action.", ephemeral=True)
            return
        await interaction.response.edit_message(content="Action canceled.", view=None)
