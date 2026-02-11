from __future__ import annotations

from datetime import datetime
from typing import Optional

import discord
from discord import app_commands
from discord.ext import commands

from embeds import (
    error_embed,
    info_embed,
    my_quests_embed,
    profile_embed,
    quest_completion_review_embed,
    quest_details_embed,
    quest_review_embed,
    signup_embed,
    success_embed,
)
from party_embeds import party_disbanded_embed, party_formed_embed
from utils import format_dt, now_utc
from views import AbandonQuestConfirmView, QuestBoardView, QuestReviewView

TEST_USER_ID = 1027732252685250560


class TestRunModal(discord.ui.Modal):
    def __init__(self, bot: commands.Bot) -> None:
        super().__init__(title="Run Test Script")
        self.bot = bot
        self.test_username = discord.ui.TextInput(label="Test Username", placeholder="TestUser", max_length=32)
        self.quest_description = discord.ui.TextInput(
            label="Quest Description",
            placeholder="Deliver supplies to the outpost.",
            style=discord.TextStyle.paragraph,
            max_length=200,
        )
        self.reward = discord.ui.TextInput(label="Reward", placeholder="100 gold", max_length=64)
        self.abandon_reason = discord.ui.TextInput(label="Abandon Reason", placeholder="Test run", max_length=120)
        self.member1_id = discord.ui.TextInput(label="Party Member Discord ID", placeholder="123456789012345678", max_length=20)
        self.add_item(self.test_username)
        self.add_item(self.quest_description)
        self.add_item(self.reward)
        self.add_item(self.abandon_reason)
        self.add_item(self.member1_id)

    async def _update_board_message(self, quest: dict) -> None:
        board_message_id = quest.get("Board Message ID", "")
        if not board_message_id:
            return
        board_channel = self.bot.get_channel(self.bot.config.quest_board_channel_id)
        if not board_channel:
            return
        try:
            message = await board_channel.fetch_message(int(board_message_id))
            await message.edit(embed=quest_details_embed(self.bot.config, quest), view=QuestBoardView(self.bot, quest.get("Quest ID", "")))
        except (discord.NotFound, discord.Forbidden, discord.HTTPException, ValueError):
            pass

    async def on_submit(self, interaction: discord.Interaction) -> None:
        config = self.bot.config
        await interaction.response.defer(ephemeral=True)
        if interaction.user.id != TEST_USER_ID:
            await interaction.followup.send(embed=error_embed(config, "Insufficient permissions."), ephemeral=True)
            return
        member1_id_raw = self.member1_id.value.strip()
        if not member1_id_raw.isdigit():
            await interaction.followup.send(embed=error_embed(config, "Member ID must be numeric."), ephemeral=True)
            return
        member1_id = int(member1_id_raw)
        summary = []
        test_username = self.test_username.value.strip()
        quest_description = self.quest_description.value.strip()
        reward = self.reward.value.strip()
        abandon_reason = self.abandon_reason.value.strip()
        leader_id = str(interaction.user.id)

        # Make sure the test user exists and isn't already in a party.
        leader_user = await self.bot.db.get_user_by_discord_id(leader_id)
        if not leader_user:
            await self.bot.db.create_user(test_username, leader_id, format_dt(now_utc()))
            summary.append("Created test user.")
        elif leader_user.get("Party") not in {"", "None"}:
            await interaction.followup.send(embed=error_embed(config, "Test user is already in a party."), ephemeral=True)
            return

        # Make sure the second user exists and isn't already in a party.
        member1 = self.bot.get_user(member1_id)
        if member1 is None:
            try:
                member1 = await self.bot.fetch_user(member1_id)
            except (discord.NotFound, discord.Forbidden, discord.HTTPException, ValueError):
                await interaction.followup.send(embed=error_embed(config, "Member user not found."), ephemeral=True)
                return
        member1_db = await self.bot.db.get_user_by_discord_id(str(member1_id))
        if not member1_db:
            await self.bot.db.create_user(member1.name, str(member1_id), format_dt(now_utc()))
            summary.append("Created member user.")
        elif member1_db.get("Party") not in {"", "None"}:
            await interaction.followup.send(embed=error_embed(config, "Member is already in a party."), ephemeral=True)
            return

        # Quest flow: commission -> approve -> accept -> abandon -> edit.
        await self.bot.db.create_quest(
            quest_description,
            reward,
            "Player",
            interaction.user.name,
            format_dt(now_utc()),
            "Pending Review",
        )
        quest_rows = await self.bot.db.sheets.get_rows_as_dicts(config.quests_sheet_name)
        quest = quest_rows[-1] if quest_rows else {}
        quest_id = quest.get("Quest ID", "")
        if not quest_id:
            await interaction.followup.send(embed=error_embed(config, "Quest creation failed."), ephemeral=True)
            return
        summary.append(f"Commissioned quest {quest_id}.")

        review_channel = self.bot.get_channel(config.quest_review_channel_id)
        review_message = None
        if review_channel:
            review_message = await review_channel.send(embed=quest_review_embed(config, quest))
        else:
            summary.append("Review channel not found.")

        await self.bot.db.update_quest_fields(quest_id, {"Quest Rank": "F", "Status": "Active", "Assigned By": interaction.user.name})
        quest = await self.bot.db.get_quest_by_id(quest_id)
        if quest:
            board_channel = self.bot.get_channel(config.quest_board_channel_id)
            if board_channel:
                board_message = await board_channel.send(embed=quest_details_embed(config, quest), view=QuestBoardView(self.bot, quest_id))
                await self.bot.db.update_quest_fields(quest_id, {"Board Message ID": str(board_message.id)})
            else:
                summary.append("Board channel not found.")
        if review_message:
            try:
                await review_message.delete()
            except (discord.NotFound, discord.Forbidden, discord.HTTPException):
                pass

        await self.bot.db.update_quest_fields(
            quest_id,
            {
                "Status": "In Progress",
                "Accepted By": interaction.user.name,
                "Accepted As": "Solo",
                "Acceptance Date": "=NOW()",
            },
        )
        quest = await self.bot.db.get_quest_by_id(quest_id)
        if quest:
            await self._update_board_message(quest)
        summary.append("Accepted quest.")

        await self.bot.db.update_quest_fields(
            quest_id,
            {
                "Status": "Active",
                "Accepted By": "",
                "Accepted As": "",
                "Acceptance Date": "",
                "Deadline": "",
                "Abandon Reason": abandon_reason,
                "Abandoned By": interaction.user.name,
                "Abandon Date": format_dt(now_utc()),
            },
        )
        quest = await self.bot.db.get_quest_by_id(quest_id)
        if quest:
            await self._update_board_message(quest)
        summary.append("Abandoned quest with reason.")

        await self.bot.db.update_quest_fields(
            quest_id,
            {
                "Quest Rank": "E",
                "Reward": reward,
                "False Rank Probability": "12.34",
            },
        )
        quest = await self.bot.db.get_quest_by_id(quest_id)
        if quest:
            await self._update_board_message(quest)
        summary.append("Edited quest details.")

        # Party flow: create -> transfer leader -> disband.
        party_name = f"{test_username}-party"
        default_settings = {
            "quest_accept": config.default_quest_accept_perm,
            "quest_complete": config.default_quest_complete_perm,
            "quest_abandon": config.default_quest_abandon_perm,
            "invite": config.default_invite_perm,
            "auto_distribute": config.default_auto_distribute,
            "require_confirmation": config.default_require_confirmation,
        }
        created_date = now_utc()
        await self.bot.db.create_party(
            party_name,
            leader_id,
            interaction.user.name,
            [str(member1_id)],
            format_dt(created_date),
            default_settings,
        )
        await self.bot.db.update_user_fields(leader_id, {"Party": party_name, "Party Role": "Leader"})
        await self.bot.db.update_user_fields(str(member1_id), {"Party": party_name, "Party Role": "Member"})
        party = await self.bot.db.get_party_by_name(party_name)
        if not party:
            await interaction.followup.send(embed=error_embed(config, "Party creation failed."), ephemeral=True)
            return
        notify_channel = self.bot.get_channel(config.party_notifications_channel_id)
        if notify_channel:
            await notify_channel.send(
                embed=party_formed_embed(
                    config,
                    party.get("Party ID", ""),
                    party_name,
                    interaction.user.name,
                    [member1.name],
                    created_date,
                    default_settings,
                    include_settings=False,
                )
            )
        summary.append("Formed party.")

        if hasattr(self.bot, "party_manager"):
            await self.bot.party_manager.transfer_party_leadership(
                party.get("Party ID", ""),
                leader_id,
                str(member1_id),
                member1.name,
            )
            summary.append("Transferred leadership.")
        else:
            summary.append("Party manager not available; skipped leadership transfer.")

        party = await self.bot.db.get_party_by_name(party_name)
        if party:
            members = [m.strip() for m in (party.get("Members", "") or "").split(",") if m.strip()]
            leader_discord_id = party.get("Leader Discord ID", "")
            notify_ids = [leader_discord_id] + members if leader_discord_id else members
            disband_embed = party_disbanded_embed(
                config,
                party.get("Party Name", ""),
                interaction.user.name,
                now_utc(),
                party.get("Rank", ""),
                party.get("Rank Points", ""),
                party.get("Completed Quests #", "0"),
            )
            for member_id in notify_ids:
                try:
                    member = self.bot.get_user(int(member_id))
                    if member is None:
                        member = await self.bot.fetch_user(int(member_id))
                    await member.send(embed=disband_embed)
                except (discord.HTTPException, discord.NotFound, discord.Forbidden, ValueError):
                    continue
        if party and hasattr(self.bot, "party_manager"):
            await self.bot.party_manager.disband_party(
                party.get("Party ID", ""),
                interaction.user.name,
                "Test run",
            )
            summary.append("Disbanded party.")
        else:
            summary.append("Party manager not available; skipped disband.")

        await interaction.followup.send(embed=success_embed(config, "Test run completed."), ephemeral=True)
        if summary:
            await interaction.followup.send("\n".join(summary), ephemeral=True)


class QuestCommands(commands.Cog):
    def __init__(self, bot: commands.Bot) -> None:
        self.bot = bot

    def _has_admin_or_mod(self, interaction: discord.Interaction) -> bool:
        if not isinstance(interaction.user, discord.Member):
            return False
        role_ids = {self.bot.config.admin_role_id, self.bot.config.mod_role_id}
        return any(role.id in role_ids for role in interaction.user.roles)

    @app_commands.command(name="signup", description="Register as a new adventurer")
    async def signup(self, interaction: discord.Interaction, username: str) -> None:
        config = self.bot.config
        existing = await self.bot.db.get_user_by_discord_id(str(interaction.user.id))
        if existing:
            await interaction.response.send_message(embed=info_embed(config, "You are already registered."), ephemeral=True)
            return
        join_date = now_utc()
        await self.bot.db.create_user(username, str(interaction.user.id), format_dt(join_date))
        embed = signup_embed(config, username, "F", join_date)
        channel = self.bot.get_channel(config.welcome_channel_id)
        if channel:
            await channel.send(embed=embed)
        await interaction.response.send_message(embed=success_embed(config, "Registration complete."), ephemeral=True)

    @app_commands.command(name="commission-quest", description="Commission a quest for review")
    async def commission_quest(self, interaction: discord.Interaction, description: str, reward: str) -> None:
        config = self.bot.config
        await self.bot.db.create_quest(description, reward, "Player", interaction.user.name, format_dt(now_utc()), "Pending Review")
        quest_rows = await self.bot.db.sheets.get_rows_as_dicts(config.quests_sheet_name)
        quest = quest_rows[-1] if quest_rows else {}
        embed = quest_review_embed(config, quest)
        view = QuestReviewView(self.bot, quest.get("Quest ID", ""))
        review_channel = self.bot.get_channel(config.quest_review_channel_id)
        if review_channel:
            await review_channel.send(embed=embed, view=view)
        await interaction.response.send_message(embed=success_embed(config, "Quest submitted for review."), ephemeral=True)

    @app_commands.command(name="quest-edit", description="Edit quest details (admin/mod only)")
    async def quest_edit(
        self,
        interaction: discord.Interaction,
        quest_id: str,
        rank: Optional[str] = None,
        reward: Optional[str] = None,
        false_rank_probability: Optional[str] = None,
    ) -> None:
        config = self.bot.config
        if not self._has_admin_or_mod(interaction):
            await interaction.response.send_message(embed=error_embed(config, "Insufficient permissions."), ephemeral=True)
            return
        updates = {}
        if rank:
            updates["Quest Rank"] = rank.strip().upper()
        if reward:
            updates["Reward"] = reward
        if false_rank_probability is not None:
            updates["False Rank Probability"] = false_rank_probability
        if not updates:
            await interaction.response.send_message(embed=info_embed(config, "No changes provided."), ephemeral=True)
            return
        quest = await self.bot.db.get_quest_by_id(quest_id)
        if not quest:
            await interaction.response.send_message(embed=error_embed(config, "Quest not found."), ephemeral=True)
            return
        await self.bot.db.update_quest_fields(quest_id, updates)
        quest = await self.bot.db.get_quest_by_id(quest_id)
        if quest:
            board_message_id = quest.get("Board Message ID", "")
            if board_message_id:
                board_channel = self.bot.get_channel(config.quest_board_channel_id)
                if board_channel:
                    try:
                        message = await board_channel.fetch_message(int(board_message_id))
                        await message.edit(embed=quest_details_embed(config, quest))
                    except (discord.NotFound, discord.Forbidden, discord.HTTPException, ValueError):
                        pass
        await interaction.response.send_message(embed=success_embed(config, "Quest updated."), ephemeral=True)

    @app_commands.command(name="abandon-quest", description="Abandon an in-progress quest")
    async def abandon_quest(self, interaction: discord.Interaction, quest_id: str, reason: str) -> None:
        config = self.bot.config
        quest = await self.bot.db.get_quest_by_id(quest_id)
        if not quest or quest.get("Status") != "In Progress":
            await interaction.response.send_message(embed=error_embed(config, "Quest is not in progress."), ephemeral=True)
            return
        view = AbandonQuestConfirmView(self.bot, quest_id, reason, interaction.user.id)
        await interaction.response.send_message(
            f"Confirm abandoning quest {quest_id}? Reason: {reason}",
            ephemeral=True,
            view=view,
        )

    @app_commands.command(name="complete-quest", description="Complete a quest")
    async def complete_quest(self, interaction: discord.Interaction, quest_id: str) -> None:
        config = self.bot.config
        quest = await self.bot.db.get_quest_by_id(quest_id)
        if not quest:
            await interaction.response.send_message(embed=error_embed(config, "Quest not found."), ephemeral=True)
            return
        status = quest.get("Status", "")
        if status in {"Completed", "Pending Completion"}:
            await interaction.response.send_message(
                embed=info_embed(config, "This quest already has a completion request or is completed."),
                ephemeral=True,
            )
            return
        await self.bot.db.update_quest_fields(
            quest_id,
            {
                "Status": "Pending Completion",
                "Completion Date": format_dt(now_utc()),
                "Completed By": str(interaction.user.id),
            },
        )
        quest = await self.bot.db.get_quest_by_id(quest_id)
        embed = quest_completion_review_embed(config, quest)
        review_channel = self.bot.get_channel(config.quest_review_channel_id)
        if review_channel:
            from views import QuestCompletionReviewView

            view = QuestCompletionReviewView(self.bot, quest_id)
            await review_channel.send(embed=embed, view=view)
        await interaction.response.send_message(embed=success_embed(config, "Completion submitted for guild review."), ephemeral=True)

    @app_commands.command(name="quest-board", description="List quests")
    async def quest_board(self, interaction: discord.Interaction, status_filter: Optional[str] = None) -> None:
        config = self.bot.config
        status = status_filter or "Active"
        quests = await self.bot.db.list_quests_by_status(status)
        embed = quest_details_embed(config, quests[0]) if quests else info_embed(config, "No quests found.")
        view = QuestBoardView(self.bot, quests[0].get("Quest ID", "")) if quests else None
        await interaction.response.send_message(embed=embed, view=view, ephemeral=True)

    @app_commands.command(name="my-quests", description="View your active quests")
    async def my_quests(self, interaction: discord.Interaction) -> None:
        config = self.bot.config
        user = await self.bot.db.get_user_by_discord_id(str(interaction.user.id))
        if not user:
            await interaction.response.send_message(embed=info_embed(config, "You are not registered."), ephemeral=True)
            return
        in_progress = await self.bot.db.list_quests_by_status("In Progress")
        overdue = await self.bot.db.list_quests_by_status("Overdue")
        quests = in_progress + overdue
        party_id = None
        if user.get("Party") not in {"", "None"}:
            party = await self.bot.db.get_party_by_name(user.get("Party", ""))
            if party:
                party_id = party.get("Party ID", "")
        username = user.get("Username", interaction.user.name)
        filtered = []
        for quest in quests:
            accepted_as = quest.get("Accepted As", "")
            if accepted_as.startswith("Party:") and party_id:
                if accepted_as.split(":", 1)[1].strip() == party_id:
                    filtered.append(quest)
            elif accepted_as == "Solo":
                if quest.get("Accepted By", "") in {interaction.user.name, username}:
                    filtered.append(quest)
        embed = my_quests_embed(config, filtered)
        await interaction.response.send_message(embed=embed, ephemeral=True)

    @app_commands.command(name="profile", description="View your adventurer profile")
    async def profile(self, interaction: discord.Interaction, user: Optional[discord.User] = None) -> None:
        config = self.bot.config
        target = user or interaction.user
        data = await self.bot.db.get_user_by_discord_id(str(target.id))
        if not data:
            await interaction.response.send_message(embed=info_embed(config, "User is not registered."), ephemeral=True)
            return
        rank = data.get("Rank", "F")
        points = int(data.get("Rank Points", "0") or 0)
        thresholds = {
            "F": config.e_rank_threshold,
            "E": config.d_rank_threshold,
            "D": config.c_rank_threshold,
            "C": config.b_rank_threshold,
            "B": config.a_rank_threshold,
            "A": max(points, config.a_rank_threshold),
        }
        next_threshold = thresholds.get(rank, max(points, config.a_rank_threshold))
        embed = profile_embed(
            config,
            data.get("Username", target.name),
            str(target),
            rank,
            points,
            next_threshold,
            int(data.get("Completed Quests #", "0") or 0),
            data.get("Completion Rate", "N/A"),
            data.get("Active Quests", "0"),
            data.get("Party", "None"),
            data.get("Party Role", "None"),
            data.get("Join Date", ""),
        )
        await interaction.response.send_message(embed=embed, ephemeral=True)

    @app_commands.command(name="test", description="Run a full automated test flow")
    async def test(self, interaction: discord.Interaction) -> None:
        config = self.bot.config
        if interaction.user.id != TEST_USER_ID:
            await interaction.response.send_message(embed=error_embed(config, "Insufficient permissions."), ephemeral=True)
            return
        await interaction.response.send_modal(TestRunModal(self.bot))
