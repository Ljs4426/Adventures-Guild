from __future__ import annotations

import discord

from party_embeds import party_settings_embed


class PartyInviteView(discord.ui.View):
    def __init__(self, bot, invite_id: str, target_id: int):
        super().__init__(timeout=None)
        self.bot = bot
        self.invite_id = invite_id
        self.target_id = target_id

    @discord.ui.button(label="Accept", style=discord.ButtonStyle.success)
    async def accept(self, interaction: discord.Interaction, button: discord.ui.Button):
        if interaction.user.id != self.target_id:
            await interaction.response.send_message("This invite is not for you.", ephemeral=True)
            return
        result = await self.bot.invite_manager.process_invite_response(self.invite_id, accepted=True)
        await interaction.response.send_message(result, ephemeral=True)

    @discord.ui.button(label="Decline", style=discord.ButtonStyle.danger)
    async def decline(self, interaction: discord.Interaction, button: discord.ui.Button):
        if interaction.user.id != self.target_id:
            await interaction.response.send_message("This invite is not for you.", ephemeral=True)
            return
        result = await self.bot.invite_manager.process_invite_response(self.invite_id, accepted=False)
        await interaction.response.send_message(result, ephemeral=True)


class PartySettingsView(discord.ui.View):
    def __init__(self, bot, party_id: str, leader_id: int):
        super().__init__(timeout=None)
        self.bot = bot
        self.party_id = party_id
        self.leader_id = leader_id

    async def _toggle(self, interaction: discord.Interaction, setting_name: str, on_value: str, off_value: str):
        if interaction.user.id != self.leader_id:
            await interaction.response.send_message("Only the leader can modify settings.", ephemeral=True)
            return
        # Flip the setting between the two values.
        party = await self.bot.db.get_party_by_id(self.party_id)
        current = party.get(setting_name, off_value) if party else off_value
        new_value = on_value if current == off_value else off_value
        await self.bot.party_manager.update_party_setting(self.party_id, setting_name, new_value, interaction.user.name)
        updated_party = await self.bot.db.get_party_by_id(self.party_id)
        embed = party_settings_embed(self.bot.config, updated_party or {})
        await interaction.response.edit_message(embed=embed, view=self)

    @discord.ui.button(label="Toggle Quest Accept", style=discord.ButtonStyle.primary)
    async def toggle_accept(self, interaction: discord.Interaction, button: discord.ui.Button):
        await self._toggle(interaction, "Quest Accept Perm", "All Members", "Leader Only")

    @discord.ui.button(label="Toggle Quest Complete", style=discord.ButtonStyle.primary)
    async def toggle_complete(self, interaction: discord.Interaction, button: discord.ui.Button):
        await self._toggle(interaction, "Quest Complete Perm", "All Members", "Leader Only")

    @discord.ui.button(label="Toggle Quest Abandon", style=discord.ButtonStyle.primary)
    async def toggle_abandon(self, interaction: discord.Interaction, button: discord.ui.Button):
        await self._toggle(interaction, "Quest Abandon Perm", "All Members", "Leader Only")

    @discord.ui.button(label="Toggle Invite", style=discord.ButtonStyle.primary)
    async def toggle_invite(self, interaction: discord.Interaction, button: discord.ui.Button):
        await self._toggle(interaction, "Invite Perm", "All Members", "Leader Only")

    @discord.ui.button(label="Toggle Auto Distribute", style=discord.ButtonStyle.secondary)
    async def toggle_auto(self, interaction: discord.Interaction, button: discord.ui.Button):
        await self._toggle(interaction, "Auto Distribute", "Yes", "No")

    @discord.ui.button(label="Toggle Confirmation", style=discord.ButtonStyle.secondary)
    async def toggle_confirmation(self, interaction: discord.Interaction, button: discord.ui.Button):
        await self._toggle(interaction, "Require Confirmation", "Yes", "No")
