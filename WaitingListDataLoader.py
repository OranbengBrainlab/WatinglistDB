import pandas as pd
import gspread
from gspread_dataframe import set_with_dataframe
import requests
import io
from typing import Dict, List




class WaitingListDataLoaderClass:
	def write_to_google_sheet(self, data_store: Dict[str, Dict[str, List[dict]]], facility: str, sheet_id: str, branches: List[str], creds_json_path: str) -> None:
		"""
		Overwrite the Google Sheet for all branches of the given facility.
		Each branch is a tab in the Google Sheet.
		creds_json_path: Path to Google service account credentials JSON file.
		"""
		gc = gspread.service_account(filename=creds_json_path)
		sh = gc.open_by_key(sheet_id)
		for b in branches:
			if b == "See all":
				continue
			branch_list = data_store[facility][b]
			if branch_list:
				df_branch = pd.DataFrame(branch_list)
			else:
				df_branch = pd.DataFrame(columns=["name"])
			try:
				worksheet = sh.worksheet(b)
			except gspread.WorksheetNotFound:
				worksheet = sh.add_worksheet(title=b, rows=100, cols=len(df_branch.columns))
			worksheet.clear()
			set_with_dataframe(worksheet, df_branch)
	def __init__(self, add_to_waitlist_func=None):
		self.add_to_waitlist = add_to_waitlist_func

	def read_google_sheet_to_data_store(self, sheet_id: str, facility: str, branch_gids: Dict[str, str]) -> Dict[str, Dict[str, List[dict]]]:
		"""
		Reads Google Sheets tabs as CSV and returns a data_store structure:
		{facility: {branch: [person_dict, ...]}}
		"""
		data_store: Dict[str, Dict[str, List[dict]]] = {facility: {branch: [] for branch in branch_gids}}
		for branch, gid in branch_gids.items():
			url = (
				f"https://docs.google.com/spreadsheets/d/"
				f"{sheet_id}/export?format=csv&gid={gid}"
			)
			print(f"Fetching: {url}")
			try:
				response = requests.get(url, verify=False)
				if response.status_code == 400:
					print(f"400 Bad Request: Check sharing settings and gid for branch '{branch}'.")
					continue
				response.raise_for_status()
				decoded_text = response.content.decode('utf-8')
				df = pd.read_csv(io.StringIO(decoded_text), on_bad_lines='skip')
				name_col = None
				for col in df.columns:
					if str(col).strip().lower() in ["name", "שם", "full name", "fullname"]:
						name_col = col
						break
				if not name_col:
					name_col = df.columns[0]
				for row in df.to_dict(orient="records"):
					if str(row.get(name_col, "")).strip():
						person = dict(row)
						person["name"] = str(row.get(name_col, "")).strip()
						data_store[facility][branch].append(person)
			except Exception as e:
				print(f"Could not load Google Sheet for branch {branch}: {e}")
		return data_store

	def read_excel_to_data_store(self, excel_path: str, facility: str, branches: List[str]) -> Dict[str, Dict[str, List[dict]]]:
		"""
		Reads waiting list data from Excel file for a facility and its branches.
		Returns: {facility: {branch: [person_dict, ...]}}
		"""
		data_store: Dict[str, Dict[str, List[dict]]] = {facility: {branch: [] for branch in branches}}
		try:
			xl = pd.ExcelFile(excel_path)
			for branch in branches:
				if branch == "See all":
					continue
				sheet_name = None
				for s in xl.sheet_names:
					if s.lower().replace(" ", "") == branch.lower().replace(" ", ""):
						sheet_name = s
						break
				if sheet_name:
					df = xl.parse(sheet_name)
					name_col = None
					for col in df.columns:
						if str(col).strip().lower() in ["name", "שם", "full name", "fullname"]:
							name_col = col
							break
					if not name_col:
						name_col = df.columns[0]
					for row in df.to_dict(orient="records"):
						if str(row.get(name_col, "")).strip():
							person = dict(row)
							person["name"] = str(row.get(name_col, "")).strip()
							if self.add_to_waitlist:
								self.add_to_waitlist(data_store, person, facility, branch)
							else:
								data_store[facility][branch].append(person)
		except Exception as e:
			print(f"Could not load Excel data: {e}")
		return data_store

	def write_to_excel(self, data_store: Dict[str, Dict[str, List[dict]]], facility: str, excel_path: str, branches: List[str]) -> None:
		"""
		Overwrite the Excel file for all branches of the given facility.
		"""
		with pd.ExcelWriter(excel_path, engine="openpyxl", mode="w") as writer:
			for b in branches:
				if b == "See all":
					continue
				branch_list = data_store[facility][b]
				if branch_list:
					df_branch = pd.DataFrame(branch_list)
				else:
					df_branch = pd.DataFrame(columns=["name"])
				df_branch.to_excel(writer, sheet_name=b, index=False)

# Example usage:
if __name__ == "__main__":
	# Example for Google Sheets
	SHEET_ID = "11HkEhjdNYUGxrO1Y1bN2qmqBnStA8raq"
	FACILITY = "Gush_Dan"
	BRANCH_GIDS = {
		"Tel Aviv": "292505320",      # Replace with actual gid for Tel Aviv tab
		"Ramat Gan": "809260774"   # Replace with actual gid for Ramat Gan tab
	}
	loader = WaitingListDataLoaderClass()
	data_store_gs = loader.read_google_sheet_to_data_store(SHEET_ID, FACILITY, BRANCH_GIDS)
	print("Google Sheets Data Store:", data_store_gs)

	# Example for Excel
	EXCEL_PATH = "Data/waiting_list_gush_dan.xlsx"
	BRANCHES = ["Tel Aviv", "Ramat Gan"]
	data_store_excel = loader.read_excel_to_data_store(EXCEL_PATH, FACILITY, BRANCHES)
	print("Excel Data Store:", data_store_excel)
    


