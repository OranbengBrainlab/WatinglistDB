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
				if branch == "הכל":
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
						if str(col).strip().lower() in ["שם", "שם מלא", "full name", "fullname"]:
							name_col = col
							break
					if not name_col:
						name_col = df.columns[0]
					for row in df.to_dict(orient="records"):
						if str(row.get(name_col, "")).strip():
							person = dict(row)
							person["שם מלא"] = str(row.get(name_col, "")).strip()
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
				if b == "הכל":
					continue
				branch_list = data_store[facility][b]
				if branch_list:
					df_branch = pd.DataFrame(branch_list)
				else:
					df_branch = pd.DataFrame(columns=["name"])
				df_branch.to_excel(writer, sheet_name=b, index=False)

class SupabaseDBClient:

    def __init__(self, supabase_url, supabase_key, facility, branches):
        self.supabase_url = supabase_url
        self.supabase_key = supabase_key
        self.facility = facility
        self.branches = branches
        self.headers = {
            "apikey": self.supabase_key,
            "Authorization": f"Bearer {self.supabase_key}",
            "Content-Type": "application/json"
        }

    def read_waiting_list(self):
        """
        Reads WaitingList table from Supabase and returns data_store format with Hebrew field names, dropping 'סניף' and 'מרחב':
        {facility: {branch: [person_dict, ...]}}
        """
        url = f"{self.supabase_url}/rest/v1/WaitingList?select=*"
        response = requests.get(url, headers=self.headers, verify=False)
        data_store = {self.facility: {branch: [] for branch in self.branches}}
        field_map = {
            "name": "שם מלא",
            "date_added": "תאריך",
            "address": "כתובת",
            "referrer": "גורם מפנה",
            "committee_approval": "אישור ועדה",
            "psychiatric_report": "דוח פסיכיאטרי",
            "psychosocial_report": "דוח פסיכוסוציאלי",
            "medical_report": "דוח רפואי",
            "id_photo": "צילום תז",
            "comments": "הערות",
            "urgent_case": "מקרה דחוף",
            "branch": "סניף",
            "facility": "מרחב"
        }
        if response.ok:
            rows = response.json()
            for row in rows:
                branch = row.get('branch')
                if branch in self.branches:
                    person = {}
                    for k, v in field_map.items():
                        person[v] = row.get(k, "")
                    # Drop 'סניף' and 'מרחב'
                    # pop("סניף", None)
                    person.pop("מרחב", None)
                    data_store[self.facility][branch].append(person)
        else:
            print(f"Error fetching waiting_list: {response.text}")
        return data_store

    def add_person(self, person_dict):
        """
        Adds a new person to the waiting_list table in Supabase.
        person_dict should use Hebrew field names as in data_store.
        """
        field_map = {
            "שם מלא": "name",
            "תאריך": "date_added",
            "כתובת": "address",
            "גורם מפנה": "referrer",
            "אישור ועדה": "committee_approval",
            "דוח פסיכיאטרי": "psychiatric_report",
            "דוח פסיכוסוציאלי": "psychosocial_report",
            "דוח רפואי": "medical_report",
            "צילום תז": "id_photo",
            "הערות": "comments",
            "מקרה דחוף": "urgent_case",
            "סניף": "branch",
            "מרחב": "facility"
        }
        # Map Hebrew keys to Supabase keys
        supabase_person = {field_map[k]: v for k, v in person_dict.items() if k in field_map}
        url = f"{self.supabase_url}/rest/v1/WaitingList"
        response = requests.post(url, headers=self.headers, json=supabase_person, verify=False)
        if response.ok:
            print("Person added successfully.")
        else:
            print(f"Error adding person: {response.text}")
            return None

    def edit_person(self, person_name, updated_fields):
        """
        Edit an existing person in the waiting_list table by id.
        updated_fields should use Hebrew field names as in data_store.
        """
        field_map = {
            "שם מלא": "name",
            "תאריך": "date_added",
            "כתובת": "address",
            "גורם מפנה": "referrer",
            "אישור ועדה": "committee_approval",
            "דוח פסיכיאטרי": "psychiatric_report",
            "דוח פסיכוסוציאלי": "psychosocial_report",
            "דוח רפואי": "medical_report",
            "צילום תז": "id_photo",
            "הערות": "comments",
            "מקרה דחוף": "urgent_case",
            "סניף": "branch",
            "מרחב": "facility"
        }
        # Map Hebrew keys to Supabase keys
        supabase_fields = {field_map[k]: v for k, v in updated_fields.items() if k in field_map}
        url = f"{self.supabase_url}/rest/v1/WaitingList?name=eq.{person_name}"
        response = requests.patch(url, headers=self.headers, json=supabase_fields, verify=False)
        if response.ok:
            print("Person updated successfully.")
        else:
            print(f"Error updating person: {response.text}")
            return None

    def read_accepted_list(self):
        
        url = f"{self.supabase_url}/rest/v1/AcceptedList?select=*"
        response = requests.get(url, headers=self.headers, verify=False)
        data_store = {self.facility: {branch: [] for branch in self.branches}}
        field_map = {
            "name": "שם מלא",
            "date_added": "תאריך המתנה",
			"date_accepted": "תאריך קבלה",
			"address": "כתובת",
			"referrer": "גורם מפנה",
			"committee_approval": "אישור ועדה",
			"psychiatric_report": "דוח פסיכיאטרי",
			"psychosocial_report": "דוח פסיכוסוציאלי",
			"medical_report": "דוח רפואי",
			"id_photo": "צילום תז",
			"comments": "הערות",
			"urgent_case": "מקרה דחוף",
			"original_branch": "סניף מקורי",
			"branch": "סניף",
			"facility": "מרחב"}
        if response.ok:
            rows = response.json()
            for row in rows:
                branch = row.get('branch')
                if branch in self.branches:
                    person = {}
                    for k, v in field_map.items():
                        person[v] = row.get(k, "")
                    # Drop 'סניף' and 'מרחב'
                    # person.pop("סניף", None)
                    person.pop("מרחב", None)
                    data_store[self.facility][branch].append(person)
            return data_store  
        else:
            print(f"Error fetching accepted_list: {response.text}")

    def remove_person_from_accepted_list(self, person_name):
        url = f"{self.supabase_url}/rest/v1/AcceptedList?name=eq.{person_name}"
        response = requests.delete(url, headers=self.headers, verify=False)
        if response.ok:
            print(f"Person '{person_name}' removed from AcceptedList.")
        else:
            print(f"Error removing person from AcceptedList: {response.text}")
			
    def remove_person_from_waiting_list(self, person_name):
        url = f"{self.supabase_url}/rest/v1/WaitingList?name=eq.{person_name}"
        response = requests.delete(url, headers=self.headers, verify=False)
        if response.ok:
            print(f"Person '{person_name}' removed from WaitingList.")
        else:
            print(f"Error removing person from WaitingList: {response.text}")

    def add_person_to_accepted_list(self, person_dict):
        """
        Adds a new person to the AcceptedList table in Supabase.
        person_dict should use Hebrew field names as in data_store.
        """
        field_map = {
            "שם מלא": "name",
            "תאריך המתנה": "date_added",
            "תאריך קבלה": "date_accepted",
            "כתובת": "address",
            "גורם מפנה": "referrer",
            "אישור ועדה": "committee_approval",
            "דוח פסיכיאטרי": "psychiatric_report",
            "דוח פסיכוסוציאלי": "psychosocial_report",
            "דוח רפואי": "medical_report",
            "צילום תז": "id_photo",
            "הערות": "comments",
            "סניף מקורי": "original_branch",
            "סניף": "branch",
            "מרחב": "facility"
        }
        # Map Hebrew keys to Supabase keys
        supabase_person = {field_map[k]: v for k, v in person_dict.items() if k in field_map}
        url = f"{self.supabase_url}/rest/v1/AcceptedList"
        response = requests.post(url, headers=self.headers, json=supabase_person, verify=False)
        if response.ok:
            print("Person added to AcceptedList successfully.")
        else:
            print(f"Error adding person to AcceptedList: {response.text}")
            return None

# Example usage:
if __name__ == "__main__":
	# Example for Google Sheets
	# SHEET_ID = "11HkEhjdNYUGxrO1Y1bN2qmqBnStA8raq"
	FACILITY = "Gush_Dan"
	BRANCH_GIDS = {
		"Tel Aviv": "292505320",      # Replace with actual gid for Tel Aviv tab
		"Ramat Gan": "809260774"   # Replace with actual gid for Ramat Gan tab
	}
	loader = WaitingListDataLoaderClass()
	# data_store_gs = loader.read_google_sheet_to_data_store(SHEET_ID, FACILITY, BRANCH_GIDS)
	# print("Google Sheets Data Store:", data_store_gs)

	# Example for Excel
	EXCEL_PATH = "Data/waiting_list_gush_dan.xlsx"
	FACILITIES = ["גוש דן"]
	# Branches per facility
	FACILITY_BRANCHES = {
	    "גוש דן": ["הכל", "תל אביב", "רמת גן - גבעתיים", "בקעת אונו", "הרצליה - רמת השרון", "חולון - בת ים","להטבק", "טראומה מורכבת","דרי רחוב"]}
	BRANCHES = FACILITY_BRANCHES[FACILITIES[0]]
	data_store_excel = loader.read_excel_to_data_store(EXCEL_PATH, FACILITY, BRANCHES)
	print("Excel Data Store:", data_store_excel)



