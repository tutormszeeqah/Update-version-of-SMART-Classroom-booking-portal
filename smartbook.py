import streamlit as st
import pandas as pd
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from datetime import datetime, date
import calendar
import urllib.parse
from PIL import Image
from streamlit_gsheets import GSheetsConnection

# ==========================================
# 1. PAGE CONFIGURATION & CUSTOM STYLING
# ==========================================
st.set_page_config(
    page_title="PTES Smart Classroom Digital Log",
    page_icon="💻",
    layout="wide"
)

# Custom CSS for Sidebar, Main Dashboard Background, Tabs, and Text Styling
st.markdown("""
    <style>
        /* 1. Main Dashboard / Front Background Color */
        [data-testid="stAppViewContainer"] {
            background-color: #8FF8FA;
        }

        /* Keep header background consistent with main background */
        [data-testid="stHeader"] {
            background-color: transparent;
        }

        /* 2. Custom Sidebar Background Color */
        [data-testid="stSidebar"] {
            background-color: #F7E987;
            padding-top: 1rem;
        }

        /* 3. Custom Tabs Background & Styling */
        div[data-baseweb="tab-list"] {
            gap: 8px;
            background-color: #F0F4F9;
            padding: 8px;
            border-radius: 10px;
        }

        button[data-baseweb="tab"] {
            background-color: #FFFFFF;
            border-radius: 8px;
            padding: 8px 16px;
            font-weight: 600;
            color: #333333;
            border: 1px solid #D1D5DB;
        }

        /* Styling for Currently Selected Active Tab */
        button[data-baseweb="tab"][aria-selected="true"] {
            background-color: #1A73E8 !important;
            color: #FFFFFF !important;
            border: 1px solid #1A73E8 !important;
        }

        /* 4. Subtitle Custom Font Styling */
        .school-subtitle {
            font-size: 24px !important;
            font-weight: 700 !important;
            color: #8E24AA !important;
            margin-top: -10px;
            margin-bottom: 25px;
        }
    </style>
""", unsafe_allow_html=True)

# Admin WhatsApp Phone Number
ADMIN_WA_NUMBER = "6738358186"

# Initialize Google Sheets Connection
conn = st.connection("gsheets", type=GSheetsConnection)

# Facilities Options List
FACILITIES = [
    "Interactive SMART Panel",
    "Chromebook devices",
    "Recording Terminal",
    "Internet Access",
    "SMART TV"
]

# Available Time Slots
TIME_SLOTS = [
    "08:00 - 09:45",
    "10:15 - 12:15",
    "13:15 - 15:15"
]

# ==========================================
# 2. HELPER FUNCTIONS
# ==========================================

def load_booking_data():
    """Fetches real-time booking records from Google Sheets."""
    try:
        df = conn.read(ttl=0)
        return df if df is not None else pd.DataFrame()
    except Exception as e:
        st.error(f"Error loading database: {e}")
        return pd.DataFrame()

def send_notification_email(booking_details):
    """Sends an automated HTML email notification using Gmail SMTP credentials from secrets."""
    try:
        sender_email = st.secrets["SENDER_EMAIL"]
        sender_password = st.secrets["SENDER_PASSWORD"]
        receiver_email = st.secrets["ADMIN_RECEIVER_EMAIL"]

        subject = f"🔔 New Booking Alert: {booking_details['Facilities']} ({booking_details['Date']})"
        
        html_content = f"""
        <html>
        <body style="font-family: Arial, sans-serif; color: #333;">
            <h2 style="color: #1A73E8;">PUSAT TINGKATAN ENAM SENGKURONG</h2>
            <h3>Smart Classroom Reservation Notification</h3>
            <hr>
            <p>A new classroom reservation has been recorded:</p>
            <ul>
                <li><b>Name:</b> {booking_details['Name']}</li>
                <li><b>Department:</b> {booking_details['Department']}</li>
                <li><b>Facilities Requested:</b> {booking_details['Facilities']}</li>
                <li><b>Date:</b> {booking_details['Date']}</li>
                <li><b>Time Slot:</b> {booking_details['Time_Slot']}</li>
            </ul>
            <hr>
            <p style="font-size: 0.8em; color: #777;">This is an automated system message from PTES SmartLab Digitalog.</p>
        </body>
        </html>
        """

        msg = MIMEMultipart("alternative")
        msg["Subject"] = subject
        msg["From"] = f"PTES SmartLab <{sender_email}>"
        msg["To"] = receiver_email
        msg.attach(MIMEText(html_content, "html"))

        # Send via Gmail SMTP
        server = smtplib.SMTP("smtp.gmail.com", 587)
        server.starttls()
        server.login(sender_email, sender_password)
        server.send_message(msg)
        server.quit()
        return True
    except Exception as e:
        st.warning(f"Booking saved, but notification email could not be sent: {e}")
        return False

# ==========================================
# 3. SIDEBAR BRANDING & LAYOUT
# ==========================================
with st.sidebar:
    try:
        logo = Image.open("ptes_logo.png")
        st.image(logo, use_container_width=True)
    except Exception:
        st.info("📌 Add 'ptes_logo.png' to your GitHub repository to display the school logo.")

    st.title("PTES SmartLab")
    st.caption("Nurturing Resilient Leaders & Future Ready Citizens")
    st.markdown("---")
    
    # Quick DB status check
    df_check = load_booking_data()
    if not df_check.empty:
        st.success("🟢 Google Sheets Connected")
    else:
        st.warning("🟡 Sheet empty or initializing...")

# ==========================================
# 4. MAIN APPLICATION INTERFACE
# ==========================================
st.title("💻 Smart Classroom Booking Platform")

# Subtitle with custom purple styling
st.markdown('<p class="school-subtitle">Pusat Tingkatan Enam Sengkurong</p>', unsafe_allow_html=True)

tab_book, tab_calendar, tab_admin = st.tabs(["📝 New Booking", "📅 Interactive Calendar", "🔒 Admin Portal"])

# ------------------------------------------
# TAB 1: NEW BOOKING FORM & PREVIEW
# ------------------------------------------
with tab_book:
    st.subheader("Reserve Smart Classroom Facilities")
    
    with st.form("booking_form", clear_on_submit=False):
        col1, col2 = st.columns(2)
        
        with col1:
            name = st.text_input("Name *")
            department = st.selectbox("Department *", [
                "Computing", "Business / Accounting / Economics", "English/G.P/Malay", 
                "Mathematics", "Sciences", "Languages", "Humanities", "Administration", "Others"
            ])
            # Multi-select widget allowing tutors to choose multiple items
            selected_facilities = st.multiselect(
                "Facilities Required *", 
                FACILITIES, 
                default=["Interactive SMART Panel"]
            )

        with col2:
            booking_date = st.date_input("Date *", min_value=date.today())
            time_slot = st.selectbox("Time Slot *", TIME_SLOTS)
            
            # Notification Preference Selector
            notify_option = st.selectbox("Notify Admin via", [
                "Email Notification", 
                "WhatsApp Link", 
                "No Notification"
            ])

        submitted = st.form_submit_button("Submit & Confirm Reservation")

        if submitted:
            if not name or not selected_facilities:
                st.error("⚠️ Please fill in all required fields marked with *, including selecting at least one facility.")
            else:
                date_str = booking_date.strftime("%d/%m/%Y")
                # Format the list into a clean string for storage and notification
                facilities_str = ", ".join(selected_facilities)
                df_existing = load_booking_data()

                # Clash Detection Logic
                clash = False
                if not df_existing.empty and {"Date", "Time_Slot"}.issubset(df_existing.columns):
                    matches = df_existing[
                        (df_existing["Date"].astype(str) == date_str) &
                        (df_existing["Time_Slot"] == time_slot)
                    ]
                    if not matches.empty:
                        clash = True

                if clash:
                    st.error(f"❌ **Booking Conflict:** The time slot **{time_slot}** on **{date_str}** is already booked. Please select another slot or date.")
                else:
                    new_entry = pd.DataFrame([{
                        "Name": name,
                        "Department": department,
                        "Date": date_str,
                        "Time_Slot": time_slot,
                        "Facilities": facilities_str
                    }])

                    updated_df = pd.concat([df_existing, new_entry], ignore_index=True)
                    conn.update(data=updated_df)
                    
                    st.success("🎉 Booking successfully recorded!")
                    
                    st.markdown("---")
                    st.markdown("### 📋 Booked SmartLab Reservation Summary")
                    
                    preview_container = st.container(border=True)
                    with preview_container:
                        p_col1, p_col2 = st.columns(2)
                        with p_col1:
                            st.markdown(f"👤 **Name:** `{name}`")
                            st.markdown(f"🏢 **Department:** `{department}`")
                            st.markdown(f"🏫 **Facilities Required:** `{facilities_str}`")
                        with p_col2:
                            st.markdown(f"📅 **Date:** `{date_str}`")
                            st.markdown(f"⏰ **Time Slot:** `{time_slot}`")
                            st.markdown("STATUS: `CONFIRMED`")

                    booking_dict = new_entry.iloc[0].to_dict()
                    
                    if notify_option == "Email Notification":
                        with st.spinner("Notifying Admin via automated email..."):
                            email_sent = send_notification_email(booking_dict)
                        if email_sent:
                            st.info("✉️ Admin notified via automated email.")
                            
                    elif notify_option == "WhatsApp Link":
                        wa_message = (
                            f"📌 *NEW SMARTLAB BOOKING NOTIFICATION*\n\n"
                            f"👤 *Name:* {name}\n"
                            f"🏢 *Department:* {department}\n"
                            f"🏫 *Facilities:* {facilities_str}\n"
                            f"📅 *Date:* {date_str}\n"
                            f"⏰ *Time Slot:* {time_slot}"
                        )
                        encoded_msg = urllib.parse.quote(wa_message)
                        wa_url = f"https://wa.me/{ADMIN_WA_NUMBER}?text={encoded_msg}"
                        
                        st.markdown(f'👉 [**Click Here to Send WhatsApp Notification to Admin**]({wa_url})')

# ------------------------------------------
# TAB 2: INTERACTIVE CALENDAR SCHEDULE VIEW
# ------------------------------------------
with tab_calendar:
    st.subheader("📅 Monthly Interactive Schedule Calendar")
    
    master_data = load_booking_data()

    col_m, col_y = st.columns(2)
    with col_m:
        month_names = list(calendar.month_name)[1:]
        selected_month_str = st.selectbox("Select Month", month_names, index=datetime.today().month - 1)
        selected_month = month_names.index(selected_month_str) + 1
    with col_y:
        selected_year = st.number_input("Select Year", min_value=2024, max_value=2030, value=datetime.today().year)

    if 'selected_calendar_day' not in st.session_state:
        st.session_state.selected_calendar_day = datetime.today().day

    if not master_data.empty:
        display_df = master_data.copy()
        
        display_df['datetime_obj'] = pd.to_datetime(display_df['Date'], dayfirst=True, errors='coerce')

        month_data = display_df[
            (display_df['datetime_obj'].dt.month == selected_month) &
            (display_df['datetime_obj'].dt.year == selected_year)
        ]

        cal = calendar.Calendar(firstweekday=0)
        month_days = cal.monthdayscalendar(selected_year, selected_month)

        days_header = ["Mon", "Tue", "Wed", "Thu", "Fri", "Sat", "Sun"]
        cols = st.columns(7)
        for idx, header in enumerate(days_header):
            cols[idx].markdown(f"### {header}")

        st.divider()

        for week in month_days:
            grid_cols = st.columns(7)
            for i, day in enumerate(week):
                with grid_cols[i]:
                    if day != 0:
                        day_str = f"{day:02d}/{selected_month:02d}/{selected_year}"
                        
                        day_bookings = month_data[
                            (month_data['Date'].astype(str) == day_str) | 
                            (month_data['datetime_obj'].dt.day == day)
                        ]
                        booking_count = len(day_bookings)

                        if booking_count > 0:
                            label = f"🔴 {day:02d} ({booking_count})"
                        else:
                            label = f"⚪ {day:02d}"

                        if st.button(label, key=f"btn_day_{day}_{selected_month}_{selected_year}", use_container_width=True):
                            st.session_state.selected_calendar_day = day

        st.divider()

        active_day = st.session_state.selected_calendar_day
        max_days = calendar.monthrange(selected_year, selected_month)[1]
        if active_day > max_days:
            active_day = max_days

        inspected_date_str = f"{active_day:02d}/{selected_month:02d}/{selected_year}"
        st.write(f"### 🔍 Reservations Summary for **{inspected_date_str}**")

        details_df = month_data[
            (month_data['Date'].astype(str) == inspected_date_str) |
            (month_data['datetime_obj'].dt.day == active_day)
        ]

        if not details_df.empty:
            st.success(f"Found {len(details_df)} booking(s) for this date:")
            display_cols = [c for c in ['Name', 'Department', 'Facilities', 'Time_Slot', 'Date'] if c in details_df.columns]
            st.dataframe(details_df[display_cols], hide_index=True, use_container_width=True)
        else:
            st.info(f"No bookings registered for {inspected_date_str}.")
    else:
        st.info("No bookings currently recorded in the database.")

# ------------------------------------------
# TAB 3: ADMIN PORTAL
# ------------------------------------------
with tab_admin:
    st.subheader("Administrator Management Portal")
    admin_input = st.text_input("Enter Admin Security Password", type="password")

    if admin_input:
        if admin_input == st.secrets.get("admin_password", ""):
            st.success("🔓 Authenticated as Administrator")
            df_admin = load_booking_data()

            if not df_admin.empty:
                st.markdown("### Manage / Delete Bookings")
                st.dataframe(df_admin, use_container_width=True)

                row_to_delete = st.number_input("Select Row Index to Delete", min_value=0, max_value=len(df_admin)-1, step=1)
                if st.button("Delete Selected Booking", type="primary"):
                    updated_admin_df = df_admin.drop(index=row_to_delete).reset_index(drop=True)
                    conn.update(data=updated_admin_df)
                    st.success(f"🗑️ Row {row_to_delete} removed successfully!")
                    st.rerun()
            else:
                st.info("No records to manage.")
        else:
            st.error("🔒 Invalid Password.")
