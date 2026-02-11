from __future__ import annotations

from datetime import datetime
from typing import Dict, List

import discord

from utils import format_dt, progress_bar


def party_formed_embed(
    config,
    party_id: str,
    party_name: str,
    leader_name: str,
    members: List[str],
    created_date: datetime,
    settings: Dict[str, str],
    include_settings: bool = True,
) -> discord.Embed:
    embed = discord.Embed(title="New Party Formed", color=config.color_party)
    embed.add_field(name="Party", value=f"{party_name} ({party_id})", inline=False)
    embed.add_field(name="Leader", value=leader_name, inline=False)
    embed.add_field(name="Members", value="\n".join(members), inline=False)
    embed.add_field(name="Starting Rank", value="F", inline=True)
    embed.add_field(name="Formed", value=format_dt(created_date), inline=True)
    if include_settings:
        rows = []
        rows.append(f"Quest Accept: {settings.get('quest_accept', '')}")
        rows.append(f"Quest Complete: {settings.get('quest_complete', '')}")
        rows.append(f"Quest Abandon: {settings.get('quest_abandon', '')}")
        rows.append(f"Invite: {settings.get('invite', '')}")
        rows.append(f"Auto Distribute: {settings.get('auto_distribute', '')}")
        rows.append(f"Require Confirmation: {settings.get('require_confirmation', '')}")
        settings_text = "\n".join(rows)
        embed.add_field(name="Settings", value=settings_text, inline=False)
    return embed


def party_invite_embed(config, party_name: str, leader_name: str, party_rank: str, completed: str, members: List[str], expires_in_hours: int) -> discord.Embed:
    embed = discord.Embed(title="Party Invitation", color=config.color_party)
    embed.add_field(name="Party", value=party_name, inline=True)
    embed.add_field(name="Leader", value=leader_name, inline=True)
    embed.add_field(name="Rank", value=party_rank, inline=True)
    embed.add_field(name="Completed Quests", value=completed, inline=True)
    embed.add_field(name="Members", value="\n".join(members), inline=False)
    embed.set_footer(text=f"Expires in {expires_in_hours} hours")
    return embed


def party_settings_embed(config, party: Dict[str, str]) -> discord.Embed:
    embed = discord.Embed(title="Party Settings", color=config.color_party)
    embed.add_field(name="Party", value=party.get("Party Name", ""), inline=False)
    embed.add_field(name="Leader", value=party.get("Leader Username", ""), inline=False)
    rows = []
    rows.append(f"Quest Accept: {party.get('Quest Accept Perm', '')}")
    rows.append(f"Quest Complete: {party.get('Quest Complete Perm', '')}")
    rows.append(f"Quest Abandon: {party.get('Quest Abandon Perm', '')}")
    rows.append(f"Invite: {party.get('Invite Perm', '')}")
    rows.append(f"Auto Distribute: {party.get('Auto Distribute', '')}")
    rows.append(f"Require Confirmation: {party.get('Require Confirmation', '')}")
    settings_text = "\n".join(rows)
    embed.add_field(name="Settings", value=settings_text, inline=False)
    embed.set_footer(text=f"Last Updated: {party.get('Last Settings Update', '')} by {party.get('Settings Updated By', '')}")
    return embed


def party_info_embed(config, party: Dict[str, str], members: List[str], next_threshold: int) -> discord.Embed:
    embed = discord.Embed(title="Party Info", color=config.color_party)
    embed.add_field(name="Party", value=f"{party.get('Party Name', '')} ({party.get('Party ID', '')})", inline=False)
    embed.add_field(name="Leader", value=party.get("Leader Username", ""), inline=True)
    embed.add_field(name="Members", value="\n".join(members), inline=False)
    points = int(party.get("Rank Points", "0") or 0)
    embed.add_field(name="Rank", value=f"{party.get('Rank', '')} ({points}/{next_threshold})", inline=True)
    embed.add_field(name="Progress", value=progress_bar(points, next_threshold), inline=True)
    embed.add_field(name="Completed Quests", value=party.get("Completed Quests #", "0"), inline=True)
    embed.add_field(name="Completion Rate", value=party.get("Completion Rate", "N/A"), inline=True)
    embed.add_field(name="Active Quests", value=party.get("Active Quests", "0"), inline=True)
    embed.add_field(name="Formed", value=party.get("Created Date", ""), inline=True)
    return embed


def party_log_embed(config, party_name: str, days: int, events: List[str], include_settings: bool, include_admin: bool) -> discord.Embed:
    embed = discord.Embed(title="Party Activity Log", color=config.color_info)
    embed.add_field(name="Party", value=party_name, inline=True)
    embed.add_field(name="Window", value=f"Last {days} days", inline=True)
    log_text = "\n".join(events) if events else "No recent activity."
    embed.add_field(name="Events", value=log_text, inline=False)
    if include_settings:
        embed.add_field(name="Settings", value="Leader view enabled", inline=False)
    if include_admin:
        embed.add_field(name="Admin", value="Leader view enabled", inline=False)
    return embed


def party_permission_denied_embed(config, party_name: str, leader_name: str, setting_name: str) -> discord.Embed:
    embed = discord.Embed(title="Permission Denied", color=config.color_error)
    embed.add_field(name="Party", value=party_name, inline=False)
    embed.add_field(name="Setting", value=setting_name, inline=False)
    embed.add_field(name="Leader", value=leader_name, inline=False)
    embed.add_field(
        name="Tip",
        value="Ask the party leader to perform this action or update permissions.",
        inline=False,
    )
    return embed


def leadership_transfer_embed(config, party_name: str, old_leader: str, new_leader: str, when: datetime) -> discord.Embed:
    embed = discord.Embed(title="Leadership Transferred", color=config.color_party)
    embed.add_field(name="Party", value=party_name, inline=False)
    embed.add_field(name="Old Leader", value=old_leader, inline=True)
    embed.add_field(name="New Leader", value=new_leader, inline=True)
    embed.add_field(name="Date", value=format_dt(when), inline=False)
    return embed


def member_kicked_embed(config, party_name: str, removed_by: str, when: datetime, reason: str) -> discord.Embed:
    embed = discord.Embed(title="Removed From Party", color=config.color_warning)
    embed.add_field(name="Party", value=party_name, inline=False)
    embed.add_field(name="Removed By", value=removed_by, inline=True)
    embed.add_field(name="Date", value=format_dt(when), inline=True)
    embed.add_field(name="Reason", value=reason or "No reason provided", inline=False)
    return embed


def party_disbanded_embed(config, party_name: str, disbanded_by: str, when: datetime, final_rank: str, total_points: str, completed: str) -> discord.Embed:
    embed = discord.Embed(title="Party Disbanded", color=config.color_warning)
    embed.add_field(name="Party", value=party_name, inline=False)
    embed.add_field(name="Disbanded By", value=disbanded_by, inline=True)
    embed.add_field(name="Date", value=format_dt(when), inline=True)
    embed.add_field(name="Final Rank", value=final_rank, inline=True)
    embed.add_field(name="Total Points", value=total_points, inline=True)
    embed.add_field(name="Completed Quests", value=completed, inline=True)
    return embed
