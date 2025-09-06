import streamlit as st
from typing import Dict, List
import pandas as pd
import time
import altair as alt
from datetime import datetime, date
from WaitingListDataLoader import WaitingListDataLoaderClass,SupabaseDBClient


# --- Configuration ---
FACILITIES = ["גוש דן"]
# Branches per facility
FACILITY_BRANCHES = {
    "גוש דן": ["הכל", "תל אביב", "רמת גן - גבעתיים", "בקעת אונו", "הרצליה - רמת השרון", "חולון - בת ים","להטבק", "טראומה מורכבת","דרי רחוב"]}


#FACILITIES = ["גוש דן", "שרון", "ירושלים"]
# Branches per facility
#FACILITY_BRANCHES = {
#    "גוש דן": ["הכל", "תל אביב", "רמת גן"],
#    "שרון": ["נתניה", "עמק_חפר", "הכל"],
#    "ירושלים": ["מרכז", "מבשרת", "הכל"]
# }
# DataType = "Excel"
DataType = "DB"



# --- Data Store Logic ---
def init_data_store() -> Dict[str, Dict[str, List[str]]]:
    """Initialize the waiting list data store."""
    return {facility: {branch: [] for branch in FACILITY_BRANCHES[facility]} for facility in FACILITIES}

def add_to_waitlist(data_store: Dict[str, Dict[str, List[str]]], name: str, facility: str, branch: str) -> bool:
    """Add a person to the waiting list. Returns True if added, False if invalid."""
    # This function will now expect a dict for person data
    if isinstance(name, dict):
        person = name
        if not person.get("שם מלא", "").strip():
            return False
        data_store[facility][branch].append(person)
        return True
    else:
        name = name.strip()
        if not name:
            return False
        data_store[facility][branch].append({"שם מלא": name})
        return True

def get_waitlist(data_store: Dict[str, Dict[str, List[str]]], facility: str, branch: str) -> List[str]:
    """Get the waiting list for a facility and branch."""
    return data_store[facility][branch]

# --- Statistics Function ---
def calculate_statistics(data_store, facility=None, branch=None):
    """
    Returns a list of dicts with statistics for each branch:
    - facility: facility name
    - branch: branch name
    - count: number of people waiting
    - avg_wait: average waiting time in days
    - dates: list of dates for occupancy trends
    """
    stats = []
    facilities = [facility] if facility else FACILITIES
    for fac in facilities:
        branches = [branch] if branch else [b for b in FACILITY_BRANCHES[fac] if b != "הכל"]
        for br in branches:
            people = get_waitlist(data_store, fac, br)
            if not people:
                continue
            filtered = people
            avg_wait = None
            if filtered and "תאריך" in filtered[0]:
                dates = [
                    pd.to_datetime(p["תאריך"], errors="coerce")
                    for p in filtered if p.get("תאריך")
                ]
                dates = [d for d in dates if pd.notnull(d)]
                if dates:
                    days = [(datetime.today() - d).days for d in dates]
                    avg_wait = sum(days) / len(days)
            stats.append({
                "facility": fac,
                "branch": br,
                "count": len(filtered),
                "avg_wait": avg_wait if avg_wait is not None else 0,
                "dates": [p["תאריך"] for p in filtered if p.get("תאריך")]
            })
    return stats

def load_waiting_list_from_excel(file_path: str, facility: str, branches: list) -> Dict[str, List[dict]]:
    """Load waiting list data from Excel file for a facility and its branches."""
    xl = pd.ExcelFile(file_path)
    branch_data = {}
    for branch in branches:
        if branch == "הכל":
            continue
        if branch in xl.sheet_names:
            df = xl.parse(branch)
            # Convert each row to dict, skip empty names
            people = [row for row in df.to_dict(orient="records") if str(row.get("שם מלא", "")).strip()]
            branch_data[branch] = people
        else:
            branch_data[branch] = []
    return branch_data

def serialize_dates(data):
    for k, v in data.items():
        if isinstance(v, date):
            data[k] = v.strftime("%Y-%m-%d")
    return data

# --- Streamlit UI ---


st.set_page_config(page_title="Waiting List Manager", layout="centered")


if DataType == "Excel":
    excel_path = "Data/waiting_list_gush_dan.xlsx"
    if "waiting_lists" not in st.session_state:
        loader = WaitingListDataLoaderClass(add_to_waitlist)
        try:
            store = loader.read_excel_to_data_store(
                excel_path,
                "גוש דן",
                FACILITY_BRANCHES["גוש דן"]
            )
        except Exception as e:
            st.warning(f"Could not load Excel data: {e}")
        st.session_state["waiting_lists"] = store

    data_store = st.session_state["waiting_lists"]
elif DataType == "DB":
    DBloader = SupabaseDBClient(
        supabase_url="https://fpvswpsvpyqvwpkmxtgj.supabase.co",
        supabase_key="eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6ImZwdnN3cHN2cHlxdndwa214dGdqIiwicm9sZSI6ImFub24iLCJpYXQiOjE3NTY5OTYyNTQsImV4cCI6MjA3MjU3MjI1NH0.d7IQonhpRMvoGcaG47gVA4JE95O5fFQfmvUe9WB6BpQ",
        facility="גוש דן",
        branches=FACILITY_BRANCHES["גוש דן"]
    )
    try:
        store = DBloader.read_waiting_list()
    except Exception as e:
        st.warning(f"Could not load DB data: {e}")
    st.session_state["waiting_lists"] = store
    data_store = st.session_state["waiting_lists"]
    try:
        store2 = DBloader.read_accepted_list()
    except Exception as e:
        st.warning(f"Could not load DB data: {e}")
    st.session_state["accepted_lists"] = store2

# --- User Authentication ---
VALID_USERS = {
    "admin": "admin",
    "user1": "pass1",
    "Tal": "Tal",
    "user2": "pass2",
    "test": "test"
}

def check_login(username, password):
    return VALID_USERS.get(username) == password

# Sidebar navigation


def show_debug_panel():
    st.markdown("### 🐛 Debug Information")
    # Session State Debug
    with st.expander("📊 Session State", expanded=False):
        st.write("**Session State Variables:**")
        for key, value in st.session_state.items():
            st.write(f"- {key}: {type(value).__name__} = {str(value)[:100]}...")
    # Data Debug
    with st.expander("📋 Data Debug", expanded=False):
        st.write("**Current Waiting Lists Data:**")
        st.write(st.session_state.get("waiting_lists", {}))
        st.write(st.session_state.get("waiting_lists2", {}))
        # Excel debug info
        excel_path = "Data/waiting_list_gush_dan.xlsx"
        try:
            xl = pd.ExcelFile(excel_path)
            st.write(f"**Excel file loaded:** {excel_path}")
            st.write(f"**Sheet names:** {xl.sheet_names}")
            for sheet in xl.sheet_names:
                st.write(f"**Sample from sheet '{sheet}':**")
                df = xl.parse(sheet)
                st.write(df.head())
        except Exception as e:
            st.write(f"Excel debug error: {e}")
    # Module Status Debug
    with st.expander("🔧 Module Status", expanded=False):
        st.write("- Streamlit: Available")


# Check login status
logged_in = st.session_state.get("logged_in_user")

with st.sidebar:
    st.image("Images/Logo.jpg", width=720)
    st.markdown('---')

    sidebar_choice = st.radio(
        "",
        ["🏠 דף בית", "📋 רשימת המתנה", "➕ הוספת משתקם", "📝 עריכת משתקם", "✅ מתקבלים", "📊 סטטיסטיקה ודוחות"],
        index=0
    )

if sidebar_choice == "🏠 דף בית":
    # Logo moved to sidebar
    st.markdown("# ידיד תור", unsafe_allow_html=True)
    st.markdown("### ברוכים הבאים לאפליקציית ניהול התורים של ידיד נפש", unsafe_allow_html=True)
    st.markdown("---")
    st.subheader("כניסה")
    if not logged_in:
        with st.form("login_form"):
            username = st.text_input("שם משתמש")
            password = st.text_input("סיסמה", type="password")
            login_btn = st.form_submit_button("התחבר/י")
            if login_btn:
                if check_login(username, password):
                    st.success(f"ברוך הבא, {username}!")
                    st.session_state["logged_in_user"] = username
                else:
                    st.error("שם משתמש או סיסמה לא נכונים.")
    else:
        st.success(f"אתה מחובר כ-{logged_in}.")

if sidebar_choice != "🏠 דף בית" and not logged_in:
    st.warning("אנא התחבר/י למערכת")
    st.stop()

elif sidebar_choice == "📋 רשימת המתנה":
    st.header("רשימת המתנה")
    # excel_path = "Data/waiting_list_gush_dan.xlsx"
    # if "waiting_lists" not in st.session_state:
    #     loader = WaitingListDataLoaderClass(add_to_waitlist)
    #    try:
    #         store = loader.read_excel_to_data_store(
    #             excel_path,
    #             "גוש דן",
    #             FACILITY_BRANCHES["גוש דן"]
    #         )
    #     except Exception as e:
    #         st.warning(f"Could not load Excel data: {e}")
    #     st.session_state["waiting_lists"] = store
    data_store = st.session_state["waiting_lists"]
    col1, col2 = st.columns(2)
    with col1:
        facility = st.selectbox("בחר/י מרחב", FACILITIES, key="view_facility")
    with col2:
        branch = st.selectbox("בחר/י סניף", FACILITY_BRANCHES[facility], key="view_branch")
    st.subheader(f"רשימת המתנה עבור {facility} - {branch}")
    # --- Advanced Search & Filter Controls ---
    filter_col1, filter_col2, filter_col3 = st.columns(3)
    with filter_col1:
        search_name = st.text_input("🔍 חפש/י לפי שם", value="", key="search_name")
    with filter_col2:
        filter_urgent = st.selectbox("🆘 הצג/י רק מקרים דחופים", ("מקרה דחוף", "מקרה לא דחוף"), index=None, placeholder="בחר/י סוג מקרה", key="filter_urgent")
    with filter_col3:
        filter_date = st.date_input("📅 הצג/י ממתינים מתאריך", value=None, key="filter_date")
    # Get all people for selected branch/facility
    if branch == "הכל":
        all_people = []
        for b in FACILITY_BRANCHES[facility]:
            if b != "הכל":
                all_people.extend(get_waitlist(data_store, facility, b))
        waiting_list = all_people
    else:
        waiting_list = get_waitlist(data_store, facility, branch)
    # --- Apply Filters ---
    filtered_list = waiting_list
    if search_name:
        filtered_list = [p for p in filtered_list if search_name.strip() in str(p.get("שם מלא", ""))]
    if filter_urgent == "מקרה דחוף":
        filtered_list = [p for p in filtered_list if p.get("מקרה דחוף") in [True, "כן"]]
    elif filter_urgent == "מקרה לא דחוף":
        filtered_list = [ p for p in filtered_list if p.get("מקרה דחוף") in [False, "לא", None, ""] or pd.isna(p.get("מקרה דחוף"))]
    if filter_date:
        # Only show people added on or after the selected date
        try:
            filter_date_str = filter_date.strftime("%Y-%m-%d") if hasattr(filter_date, "strftime") else str(filter_date)
            filtered_list = [p for p in filtered_list if pd.to_datetime(p.get("תאריך", None), errors="coerce") >= pd.to_datetime(filter_date_str)]
        except Exception:
            pass
    if filtered_list:
        df = pd.DataFrame(filtered_list)
        df.index += 1
        # Ensure 'תאריך' column is string for Arrow compatibility
        if 'תאריך' in df.columns:
            df['תאריך'] = df['תאריך'].apply(lambda x: x.strftime('%Y-%m-%d') if hasattr(x, 'strftime') else str(x))
        # Keep green check logic
        def highlight_yes(row):
            yes_fields = ["אישור ועדה", "דוח פסיכיאטרי", "דוח פסיכוסוציאלי", "דוח רפואי", "צילום תז"]
            if all(row.get(f) == "כן" for f in yes_fields):
                return ["background-color: lightgreen"] * len(row)
            return [""] * len(row)
        # Add urgent icon column if 'מקרה דחוף?' exists
        if "מקרה דחוף" in df.columns:
            df["מקרה דחוף"] = df["מקרה דחוף"].apply(lambda x: "🚨" if x in [True, "כן"] else "")
        styled_df = df.style.apply(highlight_yes, axis=1)
        # Add Google Maps link column if 'כתובת' exists
        if 'כתובת' in df.columns:
            st.dataframe(styled_df)
            st.markdown('---')
            st.subheader('תראה את הכתובת על המפה')
            addresses = [a for a in df['כתובת'] if a]
            selected_address = st.selectbox('בחר/י כתובת להציג על המפה', addresses)
            if st.button('הצג/י על המפה'):
                map_url = f"https://www.google.com/maps/search/{selected_address.replace(' ', '+')}"
                st.markdown(f"[Open in Google Maps]({map_url})", unsafe_allow_html=True)
        else:
            st.dataframe(styled_df)
            # --- Shift person to accepted list ---
        st.markdown("### העבר/י משתקם לרשימת המתקבלים")
        if len(df) > 0:
            person_names = [str(p.get("שם מלא", "")) for p in waiting_list]
            selected_person = st.selectbox("בחר/י משתקם להעברה לרשימת המתקבלים", person_names, key="move_to_accepted")
            target_branches = [b for b in FACILITY_BRANCHES[facility] if b != "הכל"]
            target_branch = st.selectbox("בחר/י סניף יעד לרשימת המתקבלים", target_branches, key="move_to_accepted_branch")
            if st.button("✅ העבר/י לרשימת המתקבלים"):
                # Remove from WaitingList DB and add to AcceptedList DB
                original_branch = None
                person_to_move = None
                if branch == "הכל":
                    for b in [b for b in FACILITY_BRANCHES[facility] if b != "הכל"]:
                        for i, p in enumerate(data_store[facility][b]):
                            p_name = str(p.get("שם מלא", "")) if isinstance(p, dict) else str(p)
                            if p_name == selected_person:
                                person_to_move = data_store[facility][b][i]
                                original_branch = b
                                break
                        if original_branch:
                            break
                else:
                    for i, p in enumerate(waiting_list):
                        p_name = str(p.get("שם מלא", "")) if isinstance(p, dict) else str(p)
                        if p_name == selected_person:
                            person_to_move = waiting_list[i]
                            original_branch = branch
                            break
                if person_to_move:
                    if not isinstance(person_to_move, dict):
                        person_to_move = {"שם מלא": str(person_to_move)}
                    accepted_person = {
                        "שם מלא": person_to_move.get("שם מלא", ""),
                        "תאריך המתנה": person_to_move.get("תאריך", ""),
                        "תאריך קבלה": datetime.today().strftime("%Y-%m-%d"),
                        "כתובת": person_to_move.get("כתובת", ""),
                        "גורם מפנה": person_to_move.get("גורם מפנה", ""),
                        "סניף מקורי": f"{original_branch if original_branch else ''}",
                        "אישור ועדה": person_to_move.get("אישור ועדה", ""),
                        "דוח פסיכיאטרי": person_to_move.get("דוח פסיכיאטרי", ""),
                        "דוח פסיכוסוציאלי": person_to_move.get("דוח פסיכוסוציאלי", ""),
                        "דוח רפואי": person_to_move.get("דוח רפואי", ""),
                        "צילום תז": person_to_move.get("צילום תז", ""),
                        "הערות": person_to_move.get("הערות", ""),
                        # New for DB ONLY
                        "סניף": target_branch,
                        "מרחב": facility
                    }
                    # Ensure 'מקרה דחוף' is boolean for Supabase
                    accepted_person["מקרה דחוף"] = True if person_to_move.get("מקרה דחוף") in [True, "כן", "true", "True", 1] else False
                    DBloader = SupabaseDBClient(
                        supabase_url="https://fpvswpsvpyqvwpkmxtgj.supabase.co",
                        supabase_key="eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6ImZwdnN3cHN2cHlxdndwa214dGdqIiwicm9sZSI6ImFub24iLCJpYXQiOjE3NTY5OTYyNTQsImV4cCI6MjA3MjU3MjI1NH0.d7IQonhpRMvoGcaG47gVA4JE95O5fFQfmvUe9WB6BpQ",
                        facility="גוש דן",
                        branches=FACILITY_BRANCHES["גוש דן"]
                    )
                    # Add to AcceptedList DB
                    DBloader.add_person_to_accepted_list(accepted_person)
                    # Remove from WaitingList DB
                    DBloader.remove_person_from_waiting_list(selected_person)
                    st.success(f"{selected_person} הועבר/ה לרשימת המתקבלים בסניף {target_branch}!")
                    st.rerun()
        # Delete person functionality
        st.markdown("---")
        st.markdown("### להוציא משתקם מהרשימת ההמתנה")
        if len(df) > 0:
            person_names = [str(p.get("שם מלא", "")) for p in waiting_list]
            selected_person = st.selectbox("בחר/י משתקם להסרה", person_names)
            if st.button("❌ להסיר משתקם"):
                # Remove first matching person
                for i, p in enumerate(waiting_list):
                    if str(p.get("שם מלא", "")) == selected_person:
                        DBloader = SupabaseDBClient(
                            supabase_url="https://fpvswpsvpyqvwpkmxtgj.supabase.co",
                            supabase_key="eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6ImZwdnN3cHN2cHlxdndwa214dGdqIiwicm9sZSI6ImFub24iLCJpYXQiOjE3NTY5OTYyNTQsImV4cCI6MjA3MjU3MjI1NH0.d7IQonhpRMvoGcaG47gVA4JE95O5fFQfmvUe9WB6BpQ",
                            facility="גוש דן",
                            branches=FACILITY_BRANCHES["גוש דן"]
                        )
                        DBloader.remove_person_from_waiting_list(selected_person)
                        st.success(f"Removed {selected_person} from the waiting list.")
                        st.rerun()
                        break
    else:
        st.info("No one is currently on the waiting list.")
    # Save Changes button for Gush_Dan branches
#     if facility == "גוש דן":
#         if st.button("💾 שמור/י את השינויים"):
#             loader = WaitingListDataLoaderClass(add_to_waitlist)
#             if DataType == "Excel":
#                 loader.write_to_excel(data_store, facility, excel_path, FACILITY_BRANCHES["גוש דן"])
#             st.success("!השינויים נשמרו בהצלחה")
        # --- Admin-only Excel download ---
#         if logged_in == "admin":
#             with open(excel_path, "rb") as f:
#                 st.download_button(
#                     label="הורד/י את קובץ האקסל",
#                     data=f,
#                     file_name="waiting_list_gush_dan.xlsx",
#                     mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
#                )

elif sidebar_choice == "➕ הוספת משתקם":

    st.header("הוספת משתקם לרשימת ההמתנה")
    col1, col2 = st.columns(2)
    with col1:
        facility_q = st.selectbox("בחר/י מרחב", FACILITIES, key="add_facility")
    with col2:
        branches_no_all = [b for b in FACILITY_BRANCHES[facility_q] if b != "הכל"]
        branch_q = st.selectbox("בחר/י סניף", branches_no_all, key="add_branch", index=None, placeholder="בחר/י סניף")
    from datetime import date
    # Questionnaire inputs (outside the form for immediate checkmark update)
    שם_מלא = st.text_input("הוסף/י את שם המשתקם", max_chars=50)
    תאריך = st.date_input("בחר/י תאריך הוספה", value=None)
    כתובת = st.text_input("הוסף/י כתובת", max_chars=100)
    גורם_מפנה = st.text_input("הוסף/י גורם מפנה", max_chars=100)
    st.markdown("**:בבקשה תמלא/י את השאלון הבא**")
    q1 = st.radio("אישור ועדה", ["כן", "לא"], index=1, horizontal=True)
    q2 = st.radio("דוח פסיכיאטרי עדכני", ["כן", "לא"], index=1, horizontal=True)
    q3 = st.radio("דוח פסיכוסוציאלי", ["כן", "לא"], index=1, horizontal=True)
    q4 = st.radio("דוח רפואי", ["כן", "לא"], index=1, horizontal=True)
    q5 = st.radio("צילום תעודת זהות", ["כן", "לא"], index=1, horizontal=True)
    comments = st.text_area("הערות נוספות", max_chars=200)
    מקרה_דחוף = st.checkbox("?מקרה דחוף", value=False)
    # Show checkmark if all answers are 'כן' (immediately after questions)
    show_check = all([q1 == "כן", q2 == "כן", q3 == "כן", q4 == "כן", q5 == "כן"])
    if show_check:
        st.markdown("<div style='text-align:center'><span style='font-size:2em;color:green'>&#10003;</span></div>", unsafe_allow_html=True)
    # Form for submission only
    with st.form("add_form", clear_on_submit=True):
        submitted = st.form_submit_button("הוספת משתקם לרשימת ההמתנה")
        if submitted:
            # Ensure date is saved as YYYY-MM-DD string
            date_str = תאריך.strftime("%Y-%m-%d") if hasattr(תאריך, "strftime") else str(תאריך)
            person = {
                "שם מלא": שם_מלא,
                "תאריך": date_str,
                "כתובת": כתובת,
                "גורם מפנה": גורם_מפנה,
                "אישור ועדה": q1,
                "דוח פסיכיאטרי": q2,
                "דוח פסיכוסוציאלי": q3,
                "דוח רפואי": q4,
                "צילום תז": q5,
                "הערות": comments,
                "מקרה דחוף": מקרה_דחוף,
                # New for DB ONLY
                "סניף": branch_q,
                "מרחב": facility_q
            }
            if not שם_מלא.strip():
                st.error("נא לבחור שם")
            elif branch_q == None:
                st.error("נא לבחור סניף")
            elif תאריך == None:
                st.error("נא לבחור תאריך")
            else:
                # loader = WaitingListDataLoaderClass(add_to_waitlist)
                # store = loader.read_excel_to_data_store(excel_path,"גוש דן",FACILITY_BRANCHES["גוש דן"])
                # st.session_state["waiting_lists"] = store
                # data_store = st.session_state["waiting_lists"]
                # add_to_waitlist(st.session_state["waiting_lists"], person, facility_q, branch_q)
                # loader.write_to_excel(data_store, "גוש דן", excel_path, FACILITY_BRANCHES["גוש דן"])
                DBloader = SupabaseDBClient(
                    supabase_url="https://fpvswpsvpyqvwpkmxtgj.supabase.co",
                    supabase_key="eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6ImZwdnN3cHN2cHlxdndwa214dGdqIiwicm9sZSI6ImFub24iLCJpYXQiOjE3NTY5OTYyNTQsImV4cCI6MjA3MjU3MjI1NH0.d7IQonhpRMvoGcaG47gVA4JE95O5fFQfmvUe9WB6BpQ",
                    facility="גוש דן",
                    branches=FACILITY_BRANCHES["גוש דן"]
                )
                DBloader.add_person(person)
                st.success(f"Added {שם_מלא} to {facility_q} - {branch_q} waiting list.")
                st.toast("המשתקם נוסף בהצלחה!", icon="✅")

elif sidebar_choice == "📝 עריכת משתקם":
    st.header("עריכת משתקם")
    col1, col2 = st.columns(2)
    with col1:
            facility = st.selectbox("בחר/י מרחב", FACILITIES, key="edit_facility")
    with col2:
        branches_no_all = [b for b in FACILITY_BRANCHES[facility] if b != "הכל"]
        branch = st.selectbox("בחר/י סניף", branches_no_all, key="edit_branch", index=None, placeholder="בחר/י סניף")
    if branch == None:
        st.info("אין משתקמים לעריכה בסניף זה.")
    else:
        waiting_list = get_waitlist(data_store, facility, branch)
        person_names = [str(p.get("שם מלא", "")) for p in waiting_list]
        selected_person_name = st.selectbox("בחר/י משתקם לעריכה", person_names)
        # Find the selected person
        selected_person = None
        for p in waiting_list:
            if str(p.get("שם מלא", "")) == selected_person_name:
                selected_person = p
                break
        if selected_person:
            # Editable fields
            Original_Name = selected_person.get("שם מלא", "")
            new_name = st.text_input("שם מלא", value=selected_person.get("שם מלא", ""))
            new_date = st.date_input("תאריך", value=selected_person.get("תאריך", ""))
            new_address = st.text_input("כתובת", value=selected_person.get("כתובת", ""))
            new_referrer = st.text_input("גורם מפנה", value=selected_person.get("גורם מפנה", ""))
            # --- Add branch switcher ---
            new_branch = st.selectbox("העבר/י לסניף אחר", branches_no_all, index=branches_no_all.index(branch))
            new_q1 = st.radio("אישור ועדה", ["כן", "לא"], index=0 if selected_person.get("אישור ועדה") == "כן" else 1, horizontal=True)
            new_q2 = st.radio("דוח פסיכיאטרי", ["כן", "לא"], index=0 if selected_person.get("דוח פסיכיאטרי") == "כן" else 1, horizontal=True)
            new_q3 = st.radio("דוח פסיכוסוציאלי", ["כן", "לא"], index=0 if selected_person.get("דוח פסיכוסוציאלי") == "כן" else 1, horizontal=True)
            new_q4 = st.radio("דוח רפואי", ["כן", "לא"], index=0 if selected_person.get("דוח רפואי") == "כן" else 1, horizontal=True)
            new_q5 = st.radio("צילום תז", ["כן", "לא"], index=0 if selected_person.get("צילום תז") == "כן" else 1, horizontal=True)
            new_comments = st.text_area("הערות", value=selected_person.get("הערות", ""))
            new_urgent = st.checkbox("?מקרה דחוף", value=selected_person.get("מקרה דחוף", False))
            if st.button("שמור/י שינויים במשקם"):
                selected_person["שם מלא"] = new_name
                selected_person["תאריך"] = new_date
                selected_person["כתובת"] = new_address
                selected_person["גורם מפנה"] = new_referrer
                selected_person["מקרה דחוף"] = new_urgent
                selected_person["אישור ועדה"] = new_q1
                selected_person["דוח פסיכיאטרי"] = new_q2
                selected_person["דוח פסיכוסוציאלי"] = new_q3
                selected_person["דוח רפואי"] = new_q4
                selected_person["צילום תז"] = new_q5
                selected_person["הערות"] = new_comments
                # For new DB Solution
                selected_person["סניף"] = new_branch
                selected_person["מרחב"] = facility
                # If branch changed, move person
                # if new_branch != branch:
                #     waiting_list.remove(selected_person)
                #     data_store[facility][new_branch].append(selected_person)
                # Save to Excel if Gush Dan
                if facility == "גוש דן":
                    DBloader = SupabaseDBClient(
                        supabase_url="https://fpvswpsvpyqvwpkmxtgj.supabase.co",
                        supabase_key="eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6ImZwdnN3cHN2cHlxdndwa214dGdqIiwicm9sZSI6ImFub24iLCJpYXQiOjE3NTY5OTYyNTQsImV4cCI6MjA3MjU3MjI1NH0.d7IQonhpRMvoGcaG47gVA4JE95O5fFQfmvUe9WB6BpQ",
                        facility="גוש דן",
                        branches=FACILITY_BRANCHES["גוש דן"]
                    )
                    selected_person = serialize_dates(selected_person)
                    try:
                        result = DBloader.edit_person(Original_Name, selected_person)
                        # If the method returns a response, check for error status
                        if hasattr(result, 'status_code') and result.status_code >= 400:
                            st.error(f"שגיאה בעדכון המשקם: {getattr(result, 'text', 'Unknown error')}")
                        else:
                            st.success("המשקם עודכן בהצלחה!")
                    except Exception as e:
                        st.error(f"עדכון המשקם נכשל: {e}")

elif sidebar_choice == "✅ מתקבלים":
    st.header("רשימת המתקבלים")
    # accepted_excel_path = "Data/accepted_list.xlsx"
    # if "accepted_lists" not in st.session_state:
    #    loader = WaitingListDataLoaderClass(add_to_waitlist)
    #    try:
    #        store = loader.read_excel_to_data_store(
    #            accepted_excel_path,
    #            "גוש דן",
    #            FACILITY_BRANCHES["גוש דן"]
    #        )
    #    except Exception as e:
    #        st.warning(f"Could not load Accepted Excel data: {e}")
    #    st.session_state["accepted_lists"] = store
    
    DBloader = SupabaseDBClient(
        supabase_url="https://fpvswpsvpyqvwpkmxtgj.supabase.co",
        supabase_key="eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6ImZwdnN3cHN2cHlxdndwa214dGdqIiwicm9sZSI6ImFub24iLCJpYXQiOjE3NTY5OTYyNTQsImV4cCI6MjA3MjU3MjI1NH0.d7IQonhpRMvoGcaG47gVA4JE95O5fFQfmvUe9WB6BpQ",
        facility="גוש דן",
        branches=FACILITY_BRANCHES["גוש דן"]
    )    
    try:
        store2 = DBloader.read_accepted_list()
    except Exception as e:
        st.warning(f"Could not load DB data: {e}")
    st.session_state["accepted_lists"] = store2
    
    data_store = st.session_state["accepted_lists"]
    col1, col2 = st.columns(2)
    with col1:
        facility = st.selectbox("בחר/י מרחב", FACILITIES, key="accepted_facility")
    with col2:
        branch = st.selectbox("בחר/י סניף", FACILITY_BRANCHES[facility], key="accepted_branch")
    st.subheader(f"רשימת המתקבלים עבור {facility} - {branch}")
    # --- Advanced Search & Filter Controls ---
    filter_col1, filter_col2, filter_col3 = st.columns(3)
    with filter_col1:
        search_name = st.text_input("🔍 חפש/י לפי שם", value="", key="accepted_search_name")
    with filter_col2:
        filter_urgent = st.selectbox("🆘 הצג/י רק מקרים דחופים", ("מקרה דחוף", "מקרה לא דחוף"), index=None, placeholder="בחר/י סוג מקרה", key="accepted_filter_urgent")
    with filter_col3:
        filter_date = st.date_input("📅 הצג/י מתקבלים מתאריך", value=None, key="accepted_filter_date")
    # Get all people for selected branch/facility
    if branch == "הכל":
        all_people = []
        for b in FACILITY_BRANCHES[facility]:
            if b != "הכל":
                all_people.extend(get_waitlist(data_store, facility, b))
        waiting_list = all_people
    else:
        waiting_list = get_waitlist(data_store, facility, branch)
    # --- Apply Filters ---
    filtered_list = waiting_list
    if search_name:
        filtered_list = [p for p in filtered_list if search_name.strip() in str(p.get("שם מלא", ""))]
    if filter_urgent == "מקרה דחוף":
        filtered_list = [p for p in filtered_list if p.get("מקרה דחוף") in [True, "כן"]]
    elif filter_urgent == "מקרה לא דחוף":
        filtered_list = [ p for p in filtered_list if p.get("מקרה דחוף") in [False, "לא", None, ""] or pd.isna(p.get("מקרה דחוף"))]
    if filter_date:
        # Only show people added on or after the selected date
        try:
            filter_date_str = filter_date.strftime("%Y-%m-%d") if hasattr(filter_date, "strftime") else str(filter_date)
            filtered_list = [p for p in filtered_list if pd.to_datetime(p.get("תאריך", None), errors="coerce") >= pd.to_datetime(filter_date_str)]
        except Exception:
            pass
    if filtered_list:
        df = pd.DataFrame(filtered_list)
        df.index += 1
        # Ensure 'תאריך' column is string for Arrow compatibility
        if 'תאריך' in df.columns:
            df['תאריך'] = df['תאריך'].apply(lambda x: x.strftime('%Y-%m-%d') if hasattr(x, 'strftime') else str(x))
        # Keep green check logic
        def highlight_yes(row):
            yes_fields = ["אישור ועדה", "דוח פסיכיאטרי", "דוח פסיכוסוציאלי", "דוח רפואי", "צילום תז"]
            if all(row.get(f) == "כן" for f in yes_fields):
                return ["background-color: lightgreen"] * len(row)
            return [""] * len(row)
        # Add urgent icon column if 'מקרה דחוף?' exists
        if "מקרה דחוף" in df.columns:
            df["מקרה דחוף"] = df["מקרה דחוף"].apply(lambda x: "🚨" if x in [True, "כן"] else "")
        styled_df = df.style.apply(highlight_yes, axis=1)
        st.dataframe(styled_df)
        # --- Move person back to waiting list ---
        st.markdown("---")
        st.markdown("### החזר/י משתקם לרשימת ההמתנה")
        person_names = [str(p.get("שם מלא", "")) for p in waiting_list]
        if person_names:
            selected_person = st.selectbox("בחר/י משתקם להחזרה לרשימת ההמתנה", person_names, key="move_to_waiting")
            target_branches = [b for b in FACILITY_BRANCHES[facility] if b != "הכל"]
            target_branch = st.selectbox("בחר/י סניף יעד לרשימת ההמתנה", target_branches, key="move_to_waiting_branch")
            if st.button("📋 החזר/י לרשימת המתנה"):
                # Remove from accepted list
                person_to_move = None
                if branch == "הכל":
                    # Search all branches except 'הכל' for the selected person
                    for b in [b for b in FACILITY_BRANCHES[facility] if b != "הכל"]:
                        for i, p in enumerate(data_store[facility][b]):
                            p_name = str(p.get("שם מלא", "")) if isinstance(p, dict) else str(p)
                            if p_name == selected_person:
                                person_to_move = data_store[facility][b].pop(i)
                                break
                        if person_to_move:
                            break
                else:
                    for i, p in enumerate(waiting_list):
                        p_name = str(p.get("שם מלא", "")) if isinstance(p, dict) else str(p)
                        if p_name == selected_person:
                            person_to_move = waiting_list.pop(i)
                            break
                if person_to_move:
                    # Prepare person dict for waiting list
                    waiting_person = {
                        "שם מלא": person_to_move.get("שם מלא", ""),
                        "תאריך": person_to_move.get("תאריך המתנה", person_to_move.get("תאריך", "")),
                        "כתובת": person_to_move.get("כתובת", ""),
                        "גורם מפנה": person_to_move.get("גורם מפנה", ""),
                        "אישור ועדה": person_to_move.get("אישור ועדה", ""),
                        "דוח פסיכיאטרי": person_to_move.get("דוח פסיכיאטרי", ""),
                        "דוח פסיכוסוציאלי": person_to_move.get("דוח פסיכוסוציאלי", ""),
                        "דוח רפואי": person_to_move.get("דוח רפואי", ""),
                        "צילום תז": person_to_move.get("צילום תז", ""),
                        "הערות": person_to_move.get("הערות", ""),
                        # "מקרה דחוף": person_to_move.get("מקרה דחוף", False),
                        # New for DB ONLY
                        "סניף": target_branch,
                        "מרחב": facility
                    }
                    # Ensure 'מקרה דחוף' is boolean for Supabase
                    waiting_person["מקרה דחוף"] = True if waiting_person.get("מקרה דחוף") in [True, "כן", "true", "True", 1] else False
                    DBloader = SupabaseDBClient(
                        supabase_url="https://fpvswpsvpyqvwpkmxtgj.supabase.co",
                        supabase_key="eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6ImZwdnN3cHN2cHlxdndwa214dGdqIiwicm9sZSI6ImFub24iLCJpYXQiOjE3NTY5OTYyNTQsImV4cCI6MjA3MjU3MjI1NH0.d7IQonhpRMvoGcaG47gVA4JE95O5fFQfmvUe9WB6BpQ",
                        facility="גוש דן",
                        branches=FACILITY_BRANCHES["גוש דן"]
                    )
                    print(waiting_person)
                    DBloader.add_person(waiting_person)
                    DBloader.remove_person_from_accepted_list(selected_person)
                    # Load waiting list from Excel/session
                    # waiting_excel_path = "Data/waiting_list_gush_dan.xlsx"
                    # if "waiting_lists" not in st.session_state:
                    #     loader = WaitingListDataLoaderClass(add_to_waitlist)
                    #     try:
                    #         store = loader.read_excel_to_data_store(waiting_excel_path,"גוש דן", FACILITY_BRANCHES["גוש דן"])
                    #     except Exception as e:
                    #         st.warning(f"Could not load Waiting Excel data: {e}")
                    #     st.session_state["waiting_lists"] = store
                    # waiting_store = st.session_state["waiting_lists"]
                    # Add to waiting list in the selected target branch
                    # waiting_store[facility][target_branch].append(waiting_person)
                    # Save both lists to Excel
                    # loader = WaitingListDataLoaderClass(add_to_waitlist)
                    # loader.write_to_excel(data_store, facility, accepted_excel_path, FACILITY_BRANCHES[facility])
                    # loader.write_to_excel(waiting_store, facility, waiting_excel_path, FACILITY_BRANCHES[facility])
                    st.success(f"{selected_person} הוחזר/ה לרשימת ההמתנה בסניף {target_branch}!")
                    st.rerun()
    else:
        st.info("No one is currently on the accepted list.")

elif sidebar_choice == "📊 סטטיסטיקה ודוחות":
    st.markdown("## 📊 סטטיסטיקה ודוחות")
    analytics_type = st.radio("בחר/י רשימה לניתוח", ["רשימת המתנה", "רשימת המתקבלים"], index=0)
    col1, col2 = st.columns(2)
    with col1:
        facility = st.selectbox("בחר/י מרחב", FACILITIES, key="stats_facility")
    with col2:
        branch = st.selectbox("בחר/י סניף", FACILITY_BRANCHES[facility], key="stats_branch")

    if analytics_type == "רשימת המתנה":
        # --- Waiting List Analytics ---
        stats_data_store = st.session_state.get("waiting_lists", {})
        stats = calculate_statistics(stats_data_store, facility, None if branch == "הכל" else branch)
        all_people = []
        if branch == "הכל":
            for b in FACILITY_BRANCHES[facility]:
                if b != "הכל":
                    all_people.extend(get_waitlist(stats_data_store, facility, b))
        else:
            all_people = get_waitlist(stats_data_store, facility, branch)
        total_people = len(all_people)
        total_yes_all = sum(
            1 for p in all_people
            if isinstance(p, dict) and all([
                p.get("אישור ועדה") == "כן",
                p.get("דוח פסיכיאטרי") == "כן",
                p.get("דוח פסיכוסוציאלי") == "כן",
                p.get("דוח רפואי") == "כן",
                p.get("צילום תז") == "כן"
            ])
        )
        total_urgent_cases = sum(
            1 for p in all_people
            if isinstance(p, dict) and p.get("מקרה דחוף") in [True, "כן"]
        )
        col1, col2, col3 = st.columns(3)
        with col1:
            st.metric(label="מספר משתקמים ברשימה", value=total_people)
        with col2:
            st.metric(label="מספר משתקמים שיש להם את כל הטפסים", value=total_yes_all)
        with col3:
            st.metric(label="מספר המקרים הדחופים", value=total_urgent_cases)
        if not stats:
            st.info("No data available for selected filters.")
        else:
            df_stats = pd.DataFrame(stats)
            if "dates" in df_stats.columns:
                df_stats["dates"] = pd.to_datetime(df_stats["dates"], errors="coerce")
            if branch == "הכל":
                bar = alt.Chart(df_stats).mark_bar().encode(
                    x="branch",
                    y="count",
                    color="branch",
                    tooltip=["branch", "count"]
                ).properties(title="מספר ממתינים מכל סניף")
                st.altair_chart(bar, use_container_width=True)
                box_data = []
                for s in stats:
                    branch_name = s["branch"]
                    dates = s["dates"]
                    for d in dates:
                        wait_days = (datetime.today() - datetime.strptime(str(d), "%Y-%m-%d")).days if isinstance(d, str) else (datetime.today() - d).days
                        box_data.append({"branch": branch_name, "wait_days": wait_days})
                df_box = pd.DataFrame(box_data)
                if not df_box.empty:
                    df_box["wait_days"] = pd.to_numeric(df_box["wait_days"], errors="coerce")
                    mean_df = df_box.groupby("branch", as_index=False)["wait_days"].mean()
                    mean_df["stat"] = "Mean"
                    median_df = df_box.groupby("branch", as_index=False)["wait_days"].median()
                    median_df["stat"] = "Median"
                    stat_df = pd.concat([mean_df, median_df])
                    stat_points = alt.Chart(stat_df).mark_point(filled=True, size=200).encode(
                        x="branch",
                        y=alt.Y("wait_days", title="Waiting Time (days)"),
                        color="branch",
                        shape="stat",
                        tooltip=["branch", "wait_days", "stat"]
                    ).properties(title="זמן המתנה עבור כל סניף (ממוצע וחציון)")
                    st.altair_chart(stat_points, use_container_width=True)
            all_dates = []
            for s in stats:
                all_dates.extend(s["dates"])
            if all_dates:
                df_dates = pd.DataFrame({"תאריך": all_dates})
                df_dates["תאריך"] = pd.to_datetime(df_dates["תאריך"])
                df_dates["day"] = df_dates["תאריך"].dt.date
                df_dates["month"] = df_dates["תאריך"].dt.to_period("M")
                day_counts = df_dates.groupby("day").size().reset_index(name="count")
                month_counts = df_dates.groupby("month").size().reset_index(name="count")
                month_counts["month"] = month_counts["month"].astype(str)
                month_chart = alt.Chart(month_counts).mark_bar().encode(
                    x=alt.X("month", title="Month"),
                    y="count",
                    tooltip=["month", "count"]
                ).properties(title="כמות ממתינים חדשים בכל חודש")
                st.altair_chart(month_chart, use_container_width=True)
    else:
        # --- Accepted List Analytics ---
        accepted_excel_path = "Data/accepted_list.xlsx"
        if "accepted_lists" not in st.session_state:
            loader = WaitingListDataLoaderClass(add_to_waitlist)
            try:
                store = loader.read_excel_to_data_store(
                    accepted_excel_path,
                    "גוש דן",
                    FACILITY_BRANCHES["גוש דן"]
                )
            except Exception as e:
                st.warning(f"Could not load Accepted Excel data: {e}")
            st.session_state["accepted_lists"] = store
        stats_data_store = st.session_state["accepted_lists"]
        stats = calculate_statistics(stats_data_store, facility, None if branch == "הכל" else branch)
        all_people = []
        if branch == "הכל":
            for b in FACILITY_BRANCHES[facility]:
                if b != "הכל":
                    all_people.extend(get_waitlist(stats_data_store, facility, b))
        else:
            all_people = get_waitlist(stats_data_store, facility, branch)
        total_people = len(all_people)
        total_yes_all = sum(
            1 for p in all_people
            if isinstance(p, dict) and all([
                p.get("אישור ועדה") == "כן",
                p.get("דוח פסיכיאטרי") == "כן",
                p.get("דוח פסיכוסוציאלי") == "כן",
                p.get("דוח רפואי") == "כן",
                p.get("צילום תז") == "כן"
            ])
        )
        total_urgent_cases = sum(
            1 for p in all_people
            if isinstance(p, dict) and p.get("מקרה דחוף") in [True, "כן"]
        )
        col1, col2, col3 = st.columns(3)
        with col1:
            st.metric(label="מספר מתקבלים ברשימה", value=total_people)
        with col2:
            st.metric(label="מספר מתקבלים שיש להם את כל הטפסים", value=total_yes_all)
        with col3:
            st.metric(label="מספר המקרים הדחופים", value=total_urgent_cases)
        if not stats:
            st.info("No data available for selected filters.")
        else:
            df_stats = pd.DataFrame(stats)
            if "dates" in df_stats.columns:
                df_stats["dates"] = pd.to_datetime(df_stats["dates"], errors="coerce")
            if branch == "הכל":
                bar = alt.Chart(df_stats).mark_bar().encode(
                    x="branch",
                    y="count",
                    color="branch",
                    tooltip=["branch", "count"]
                ).properties(title="מספר מתקבלים מכל סניף")
                st.altair_chart(bar, use_container_width=True)
            # --- Chart 1: Number accepted per month ---
            accepted_people = []
            for b in FACILITY_BRANCHES[facility]:
                if b != "הכל":
                    accepted_people.extend(get_waitlist(stats_data_store, facility, b))
            df_accepted = pd.DataFrame(accepted_people)
            if not df_accepted.empty and "תאריך קבלה" in df_accepted.columns:
                df_accepted["תאריך קבלה"] = pd.to_datetime(df_accepted["תאריך קבלה"], errors="coerce")
                df_accepted["month"] = df_accepted["תאריך קבלה"].dt.to_period("M")
                month_counts = df_accepted.groupby("month").size().reset_index(name="count")
                month_counts["month"] = month_counts["month"].astype(str)
                month_chart = alt.Chart(month_counts).mark_bar().encode(
                    x=alt.X("month", title="חודש קבלה"),
                    y="count",
                    tooltip=["month", "count"]
                ).properties(title="כמות מתקבלים בכל חודש")
                st.altair_chart(month_chart, use_container_width=True)
            # --- Chart 2: Average time from תאריך המתנה to תאריך קבלה per month ---
            if not df_accepted.empty and "תאריך קבלה" in df_accepted.columns and "תאריך המתנה" in df_accepted.columns:
                df_accepted["תאריך המתנה"] = pd.to_datetime(df_accepted["תאריך המתנה"], errors="coerce")
                df_accepted["wait_days"] = (df_accepted["תאריך קבלה"] - df_accepted["תאריך המתנה"]).dt.days
                avg_wait_by_month = df_accepted.groupby(df_accepted["תאריך קבלה"].dt.to_period("M"))["wait_days"].mean().reset_index()
                avg_wait_by_month["month"] = avg_wait_by_month["תאריך קבלה"].astype(str)
                avg_wait_chart = alt.Chart(avg_wait_by_month).mark_line(point=True).encode(
                    x=alt.X("month", title="חודש קבלה"),
                    y=alt.Y("wait_days", title="ממוצע ימים המתנה עד קבלה"),
                    tooltip=["month", "wait_days"]
                ).properties(title="ממוצע זמן המתנה עד קבלה בכל חודש")
                st.altair_chart(avg_wait_chart, use_container_width=True)

#    
# st.markdown("---")
# debug_mode = st.checkbox("🐛 Debug Mode", value=False)
# if debug_mode and logged_in:
#     show_debug_panel()
# --- End of File ---
