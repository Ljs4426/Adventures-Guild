from __future__ import annotations

import os
from dataclasses import dataclass
from datetime import datetime, timezone, timedelta
from typing import Iterable, List, Optional


def _get_env(name: str, default: Optional[str] = None) -> str:
    # Basic env getter with a default.
    value = os.getenv(name)
    if value is None:
        return default if default is not None else ""
    return value


def _get_int(name: str, default: int) -> int:
    try:
        return int(_get_env(name, str(default)).strip())
    except ValueError:
        return default


def _get_float(name: str, default: float) -> float:
    try:
        return float(_get_env(name, str(default)).strip())
    except ValueError:
        return default


def _get_bool(name: str, default: bool) -> bool:
    raw = _get_env(name, str(default)).strip().lower()
    if raw in {"1", "true", "yes", "y", "on"}:
        return True
    return False


@dataclass(frozen=True)
class Config:
    discord_bot_token: str
    google_sheets_id: str
    google_credentials_file: str

    quests_sheet_name: str
    users_sheet_name: str
    parties_sheet_name: str
    config_sheet_name: str
    logs_sheet_name: str
    deadlines_sheet_name: str
    party_invites_sheet_name: str
    archived_parties_sheet_name: str

    quest_board_channel_id: int
    quest_review_channel_id: int
    party_notifications_channel_id: int
    quest_completion_channel_id: int
    welcome_channel_id: int
    log_channel_id: int

    admin_role_id: int
    mod_role_id: int

    max_party_size: int
    quest_reward_tier_low: int
    quest_reward_tier_med: int
    quest_reward_tier_high: int
    quest_deadline_days: int
    deadline_warning_hours: int
    max_active_quests_user: int
    max_active_quests_party: int

    default_quest_accept_perm: str
    default_quest_complete_perm: str
    default_quest_abandon_perm: str
    default_invite_perm: str
    default_auto_distribute: str
    default_require_confirmation: str
    party_invite_expiry_hours: int

    deadline_check_interval: int
    invite_check_interval: int

    points_per_f_quest: int
    points_per_e_quest: int
    points_per_d_quest: int
    points_per_c_quest: int
    points_per_b_quest: int
    points_per_a_quest: int

    f_rank_threshold: int
    e_rank_threshold: int
    d_rank_threshold: int
    c_rank_threshold: int
    b_rank_threshold: int
    a_rank_threshold: int

    on_time_bonus_multiplier: float
    late_penalty_multiplier: float
    abandon_penalty_enabled: bool
    abandon_penalty_points: int

    color_f_rank: int
    color_e_rank: int
    color_d_rank: int
    color_c_rank: int
    color_b_rank: int
    color_a_rank: int
    color_success: int
    color_error: int
    color_warning: int
    color_info: int
    color_guild_quest: int
    color_in_progress: int
    color_overdue: int
    color_claimed: int
    color_party: int

    emoji_f_rank: str
    emoji_e_rank: str
    emoji_d_rank: str
    emoji_c_rank: str
    emoji_b_rank: str
    emoji_a_rank: str
    emoji_guild_quest: str
    emoji_warning: str
    emoji_party: str
    emoji_complete: str
    emoji_claimed: str
    emoji_overdue: str
    emoji_solo: str
    emoji_leader: str
    emoji_member: str

    command_prefix: str
    bot_status: str
    enable_sheet_logging: bool
    enable_channel_logging: bool
    log_level: str


def load_config() -> Config:
    return Config(
        discord_bot_token=_get_env("DISCORD_BOT_TOKEN"),
        google_sheets_id=_get_env("GOOGLE_SHEETS_ID"),
        google_credentials_file=_get_env("GOOGLE_CREDENTIALS_FILE", "credentials.json"),
        quests_sheet_name=_get_env("QUESTS_SHEET_NAME", "Quests"),
        users_sheet_name=_get_env("USERS_SHEET_NAME", "Users"),
        parties_sheet_name=_get_env("PARTIES_SHEET_NAME", "Parties"),
        config_sheet_name=_get_env("CONFIG_SHEET_NAME", "Config"),
        logs_sheet_name=_get_env("LOGS_SHEET_NAME", "Logs"),
        deadlines_sheet_name=_get_env("DEADLINES_SHEET_NAME", "Deadlines"),
        party_invites_sheet_name=_get_env("PARTY_INVITES_SHEET_NAME", "Party Invites"),
        archived_parties_sheet_name=_get_env("ARCHIVED_PARTIES_SHEET_NAME", "Archived Parties"),
        quest_board_channel_id=_get_int("QUEST_BOARD_CHANNEL_ID", 0),
        quest_review_channel_id=_get_int("QUEST_REVIEW_CHANNEL_ID", 0),
        party_notifications_channel_id=_get_int("PARTY_NOTIFICATIONS_CHANNEL_ID", 0),
        quest_completion_channel_id=_get_int("QUEST_COMPLETION_CHANNEL_ID", 0),
        welcome_channel_id=_get_int("WELCOME_CHANNEL_ID", 0),
        log_channel_id=_get_int("LOG_CHANNEL_ID", 0),
        admin_role_id=_get_int("ADMIN_ROLE_ID", 0),
        mod_role_id=_get_int("MOD_ROLE_ID", 0),
        max_party_size=_get_int("MAX_PARTY_SIZE", 6),
        quest_reward_tier_low=_get_int("QUEST_REWARD_TIER_LOW", 100),
        quest_reward_tier_med=_get_int("QUEST_REWARD_TIER_MED", 500),
        quest_reward_tier_high=_get_int("QUEST_REWARD_TIER_HIGH", 1000),
        quest_deadline_days=_get_int("QUEST_DEADLINE_DAYS", 3),
        deadline_warning_hours=_get_int("DEADLINE_WARNING_HOURS", 24),
        max_active_quests_user=_get_int("MAX_ACTIVE_QUESTS_USER", 3),
        max_active_quests_party=_get_int("MAX_ACTIVE_QUESTS_PARTY", 5),
        default_quest_accept_perm=_get_env("DEFAULT_QUEST_ACCEPT_PERM", "Leader Only"),
        default_quest_complete_perm=_get_env("DEFAULT_QUEST_COMPLETE_PERM", "Leader Only"),
        default_quest_abandon_perm=_get_env("DEFAULT_QUEST_ABANDON_PERM", "Leader Only"),
        default_invite_perm=_get_env("DEFAULT_INVITE_PERM", "Leader Only"),
        default_auto_distribute=_get_env("DEFAULT_AUTO_DISTRIBUTE", "Yes"),
        default_require_confirmation=_get_env("DEFAULT_REQUIRE_CONFIRMATION", "No"),
        party_invite_expiry_hours=_get_int("PARTY_INVITE_EXPIRY_HOURS", 24),
        deadline_check_interval=_get_int("DEADLINE_CHECK_INTERVAL", 60),
        invite_check_interval=_get_int("INVITE_CHECK_INTERVAL", 60),
        points_per_f_quest=_get_int("POINTS_PER_F_QUEST", 10),
        points_per_e_quest=_get_int("POINTS_PER_E_QUEST", 25),
        points_per_d_quest=_get_int("POINTS_PER_D_QUEST", 50),
        points_per_c_quest=_get_int("POINTS_PER_C_QUEST", 100),
        points_per_b_quest=_get_int("POINTS_PER_B_QUEST", 200),
        points_per_a_quest=_get_int("POINTS_PER_A_QUEST", 500),
        f_rank_threshold=_get_int("F_RANK_THRESHOLD", 100),
        e_rank_threshold=_get_int("E_RANK_THRESHOLD", 250),
        d_rank_threshold=_get_int("D_RANK_THRESHOLD", 500),
        c_rank_threshold=_get_int("C_RANK_THRESHOLD", 1000),
        b_rank_threshold=_get_int("B_RANK_THRESHOLD", 2000),
        a_rank_threshold=_get_int("A_RANK_THRESHOLD", 5000),
        on_time_bonus_multiplier=_get_float("ON_TIME_BONUS_MULTIPLIER", 1.2),
        late_penalty_multiplier=_get_float("LATE_PENALTY_MULTIPLIER", 0.8),
        abandon_penalty_enabled=_get_bool("ABANDON_PENALTY_ENABLED", True),
        abandon_penalty_points=_get_int("ABANDON_PENALTY_POINTS", -10),
        color_f_rank=_get_int("COLOR_F_RANK", 0x808080),
        color_e_rank=_get_int("COLOR_E_RANK", 0x8B4513),
        color_d_rank=_get_int("COLOR_D_RANK", 0xC0C0C0),
        color_c_rank=_get_int("COLOR_C_RANK", 0xFFD700),
        color_b_rank=_get_int("COLOR_B_RANK", 0x4169E1),
        color_a_rank=_get_int("COLOR_A_RANK", 0x9400D3),
        color_success=_get_int("COLOR_SUCCESS", 0x00FF00),
        color_error=_get_int("COLOR_ERROR", 0xFF0000),
        color_warning=_get_int("COLOR_WARNING", 0xFFA500),
        color_info=_get_int("COLOR_INFO", 0x0099FF),
        color_guild_quest=_get_int("COLOR_GUILD_QUEST", 0xFF4500),
        color_in_progress=_get_int("COLOR_IN_PROGRESS", 0x3498DB),
        color_overdue=_get_int("COLOR_OVERDUE", 0xE74C3C),
        color_claimed=_get_int("COLOR_CLAIMED", 0x95A5A6),
        color_party=_get_int("COLOR_PARTY", 0x9B59B6),
        emoji_f_rank=_get_env("EMOJI_F_RANK", ""),
        emoji_e_rank=_get_env("EMOJI_E_RANK", ""),
        emoji_d_rank=_get_env("EMOJI_D_RANK", ""),
        emoji_c_rank=_get_env("EMOJI_C_RANK", ""),
        emoji_b_rank=_get_env("EMOJI_B_RANK", ""),
        emoji_a_rank=_get_env("EMOJI_A_RANK", ""),
        emoji_guild_quest=_get_env("EMOJI_GUILD_QUEST", ""),
        emoji_warning=_get_env("EMOJI_WARNING", ""),
        emoji_party=_get_env("EMOJI_PARTY", ""),
        emoji_complete=_get_env("EMOJI_COMPLETE", ""),
        emoji_claimed=_get_env("EMOJI_CLAIMED", ""),
        emoji_overdue=_get_env("EMOJI_OVERDUE", ""),
        emoji_solo=_get_env("EMOJI_SOLO", ""),
        emoji_leader=_get_env("EMOJI_LEADER", ""),
        emoji_member=_get_env("EMOJI_MEMBER", ""),
        command_prefix=_get_env("COMMAND_PREFIX", "/"),
        bot_status=_get_env("BOT_STATUS", "Managing Adventures"),
        enable_sheet_logging=_get_bool("ENABLE_SHEET_LOGGING", True),
        enable_channel_logging=_get_bool("ENABLE_CHANNEL_LOGGING", True),
        log_level=_get_env("LOG_LEVEL", "INFO"),
    )


def now_utc() -> datetime:
    return datetime.now(timezone.utc)


def format_dt(dt: Optional[datetime]) -> str:
    if not dt:
        return "N/A"
    return dt.astimezone(timezone.utc).strftime("%Y-%m-%d %H:%M UTC")


def add_days(dt: datetime, days: int) -> datetime:
    return dt + timedelta(days=days)


def progress_bar(current: int, total: int, width: int = 10) -> str:
    if total <= 0:
        return "[]"
    ratio = max(0.0, min(1.0, current / total))
    filled = int(round(ratio * width))
    return "[" + ("=" * filled) + ("-" * (width - filled)) + "]"


def split_csv(raw: str) -> List[str]:
    if not raw:
        return []
    return [item.strip() for item in raw.split(",") if item.strip()]


def join_csv(items: Iterable[str]) -> str:
    return ", ".join([item.strip() for item in items if item and item.strip()])


def mention(user_id: int) -> str:
    return f"<@{user_id}>"


RANK_ORDER = ["F", "E", "D", "C", "B", "A"]


def rank_index(rank: str) -> int:
    rank_upper = rank.upper()
    for idx, item in enumerate(RANK_ORDER):
        if item == rank_upper:
            return idx
    return -1


def can_accept_rank(user_rank: str, quest_rank: str) -> bool:
    user_idx = rank_index(user_rank)
    quest_idx = rank_index(quest_rank)
    if user_idx == -1 or quest_idx == -1:
        return False
    return quest_idx <= user_idx + 1


def rank_points(config, quest_rank: str) -> int:
    mapping = {
        "F": config.points_per_f_quest,
        "E": config.points_per_e_quest,
        "D": config.points_per_d_quest,
        "C": config.points_per_c_quest,
        "B": config.points_per_b_quest,
        "A": config.points_per_a_quest,
    }
    return mapping.get(quest_rank.upper(), 0)
