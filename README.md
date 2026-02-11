# Adventures Guild Quests Bot

Discord bot that manages quests and parties using Google Sheets.

## Features

- Quest commission, review, board, and completion
- Party create, invite, transfer leader, disband
- Ranks and points with embed info
- Config from `.env`

## Requirements

- Python 3.12+
- Discord bot token
- Google Sheets API service account credentials

## Setup

1. Make a venv and install deps:

   ```bash
   python -m venv .venv
   source .venv/bin/activate
   pip install -r requirements.txt
   ```

2. Make a `.env` with your bot token + channel/role IDs.

3. Put your Google Sheets service account file where `GOOGLE_CREDENTIALS_FILE` points.

4. Run the bot:

   ```bash
   python main.py
   ```

## Discord Commands (Selected)

- `/signup <username>`
- `/commission-quest <description> <reward>`
- `/quest-edit <quest_id> [rank] [reward] [false_rank_probability]` (admin/mod)
- `/quest-board [status]`
- `/my-quests`
- `/complete-quest <quest_id>`
- `/abandon-quest <quest_id> <reason>` (requires confirmation)
- `/form-party <party_name> <member>`
- `/party-invite <user>`
- `/party-transfer-leader <user>`
- `/party-disband [reason]`

## Test Runner

A restricted `/test` command runs a full flow and asks for input in a modal.

- Only user ID `1027732252685250560` can run it.
- Prompts for username, quest description, reward, abandon reason, and a member ID.
- Posts to the normal channels and DMs members on disband.

## Config Notes

- Keep your bot token private and never commit it.
- Quest + party data live in Google Sheets, so headers need to match the code.
- Optional quest fields: `Abandon Reason`, `Abandoned By`, `Abandon Date`.

## Troubleshooting

- If a modal shows “Something went wrong,” check the bot console.
- Ensure channel and role IDs in `.env` are valid and the bot has permissions.
