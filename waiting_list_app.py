"""
Streamlit Waiting List Manager for Multiple Facilities and Branches

Features:
- Add a person to a waiting list for a specific facility and branch
- View waiting lists per facility and branch
- UI: Dropdowns, text input, table view
- Data: In-memory nested dict, easy to swap for DB
- Validation: No empty names
- Auto-refresh after adding
"""


import streamlit as st
from typing import Dict, List
import pandas as pd
import os
import requests
import time
import altair as alt
from datetime import datetime
from WaitingListDataLoader import WaitingListDataLoaderClass

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
            if filtered and "date" in filtered[0]:
                dates = [datetime.strptime(p["date"], "%Y-%m-%d") for p in filtered if p.get("date")]
                if dates:
                    days = [(datetime.today() - d).days for d in dates]
                    avg_wait = sum(days) / len(days)
            stats.append({
                "facility": fac,
                "branch": br,
                "count": len(filtered),
                "avg_wait": avg_wait if avg_wait is not None else 0,
                "dates": [p["date"] for p in filtered if p.get("date")]
            })
    return stats

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
# DataType = "Google drive"
DataType = "Excel"



# --- Data Store Logic ---
def init_data_store() -> Dict[str, Dict[str, List[str]]]:
    """Initialize the waiting list data store."""
    return {facility: {branch: [] for branch in FACILITY_BRANCHES[facility]} for facility in FACILITIES}

def add_to_waitlist(data_store: Dict[str, Dict[str, List[str]]], name: str, facility: str, branch: str) -> bool:
    """Add a person to the waiting list. Returns True if added, False if invalid."""
    # This function will now expect a dict for person data
    if isinstance(name, dict):
        person = name
        if not person.get("name", "").strip():
            return False
        data_store[facility][branch].append(person)
        return True
    else:
        name = name.strip()
        if not name:
            return False
        data_store[facility][branch].append({"name": name})
        return True

def get_waitlist(data_store: Dict[str, Dict[str, List[str]]], facility: str, branch: str) -> List[str]:
    """Get the waiting list for a facility and branch."""
    return data_store[facility][branch]

# --- Streamlit UI ---


st.set_page_config(page_title="Waiting List Manager", layout="centered")

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
            people = [row for row in df.to_dict(orient="records") if str(row.get("name", "")).strip()]
            branch_data[branch] = people
        else:
            branch_data[branch] = []
    return branch_data


if DataType ==  "Google drive":    
    CREDS_JSON_PATH = "credentials/service_account.json"
    SHEET_ID = "17dHYU80oPg8PhH586AOinuFWSMsLpXQD"
    FACILITY = "גוש דן"
    BRANCH_GIDS = {
     	"תל אביב": "732546362",      # Replace with actual gid for Tel Aviv tab
     	"רמת גן - גבעתיים": "1227991176",
        "בקעת אונו": "969356485", 
        "הרצליה - רמת השרון": "235834184",
        "חולון - בת ים": "1402390217",
        "להטבק": "1040400252",
        "טראומה מורכבת": "976592902",
        "דרי רחוב": "1771885286"
    }
    if "waiting_lists" not in st.session_state:
         loader = WaitingListDataLoaderClass(add_to_waitlist)
         try:
             store = loader.read_google_sheet_to_data_store(SHEET_ID, FACILITY, BRANCH_GIDS)
         except Exception as e:
             st.warning(f"Could not load Excel data: {e}")
         st.session_state["waiting_lists"] = store

    data_store = st.session_state["waiting_lists"]
elif DataType == "Excel":
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


# --- User Authentication ---
VALID_USERS = {
    "admin": "admin",
    "user1": "pass1",
    "user2": "pass2"
}

def check_login(username, password):
    return VALID_USERS.get(username) == password

# Sidebar navigation


def show_debug_panel():
    """Display debug information panel (Session State, Data, Module Status)."""
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
    sidebar_choice = st.radio(
        "",
        ["🏠 דף בית", "📋 רשימת המתנה", "➕ הוספת משתקם", "📊 סטטיסטיקה ודוחות"],
        index=0
    )
    st.markdown("---")
    debug_mode = st.checkbox("🐛 Debug Mode", value=False)
    if debug_mode and logged_in:
        show_debug_panel()

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
            login_btn = st.form_submit_button("התחבר")
            if login_btn:
                if check_login(username, password):
                    st.success(f"ברוך הבא, {username}!")
                    st.session_state["logged_in_user"] = username
                else:
                    st.error("שם משתמש או סיסמה לא נכונים.")
    else:
        st.success(f"אתה מחובר כ-{logged_in}.")

if sidebar_choice != "🏠 דף בית" and not logged_in:
    st.warning("Please log in to access the app features.")
    st.stop()

if sidebar_choice == "📋 רשימת המתנה":

    st.header("רשימת המתנה")
    col1, col2 = st.columns(2)
    with col1:
        facility = st.selectbox("בחר מרחב", FACILITIES, key="view_facility")
    with col2:
        branch = st.selectbox("בחר סניף", FACILITY_BRANCHES[facility], key="view_branch")
    st.subheader(f"רשימת המתנה עבור {facility} - {branch}")

    if branch == "הכל":
        # Combine all branches for the selected facility
        all_people = []
        for b in FACILITY_BRANCHES[facility]:
            if b != "הכל":
                all_people.extend(get_waitlist(data_store, facility, b))
        waiting_list = all_people
    else:
        waiting_list = get_waitlist(data_store, facility, branch)


    if waiting_list:
        df = pd.DataFrame(waiting_list)
        df.index += 1

        def highlight_yes(row):
            yes_fields = ["resident", "special_needs", "first_time", "urgent", "willing_to_wait"]
            if all(row.get(f) == "כן" for f in yes_fields):
                return ["background-color: lightgreen"] * len(row)
            return [""] * len(row)

        styled_df = df.style.apply(highlight_yes, axis=1)

        # Add Google Maps link column if 'address' exists
        if 'address' in df.columns:
            st.dataframe(styled_df)
            st.markdown('---')
            st.subheader('תראה את הכתובת על המפה')
            addresses = [a for a in df['address'] if a]
            selected_address = st.selectbox('בחר כתובת להציג על המפה', addresses)
            if st.button('הצג על המפה'):
                map_url = f"https://www.google.com/maps/search/{selected_address.replace(' ', '+')}"
                st.markdown(f"[Open in Google Maps]({map_url})", unsafe_allow_html=True)
        else:
            st.dataframe(styled_df)

        # Delete person functionality
        st.markdown("---")
        st.markdown("### הוצא משתקם מהרשימת ההמתנה")
        if len(df) > 0:
            person_names = [str(p.get("name", "")) for p in waiting_list]
            selected_person = st.selectbox("בחר משתקם להסרה", person_names)
            if st.button("❌ הוצא משתקם"):
                # Remove first matching person
                for i, p in enumerate(waiting_list):
                    if str(p.get("name", "")) == selected_person:
                        del waiting_list[i]
                        st.success(f"Removed {selected_person} from the waiting list.")
                        st.rerun()
                        break
    else:
        st.info("No one is currently on the waiting list.")

    # Save Changes button for Gush_Dan branches
    if facility == "גוש דן":
        if st.button("💾 שמור את השינויים"):
            loader = WaitingListDataLoaderClass(add_to_waitlist)
            if DataType == "Google drive":
                loader.write_to_google_sheet(data_store, facility, SHEET_ID, FACILITY_BRANCHES, CREDS_JSON_PATH)
            elif DataType == "Excel":
                xl_path = excel_path
                loader.write_to_excel(data_store, facility, xl_path, FACILITY_BRANCHES["גוש דן"])
            st.success("Changes saved to Excel file!")

elif sidebar_choice == "➕ הוספת משתקם":

    st.header("הוספת משתקם לרשימת ההמתנה")
    col1, col2 = st.columns(2)
    with col1:
        facility_q = st.selectbox("בחר מרחב", FACILITIES, key="add_facility")
    with col2:
        branches_no_all = [b for b in FACILITY_BRANCHES[facility_q] if b != "הכל"]
        branch_q = st.selectbox("בחר סניף", branches_no_all, key="add_branch")
    from datetime import date
    # Questionnaire inputs (outside the form for immediate checkmark update)
    name = st.text_input("הוסף את שם המשתקם", max_chars=50)
    selected_date = st.date_input("בחר תאריך הוספה", value=date.today())
    address = st.text_input("הוסף כתובת", max_chars=100)
    st.markdown("**:בבקשה תמלא את השאלון הבא**")
    q1 = st.radio("אישור ועדה", ["כן", "לא"], index=1, horizontal=True)
    q2 = st.radio("דוח פסיכיאטרי עדכני", ["כן", "לא"], index=1, horizontal=True)
    q3 = st.radio("דוח פסיכוסוציאלי", ["כן", "לא"], index=1, horizontal=True)
    q4 = st.radio("דוח רפואי", ["כן", "לא"], index=1, horizontal=True)
    q5 = st.radio("צילום תעודת זהות", ["כן", "לא"], index=1, horizontal=True)
    # Show checkmark if all answers are 'כן' (immediately after questions)
    show_check = all([q1 == "כן", q2 == "כן", q3 == "כן", q4 == "כן", q5 == "כן"])
    if show_check:
        st.markdown("<div style='text-align:center'><span style='font-size:2em;color:green'>&#10003;</span></div>", unsafe_allow_html=True)
    # Form for submission only
    with st.form("add_form", clear_on_submit=True):
        submitted = st.form_submit_button("הוסף משתקם לרשימת ההמתנה")
        if submitted:
            # Ensure date is saved as YYYY-MM-DD string
            date_str = selected_date.strftime("%Y-%m-%d") if hasattr(selected_date, "strftime") else str(selected_date)
            person = {
                "name": name,
                "date": date_str,
                "address": address,
                "resident": q1,
                "special_needs": q2,
                "first_time": q3,
                "urgent": q4,
                "willing_to_wait": q5
            }
            if not name.strip():
                st.error("Name cannot be empty.")
            else:
                add_to_waitlist(st.session_state["waiting_lists"], person, facility_q, branch_q)
                st.success(f"Added {name} to {facility_q} - {branch_q} waiting list.")
                st.toast("המשתקם נוסף בהצלחה!", icon="✅")

elif sidebar_choice == "📊 סטטיסטיקה ודוחות":
    st.markdown("## 📊 סטטיסטיקה ודוחות")
    col1, col2 = st.columns(2)
    with col1:
        facility = st.selectbox("בחר מרחב", FACILITIES, key="stats_facility")
    with col2:
        branch = st.selectbox("בחר סניף", FACILITY_BRANCHES[facility], key="stats_branch")
    stats = calculate_statistics(data_store, facility, None if branch == "הכל" else branch)
    # --- Total statistics ---
    # Gather all people for selected facility/branch
    all_people = []
    if branch == "הכל":
        for b in FACILITY_BRANCHES[facility]:
            if b != "הכל":
                all_people.extend(get_waitlist(data_store, facility, b))
    else:
        all_people = get_waitlist(data_store, facility, branch)

    total_people = len(all_people)
    total_yes_all = sum(
        1 for p in all_people
        if isinstance(p, dict) and all([
            p.get("resident") == "כן",
            p.get("special_needs") == "כן",
            p.get("first_time") == "כן",
            p.get("urgent") == "כן",
            p.get("willing_to_wait") == "כן"
        ])
    )
    col1, col2 = st.columns(2)
    with col1:
        st.metric(label="מספר משתקמים ברשימה", value=total_people)
    
    with col2:
        st.metric(label="מספר משתקמים שיש להם את כל הטפסים", value=total_yes_all)

    if not stats:
        st.info("No data available for selected filters.")
    else:
        df_stats = pd.DataFrame(stats)
        if branch == "הכל":
            # Number of people waiting per branch
            bar = alt.Chart(df_stats).mark_bar().encode(
                x="branch",
                y="count",
                color="branch",
                tooltip=["branch", "count"]
            ).properties(title="מספר ממתינים מכל סניף")
            st.altair_chart(bar, use_container_width=True)
            # Boxplot of waiting times per branch
            # Gather all waiting times per branch
            box_data = []
            for s in stats:
                branch_name = s["branch"]
                dates = s["dates"]
                for d in dates:
                    wait_days = (datetime.today() - datetime.strptime(d, "%Y-%m-%d")).days
                    box_data.append({"branch": branch_name, "wait_days": wait_days})
            df_box = pd.DataFrame(box_data)
            if not df_box.empty:
                # Calculate mean and median per branch
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
        # Load/occupancy trends by day and month
        all_dates = []
        for s in stats:
            all_dates.extend(s["dates"])
        if all_dates:
            df_dates = pd.DataFrame({"date": all_dates})
            df_dates["date"] = pd.to_datetime(df_dates["date"])
            df_dates["day"] = df_dates["date"].dt.date
            df_dates["month"] = df_dates["date"].dt.to_period("M")
            day_counts = df_dates.groupby("day").size().reset_index(name="count")
            month_counts = df_dates.groupby("month").size().reset_index(name="count")
            # Convert month to string for Altair axis
            month_counts["month"] = month_counts["month"].astype(str)
            month_chart = alt.Chart(month_counts).mark_bar().encode(
                x=alt.X("month", title="Month"),
                y="count",
                tooltip=["month", "count"]
            ).properties(title="כמות משתקמים חדשים בכל חודש")
            st.altair_chart(month_chart, use_container_width=True)


# --- End of File ---
