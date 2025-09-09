
import requests
from WaitingListDataLoader import SupabaseDBClient

SUPABASE_URL = "https://fpvswpsvpyqvwpkmxtgj.supabase.co"
SUPABASE_KEY = "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6ImZwdnN3cHN2cHlxdndwa214dGdqIiwicm9sZSI6ImFub24iLCJpYXQiOjE3NTY5OTYyNTQsImV4cCI6MjA3MjU3MjI1NH0.d7IQonhpRMvoGcaG47gVA4JE95O5fFQfmvUe9WB6BpQ"


headers = {
    "apikey": SUPABASE_KEY,
    "Authorization": f"Bearer {SUPABASE_KEY}",
    "Content-Type": "application/json"}

def show_table(table_name):
    url = f"{SUPABASE_URL}/rest/v1/{table_name}?select=*"
    response = requests.get(url, headers=headers, verify=False)
    print(f"Status: {response.status_code}")
    if response.ok:
        print(f"Sample rows from '{table_name}':")
        t= response.json()
        print(response.json())
    else:
        print(f"Error while fetching data from '{table_name}':", response.text)

def add_demo_person():
    url = f"{SUPABASE_URL}/rest/v1/WaitingList"
    demo_person = {
        'name': 'Demo User',
        'date_added': '2025-09-04',
        'address': 'Demo Address',
        'referrer': 'Demo Referrer',
        'committee_approval': 'כן',
        'psychiatric_report': 'כן',
        'psychosocial_report': 'כן',
        'medical_report': 'כן',
        'id_photo': 'כן',
        'comments': 'Demo comment',
        'urgent_case': False,
        'branch': 'תל אביב',
        'facility': 'גוש דן'
    }
    response = requests.post(url, headers=headers, json=demo_person, verify=False)
    print(f"Status: {response.status_code}")
    if response.ok:
        print("Demo person added to 'WaitingList'. Response:", response.json())
    else:
        print("Error while inserting demo person:", response.text)

if __name__ == "__main__":
    # show_table('WaitingList')
    # add_demo_person()
    FACILITIES = ["גוש דן"]
    # Branches per facility
    FACILITY_BRANCHES = {
        "גוש דן": ["הכל", "תל אביב", "רמת גן - גבעתיים", "בקעת אונו", "הרצליה - רמת השרון", "חולון - בת ים","להטבק", "טראומה מורכבת","דרי רחוב"]
    }


    DBloader= SupabaseDBClient(
        supabase_url="https://fpvswpsvpyqvwpkmxtgj.supabase.co",
        supabase_key="eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6ImZwdnN3cHN2cHlxdndwa214dGdqIiwicm9sZSI6ImFub24iLCJpYXQiOjE3NTY5OTYyNTQsImV4cCI6MjA3MjU3MjI1NH0.d7IQonhpRMvoGcaG47gVA4JE95O5fFQfmvUe9WB6BpQ",
        facility="גוש דן",
        branches=FACILITY_BRANCHES["גוש דן"]
    )
    store_2= DBloader.read_waiting_list()
    
    
    demo_person = {
        'שם מלא': 'אורן טסט',
        'תאריך': '2025-09-04',
        'כתובת': 'אורן Address',
        'גורם מפנה': 'אורן Referrer',
        'אישור ועדה': 'כן',
        'דוח פסיכיאטרי': 'כן',
        'דוח פסיכוסוציאלי': 'כן',
        'דוח רפואי': 'כן',
        'צילום תז': 'כן',
        'הערות': 'Demo comment',
        'מקרה דחוף': False,
        'סניף': 'תל אביב',
        'מרחב': 'גוש דן'}
    
    demo_person_accepted = {
        'שם מלא': '2אורן טסט',
        "תאריך המתנה": "2025-09-04",
        "תאריך קבלה": "2025-09-05",
        'כתובת': 'אורן Address',
        'גורם מפנה': 'אורן Referrer',
        'אישור ועדה': 'כן',
        'דוח פסיכיאטרי': 'כן',
        'דוח פסיכוסוציאלי': 'כן',
        'דוח רפואי': 'כן',
        'צילום תז': 'כן',
        'הערות': 'Demo comment',
        'סניף': 'תל אביב',
        "סניף מקורי": "חולון - בת ים",
        'מרחב': 'גוש דן'}
    store_3= DBloader.read_accepted_list()
    DBloader.add_person_to_accepted_list(demo_person_accepted)

    SupabaseDBClient.add_person(DBloader,demo_person)
    SupabaseDBClient.edit_person(DBloader,"Demo User", demo_person)
    t=1
