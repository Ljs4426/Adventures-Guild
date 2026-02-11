from __future__ import annotations

from datetime import datetime
from typing import Optional

import discord
from discord import app_commands
from discord.ext import commands

from party_embeds import (
    party_disbanded_embed,
    party_formed_embed,
    party_info_embed,
    party_permission_denied_embed,
    party_settings_embed,
)
from party_manager import PartyManager
from party_views import PartySettingsView
from utils import format_dt, now_utc


class PartyCommands(commands.Cog):
    def __init__(self, bot: commands.Bot, invite_manager) -> None:
        self.bot = bot
        self.invite_manager = invite_manager
        self.party_manager = PartyManager(bot)
        bot.party_manager = self.party_manager
        bot.invite_manager = invite_manager

    @app_commands.command(name="form-party", description="Create a new party")
    async def form_party(self, interaction: discord.Interaction, party_name: str, member1: discord.User) -> None:
        config = self.bot.config
        leader_user = await self.bot.db.get_user_by_discord_id(str(interaction.user.id))
        if leader_user and leader_user.get("Party") not in {"", "None"}:
            await interaction.response.send_message(
                embed=party_permission_denied_embed(config, "", "", "You are already in a party"),
                ephemeral=True,
            )
            return
        member_user = await self.bot.db.get_user_by_discord_id(str(member1.id))
        if member_user and member_user.get("Party") not in {"", "None"}:
            await interaction.response.send_message(
                embed=party_permission_denied_embed(config, "", "", "Member is already in a party"),
                ephemeral=True,
            )
            return
        members = [str(member1.id)]
        default_settings = {
            "quest_accept": config.default_quest_accept_perm,
            "quest_complete": config.default_quest_complete_perm,
            "quest_abandon": config.default_quest_abandon_perm,
            "invite": config.default_invite_perm,
            "auto_distribute": config.default_auto_distribute,
            "require_confirmation": config.default_require_confirmation,
        }
        created_date = now_utc()
        await self.bot.db.create_party(party_name, str(interaction.user.id), interaction.user.name, members, format_dt(created_date), default_settings)
        await self.bot.db.update_user_fields(str(interaction.user.id), {"Party": party_name, "Party Role": "Leader"})
        await self.bot.db.update_user_fields(str(member1.id), {"Party": party_name, "Party Role": "Member"})
        embed = party_formed_embed(
            config,
            "",
            party_name,
            interaction.user.name,
            [member1.name],
            created_date,
            default_settings,
        )
        channel = self.bot.get_channel(config.party_notifications_channel_id)
        if channel:
            notification_embed = party_formed_embed(
                config,
                "",
                party_name,
                interaction.user.name,
                [member1.name],
                created_date,
                default_settings,
                include_settings=False,
            )
            await channel.send(embed=notification_embed)
        await interaction.response.send_message(embed=embed, ephemeral=True)

    @app_commands.command(name="party-settings", description="View or update party settings")
    async def party_settings(self, interaction: discord.Interaction) -> None:
        config = self.bot.config
        user = await self.bot.db.get_user_by_discord_id(str(interaction.user.id))
        if not user or user.get("Party") in {"", "None"}:
            await interaction.response.send_message(embed=party_permission_denied_embed(config, "", "", "Not in a party"), ephemeral=True)
            return
        party = await self.bot.db.get_party_by_name(user.get("Party", ""))
        if not party:
            await interaction.response.send_message(embed=party_permission_denied_embed(config, "", "", "Party not found"), ephemeral=True)
            return
        leader_id = int(party.get("Leader Discord ID", "0") or 0)
        embed = party_settings_embed(config, party)
        view = PartySettingsView(self.bot, party.get("Party ID", ""), leader_id)
        await interaction.response.send_message(embed=embed, view=view, ephemeral=True)

    @app_commands.command(name="party-info", description="View party info")
    async def party_info(self, interaction: discord.Interaction, party_name: Optional[str] = None) -> None:
        config = self.bot.config
        if party_name:
            party = await self.bot.db.get_party_by_name(party_name)
        else:
            user = await self.bot.db.get_user_by_discord_id(str(interaction.user.id))
            party = await self.bot.db.get_party_by_name(user.get("Party", "")) if user else None
        if not party:
            await interaction.response.send_message(embed=party_permission_denied_embed(config, "", "", "Party not found"), ephemeral=True)
            return
        members = []
        for raw in (party.get("Members", "") or "").split(","):
            raw = raw.strip()
            if raw:
                members.append(raw)
        embed = party_info_embed(config, party, members, 0)
        await interaction.response.send_message(embed=embed, ephemeral=True)

    @app_commands.command(name="party-invite", description="Invite a user to your party")
    async def party_invite(self, interaction: discord.Interaction, user: discord.User) -> None:
        config = self.bot.config
        actor = await self.bot.db.get_user_by_discord_id(str(interaction.user.id))
        if not actor or actor.get("Party") in {"", "None"}:
            await interaction.response.send_message(embed=party_permission_denied_embed(config, "", "", "Not in a party"), ephemeral=True)
            return
        target_user = await self.bot.db.get_user_by_discord_id(str(user.id))
        if target_user and target_user.get("Party") not in {"", "None"}:
            await interaction.response.send_message(
                embed=party_permission_denied_embed(config, "", "", "User already in a party"),
                ephemeral=True,
            )
            return
        party = await self.bot.db.get_party_by_name(actor.get("Party", ""))
        if not party:
            await interaction.response.send_message(embed=party_permission_denied_embed(config, "", "", "Party not found"), ephemeral=True)
            return
        allowed = await self.party_manager.check_party_permission(interaction.user.id, party.get("Party ID", ""), "invite")
        if not allowed:
            await interaction.response.send_message(
                embed=party_permission_denied_embed(config, party.get("Party Name", ""), party.get("Leader Username", ""), "Invite Perm"),
                ephemeral=True,
            )
            return
        invite_id = await self.invite_manager.send_party_invite(party.get("Party ID", ""), user, interaction.user)
        if not invite_id:
            await interaction.response.send_message(embed=party_permission_denied_embed(config, "", "", "Invite failed"), ephemeral=True)
            return
        await interaction.response.send_message(f"Invite sent to {user.name}.", ephemeral=True)

    @app_commands.command(name="party-transfer-leader", description="Transfer party leadership")
    async def party_transfer_leader(self, interaction: discord.Interaction, new_leader: discord.User) -> None:
        config = self.bot.config
        actor = await self.bot.db.get_user_by_discord_id(str(interaction.user.id))
        if not actor or actor.get("Party") in {"", "None"}:
            await interaction.response.send_message(embed=party_permission_denied_embed(config, "", "", "Not in a party"), ephemeral=True)
            return
        party = await self.bot.db.get_party_by_name(actor.get("Party", ""))
        if not party:
            await interaction.response.send_message(embed=party_permission_denied_embed(config, "", "", "Party not found"), ephemeral=True)
            return
        if not await self.party_manager.is_party_leader(interaction.user.id, party.get("Party ID", "")):
            await interaction.response.send_message(
                embed=party_permission_denied_embed(config, party.get("Party Name", ""), party.get("Leader Username", ""), "Leader only"),
                ephemeral=True,
            )
            return
        ok = await self.party_manager.transfer_party_leadership(
            party.get("Party ID", ""),
            str(interaction.user.id),
            str(new_leader.id),
            new_leader.name,
        )
        if not ok:
            await interaction.response.send_message(embed=party_permission_denied_embed(config, "", "", "Transfer failed"), ephemeral=True)
            return
        await interaction.response.send_message("Leadership transferred.", ephemeral=True)

    @app_commands.command(name="party-disband", description="Disband your party")
    async def party_disband(self, interaction: discord.Interaction, reason: Optional[str] = None) -> None:
        config = self.bot.config
        actor = await self.bot.db.get_user_by_discord_id(str(interaction.user.id))
        if not actor or actor.get("Party") in {"", "None"}:
            await interaction.response.send_message(embed=party_permission_denied_embed(config, "", "", "Not in a party"), ephemeral=True)
            return
        party = await self.bot.db.get_party_by_name(actor.get("Party", ""))
        if not party:
            await interaction.response.send_message(embed=party_permission_denied_embed(config, "", "", "Party not found"), ephemeral=True)
            return
        if not await self.party_manager.is_party_leader(interaction.user.id, party.get("Party ID", "")):
            await interaction.response.send_message(
                embed=party_permission_denied_embed(config, party.get("Party Name", ""), party.get("Leader Username", ""), "Leader only"),
                ephemeral=True,
            )
            return
        members = []
        for raw in (party.get("Members", "") or "").split(","):
            raw = raw.strip()
            if raw:
                members.append(raw)
        leader_id = party.get("Leader Discord ID", "")
        notify_ids = [leader_id] + members if leader_id else members
        embed = party_disbanded_embed(
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
                await member.send(embed=embed)
            except (discord.HTTPException, discord.NotFound, discord.Forbidden, ValueError):
                continue
        ok = await self.party_manager.disband_party(
            party.get("Party ID", ""),
            interaction.user.name,
            reason or "Disbanded by leader",
        )
        if not ok:
            await interaction.response.send_message(embed=party_permission_denied_embed(config, "", "", "Disband failed"), ephemeral=True)
            return
        await interaction.response.send_message("Party disbanded.", ephemeral=True)
