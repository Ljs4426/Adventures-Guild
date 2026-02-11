from __future__ import annotations

from datetime import datetime
from typing import Dict, List, Optional

import discord

from utils import format_dt, mention, progress_bar


def basic_embed(title: str, description: str, color: int) -> discord.Embed:
    return discord.Embed(title=title, description=description, color=color)


def _format_user(value: str) -> str:
    if value and value.isdigit():
        return mention(int(value))
    return value


def _rank_emoji(config, rank: str) -> str:
    if not rank:
        return ""
    letter = rank.strip().upper()[:1]
    if letter == "F":
        return config.emoji_f_rank
    if letter == "E":
        return config.emoji_e_rank
    if letter == "D":
        return config.emoji_d_rank
    if letter == "C":
        return config.emoji_c_rank
    if letter == "B":
        return config.emoji_b_rank
    if letter == "A":
        return config.emoji_a_rank
    return ""


def _format_rank_display(config, rank: str) -> str:
    emoji = _rank_emoji(config, rank)
    if emoji:
        return f"{emoji} {rank}"
    return rank


def _format_false_rank_probability(raw: str) -> str:
    if not raw:
        return ""
    try:
        value = float(raw.replace("%", "").strip())
    except ValueError:
        return raw
    return f"{value:.2f}%"


def _is_accepted_status(status: str) -> bool:
    if status == "In Progress":
        return True
    if status == "Pending Completion":
        return True
    if status == "Completed":
        return True
    if status == "Overdue":
        return True
    return False


def _build_details_value(quest: Dict[str, str]) -> str:
    lines = []
    status = quest.get("Status", "")
    if status:
        lines.append(f"Status: {status}")
    # Keep the abandon reason visible when it exists.
    abandon_reason = quest.get("Abandon Reason", "")
    if abandon_reason:
        lines.append(f"Abandon Reason: {abandon_reason}")
    commissioned_by = quest.get("Commissioned By", "")
    if commissioned_by:
        lines.append(f"Commissioned By: {commissioned_by}")
    commission_type = quest.get("Commission Type", "")
    if commission_type:
        lines.append(f"Commission Type: {commission_type}")
    if quest.get("Acceptance Date"):
        accepted_by = _format_user(quest.get("Accepted By", ""))
        accepted_as = quest.get("Accepted As", "")
        deadline = quest.get("Deadline", "")
        if accepted_by:
            lines.append(f"Accepted By: {accepted_by}")
        if accepted_as:
            lines.append(f"Accepted As: {accepted_as}")
        if deadline:
            lines.append(f"Deadline: {deadline}")
    if quest.get("Completion Date"):
        completion_date = quest.get("Completion Date", "")
        completed_by = _format_user(quest.get("Completed By", ""))
        if completion_date:
            lines.append(f"Completion Date: {completion_date}")
        if completed_by:
            lines.append(f"Completed By: {completed_by}")
    return "\n".join(lines) if lines else "N/A"


def error_embed(config, message: str) -> discord.Embed:
    return basic_embed("Error", message, config.color_error)


def info_embed(config, message: str) -> discord.Embed:
    return basic_embed("Info", message, config.color_info)


def success_embed(config, message: str) -> discord.Embed:
    return basic_embed("Success", message, config.color_success)


def signup_embed(config, username: str, starting_rank: str, join_date: datetime) -> discord.Embed:
    embed = discord.Embed(
        title="Welcome to the Guild",
        color=config.color_success,
    )
    embed.add_field(name="Username", value=username, inline=False)
    embed.add_field(name="Starting Rank", value=starting_rank, inline=True)
    embed.add_field(name="Join Date", value=format_dt(join_date), inline=True)
    embed.add_field(
        name="Tips",
        value="Use /quest-board to browse quests and /profile to track progress.",
        inline=False,
    )
    return embed


def quest_review_embed(config, quest: Dict[str, str]) -> discord.Embed:
    title = "Quest Pending Review"
    embed = discord.Embed(title=title, description=quest.get("Quest Description", ""), color=config.color_warning)
    rank = quest.get("Quest Rank", "TBD")
    rank_display = _format_rank_display(config, rank)
    embed.add_field(name="Quest ID", value=quest.get("Quest ID", ""), inline=False)
    embed.add_field(name="Rank", value=rank_display, inline=False)
    embed.add_field(name="Reward", value=quest.get("Reward", ""), inline=False)
    embed.add_field(name="Commissioned By", value=quest.get("Commissioned By", ""), inline=False)
    false_rank_probability = _format_false_rank_probability(quest.get("False Rank Probability", ""))
    if false_rank_probability:
        embed.add_field(name="False Rank Probability", value=false_rank_probability, inline=False)
    embed.add_field(name="Details", value=_build_details_value(quest), inline=False)
    return embed


def quest_board_embed(config, quests: List[Dict[str, str]], page: int, total_pages: int, rank_filter: str, status_filter: str) -> discord.Embed:
    title = "Quest Board"
    desc = f"Rank filter: {rank_filter or 'all'} | Status filter: {status_filter or 'all'}"
    embed = discord.Embed(title=title, description=desc, color=config.color_info)
    if not quests:
        embed.add_field(name="No quests", value="No quests match the filter.", inline=False)
        return embed
    for quest in quests:
        quest_id = quest.get("Quest ID", "")
        rank = quest.get("Quest Rank", "")
        status = quest.get("Status", "")
        reward = quest.get("Reward", "")
        rank_display = _format_rank_display(config, rank)
        false_rank_probability = _format_false_rank_probability(quest.get("False Rank Probability", ""))
        lines = []
        if rank_display:
            lines.append(f"Rank: {rank_display}")
        if reward:
            lines.append(f"Reward: {reward}")
        if false_rank_probability:
            lines.append(f"False Rank Probability: {false_rank_probability}")
        if status:
            lines.append(f"Status: {status}")
        value = "\n".join(lines) if lines else "N/A"
        embed.add_field(name=quest_id, value=value, inline=False)
    embed.set_footer(text=f"Page {page}/{total_pages}")
    return embed


def quest_details_embed(config, quest: Dict[str, str]) -> discord.Embed:
    title = f"Quest {quest.get('Quest ID', '')}"
    status = quest.get("Status", "")
    color = 0x000000 if _is_accepted_status(status) else config.color_info
    embed = discord.Embed(title=title, description=quest.get("Quest Description", ""), color=color)
    rank = quest.get("Quest Rank", "")
    rank_display = _format_rank_display(config, rank)
    embed.add_field(name="Quest ID", value=quest.get("Quest ID", ""), inline=False)
    embed.add_field(name="Rank", value=rank_display, inline=False)
    embed.add_field(name="Reward", value=quest.get("Reward", ""), inline=False)
    embed.add_field(name="Commissioned By", value=quest.get("Commissioned By", ""), inline=False)
    false_rank_probability = _format_false_rank_probability(quest.get("False Rank Probability", ""))
    if false_rank_probability:
        embed.add_field(name="False Rank Probability", value=false_rank_probability, inline=False)
    if _is_accepted_status(status):
        embed.add_field(name="Details", value="Accepted - details hidden.", inline=False)
    else:
        embed.add_field(name="Details", value=_build_details_value(quest), inline=False)
    return embed


def quest_completion_review_embed(config, quest: Dict[str, str]) -> discord.Embed:
    title = f"Completion Review {quest.get('Quest ID', '')}"
    status = quest.get("Status", "")
    color = 0x000000 if _is_accepted_status(status) else config.color_warning
    embed = discord.Embed(title=title, description=quest.get("Quest Description", ""), color=color)
    rank_display = _format_rank_display(config, quest.get("Quest Rank", ""))
    embed.add_field(name="Quest ID", value=quest.get("Quest ID", ""), inline=False)
    embed.add_field(name="Rank", value=rank_display, inline=False)
    embed.add_field(name="Reward", value=quest.get("Reward", ""), inline=False)
    embed.add_field(name="Commissioned By", value=quest.get("Commissioned By", ""), inline=False)
    false_rank_probability = _format_false_rank_probability(quest.get("False Rank Probability", ""))
    if false_rank_probability:
        embed.add_field(name="False Rank Probability", value=false_rank_probability, inline=False)
    if _is_accepted_status(status):
        embed.add_field(name="Details", value="Accepted - details hidden.", inline=False)
    else:
        embed.add_field(name="Details", value=_build_details_value(quest), inline=False)
    return embed


def my_quests_embed(config, quests: List[Dict[str, str]]) -> discord.Embed:
    embed = discord.Embed(title="My Quests", color=config.color_info)
    if not quests:
        embed.add_field(name="No active quests", value="You have no active quests.", inline=False)
        return embed
    for quest in quests:
        quest_id = quest.get("Quest ID", "")
        rank = quest.get("Quest Rank", "")
        deadline = quest.get("Deadline", "") or "N/A"
        rank_display = _format_rank_display(config, rank)
        reward = quest.get("Reward", "")
        lines = [f"Rank: {rank_display}", f"Deadline: {deadline}"]
        if reward:
            lines.insert(1, f"Reward: {reward}")
        embed.add_field(name=quest_id, value="\n".join(lines), inline=False)
    return embed


def profile_embed(
    config,
    username: str,
    discord_tag: str,
    rank: str,
    points: int,
    next_threshold: int,
    completed: int,
    completion_rate: str,
    active_quests: str,
    party_name: str,
    party_role: str,
    join_date: str,
) -> discord.Embed:
    embed = discord.Embed(title="Adventurer Profile", color=config.color_info)
    embed.add_field(name="User", value=f"{username} ({discord_tag})", inline=False)
    embed.add_field(name="Rank", value=f"{rank} ({points}/{next_threshold})", inline=True)
    embed.add_field(name="Progress", value=progress_bar(points, next_threshold), inline=True)
    embed.add_field(name="Party", value=f"{party_name} ({party_role})", inline=False)
    embed.add_field(name="Completed Quests", value=str(completed), inline=True)
    embed.add_field(name="Completion Rate", value=completion_rate, inline=True)
    embed.add_field(name="Active Quests", value=active_quests or "0", inline=True)
    embed.add_field(name="Join Date", value=join_date, inline=False)
    return embed
