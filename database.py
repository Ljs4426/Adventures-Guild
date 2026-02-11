from __future__ import annotations

import asyncio
import re
from typing import Any, Dict, List, Optional

from google.oauth2.service_account import Credentials
from googleapiclient.discovery import build

from formula_manager import FormulaManager
from utils import join_csv, split_csv


class SheetsClient:
    def __init__(self, sheets_id: str, credentials_file: str) -> None:
        self.sheets_id = sheets_id
        self.credentials_file = credentials_file
        self._service = None
        self._headers_cache: Dict[str, List[str]] = {}

    def _get_service(self):
        if self._service is None:
            creds = Credentials.from_service_account_file(
                self.credentials_file,
                scopes=["https://www.googleapis.com/auth/spreadsheets"],
            )
            self._service = build("sheets", "v4", credentials=creds)
        return self._service

    async def _to_thread(self, func, *args, **kwargs):
        return await asyncio.to_thread(func, *args, **kwargs)

    async def get_values(self, sheet_name: str, cell_range: str = "A:Z") -> List[List[str]]:
        def _fetch():
            service = self._get_service()
            result = (
                service.spreadsheets()
                .values()
                .get(spreadsheetId=self.sheets_id, range=f"{sheet_name}!{cell_range}")
                .execute()
            )
            return result.get("values", [])

        return await self._to_thread(_fetch)

    async def get_headers(self, sheet_name: str) -> List[str]:
        if sheet_name in self._headers_cache:
            return self._headers_cache[sheet_name]
        rows = await self.get_values(sheet_name, "1:1")
        headers = rows[0] if rows else []
        self._headers_cache[sheet_name] = headers
        return headers

    async def get_rows_as_dicts(self, sheet_name: str) -> List[Dict[str, str]]:
        rows = await self.get_values(sheet_name)
        if not rows:
            return []
        headers = rows[0]
        data = []
        for row in rows[1:]:
            item = {}
            for i in range(len(headers)):
                if i < len(row):
                    item[headers[i]] = row[i]
                else:
                    item[headers[i]] = ""
            data.append(item)
        return data

    async def append_row(self, sheet_name: str, row: List[Any]) -> Optional[int]:
        def _append():
            service = self._get_service()
            body = {"values": [row]}
            result = service.spreadsheets().values().append(
                spreadsheetId=self.sheets_id,
                range=sheet_name,
                valueInputOption="USER_ENTERED",
                body=body,
            ).execute()
            return result

        result = await self._to_thread(_append)
        return self._parse_row_index(result.get("updates", {}).get("updatedRange", ""))

    def _parse_row_index(self, updated_range: str) -> Optional[int]:
        if not updated_range:
            return None
        match = re.search(r"![A-Z]+(\d+)", updated_range)
        if not match:
            return None
        return int(match.group(1))

    async def update_cells(self, sheet_name: str, row_index: int, updates: Dict[str, Any]) -> None:
        headers = await self.get_headers(sheet_name)
        if not headers:
            return
        data = []
        for key, value in updates.items():
            if key not in headers:
                continue
            col_index = headers.index(key) + 1
            a1 = self._a1(col_index, row_index)
            data.append({"range": f"{sheet_name}!{a1}", "values": [[value]]})

        if not data:
            return

        def _update():
            service = self._get_service()
            body = {"valueInputOption": "USER_ENTERED", "data": data}
            service.spreadsheets().values().batchUpdate(
                spreadsheetId=self.sheets_id,
                body=body,
            ).execute()

        await self._to_thread(_update)

    async def find_row_index(self, sheet_name: str, column_name: str, value: str) -> Optional[int]:
        rows = await self.get_values(sheet_name)
        if not rows:
            return None
        headers = rows[0]
        if column_name not in headers:
            return None
        col_index = headers.index(column_name)
        for i, row in enumerate(rows[1:], start=2):
            if col_index < len(row) and row[col_index] == value:
                return i
        return None

    async def get_row_by_value(self, sheet_name: str, column_name: str, value: str) -> Optional[Dict[str, str]]:
        rows = await self.get_rows_as_dicts(sheet_name)
        for row in rows:
            if row.get(column_name) == value:
                return row
        return None

    async def update_row_by_value(
        self, sheet_name: str, column_name: str, value: str, updates: Dict[str, Any]
    ) -> bool:
        row_index = await self.find_row_index(sheet_name, column_name, value)
        if not row_index:
            return False
        await self.update_cells(sheet_name, row_index, updates)
        return True

    def _a1(self, col: int, row: int) -> str:
        return f"{self._col_to_a1(col)}{row}"

    def _col_to_a1(self, col: int) -> str:
        result = ""
        while col > 0:
            col, rem = divmod(col - 1, 26)
            result = chr(65 + rem) + result
        return result


class GuildDatabase:
    def __init__(self, sheets: SheetsClient, config) -> None:
        self.sheets = sheets
        self.config = config
        self.formulas = FormulaManager()

    async def _apply_formulas(self, sheet_name: str, row_index: Optional[int]) -> None:
        if not row_index:
            return
        formulas = self.formulas.get_sheet_formulas(sheet_name)
        if not formulas:
            return
        updates = {key: self.formulas.render(value, row_index) for key, value in formulas.items()}
        await self.sheets.update_cells(sheet_name, row_index, updates)

    async def get_user_by_discord_id(self, discord_id: str) -> Optional[Dict[str, str]]:
        return await self.sheets.get_row_by_value(self.config.users_sheet_name, "Discord ID", discord_id)

    async def get_user_by_username(self, username: str) -> Optional[Dict[str, str]]:
        return await self.sheets.get_row_by_value(self.config.users_sheet_name, "Username", username)

    async def create_user(self, username: str, discord_id: str, join_date: str) -> None:
        row = [
            username,
            discord_id,
            "None",
            "None",
            "F",
            "0",
            "",
            "0",
            join_date,
            join_date,
            "",
            "0",
            "N/A",
        ]
        row_index = await self.sheets.append_row(self.config.users_sheet_name, row)
        await self._apply_formulas(self.config.users_sheet_name, row_index)

    async def update_user_fields(self, discord_id: str, updates: Dict[str, Any]) -> bool:
        return await self.sheets.update_row_by_value(self.config.users_sheet_name, "Discord ID", discord_id, updates)

    async def get_party_by_id(self, party_id: str) -> Optional[Dict[str, str]]:
        return await self.sheets.get_row_by_value(self.config.parties_sheet_name, "Party ID", party_id)

    async def get_party_by_name(self, party_name: str) -> Optional[Dict[str, str]]:
        return await self.sheets.get_row_by_value(self.config.parties_sheet_name, "Party Name", party_name)

    async def create_party(
        self,
        party_name: str,
        leader_discord_id: str,
        leader_username: str,
        members: List[str],
        created_date: str,
        default_settings: Dict[str, str],
    ) -> None:
        members_csv = join_csv(members)
        row = [
            "",
            party_name,
            leader_discord_id,
            leader_username,
            members_csv,
            str(len(members)),
            "F",
            "0",
            "",
            "0",
            created_date,
            created_date,
            "",
            "0",
            "N/A",
            default_settings.get("quest_accept", "Leader Only"),
            default_settings.get("quest_complete", "Leader Only"),
            default_settings.get("quest_abandon", "Leader Only"),
            default_settings.get("invite", "Leader Only"),
            default_settings.get("auto_distribute", "Yes"),
            default_settings.get("require_confirmation", "No"),
            created_date,
            leader_username,
        ]
        row_index = await self.sheets.append_row(self.config.parties_sheet_name, row)
        await self._apply_formulas(self.config.parties_sheet_name, row_index)

    async def update_party_fields(self, party_id: str, updates: Dict[str, Any]) -> bool:
        return await self.sheets.update_row_by_value(self.config.parties_sheet_name, "Party ID", party_id, updates)

    async def list_party_members(self, party_row: Dict[str, str]) -> List[str]:
        return split_csv(party_row.get("Members", ""))

    async def set_party_members(self, party_id: str, members: List[str]) -> bool:
        updates = {"Members": join_csv(members), "Member Count": str(len(members))}
        return await self.update_party_fields(party_id, updates)

    async def create_invite(
        self,
        party_id: str,
        party_name: str,
        invited_user: str,
        invited_discord_id: str,
        invited_by: str,
        invited_date: str,
        expiry_date: str,
    ) -> None:
        row = ["", party_id, party_name, invited_user, invited_discord_id, invited_by, invited_date, expiry_date, "Pending", ""]
        row_index = await self.sheets.append_row(self.config.party_invites_sheet_name, row)
        await self._apply_formulas(self.config.party_invites_sheet_name, row_index)

    async def update_invite_fields(self, invite_id: str, updates: Dict[str, Any]) -> bool:
        return await self.sheets.update_row_by_value(self.config.party_invites_sheet_name, "Invite ID", invite_id, updates)

    async def get_invite_by_id(self, invite_id: str) -> Optional[Dict[str, str]]:
        return await self.sheets.get_row_by_value(self.config.party_invites_sheet_name, "Invite ID", invite_id)

    async def list_pending_invites(self) -> List[Dict[str, str]]:
        rows = await self.sheets.get_rows_as_dicts(self.config.party_invites_sheet_name)
        pending = []
        for row in rows:
            if row.get("Status") == "Pending":
                pending.append(row)
        return pending

    async def create_quest(
        self,
        description: str,
        reward: str,
        commission_type: str,
        commissioned_by: str,
        created_date: str,
        status: str,
        assigned_by: str = "",
    ) -> None:
        row = [
            "",
            description,
            "TBD",
            "",
            reward,
            commission_type,
            status,
            commissioned_by,
            created_date,
            "",
            "",
            "",
            "",
            "",
            "",
            assigned_by,
            "",
        ]
        row_index = await self.sheets.append_row(self.config.quests_sheet_name, row)
        await self._apply_formulas(self.config.quests_sheet_name, row_index)

    async def update_quest_fields(self, quest_id: str, updates: Dict[str, Any]) -> bool:
        return await self.sheets.update_row_by_value(self.config.quests_sheet_name, "Quest ID", quest_id, updates)

    async def get_quest_by_id(self, quest_id: str) -> Optional[Dict[str, str]]:
        return await self.sheets.get_row_by_value(self.config.quests_sheet_name, "Quest ID", quest_id)

    async def list_quests_by_status(self, status: str) -> List[Dict[str, str]]:
        rows = await self.sheets.get_rows_as_dicts(self.config.quests_sheet_name)
        results = []
        for row in rows:
            if row.get("Status") == status:
                results.append(row)
        return results
