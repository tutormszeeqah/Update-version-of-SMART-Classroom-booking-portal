import streamlit as st
import pandas as pd
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from datetime import datetime, date
import calendar
from PIL import Image
from streamlit_gsheets import GSheetsConnection

# ==========================================
# 1. PAGE CONFIGURATION & INITIALIZATION
# ==========================================
st.set_page_config(
    page_title="PTES Smart Classroom Booking",
    page_icon="💻",
    layout="wide"
)

# Initialize Google Sheets Connection
conn = st.connection("gsheets", type=GSheetsConnection)

# Facilities List
FACILITIES = [
    "Smart Classroom 1",
    "Smart Classroom 2",
    "Multimedia Lab",
    "Conference Room"
]

# Available Time Slots
TIME_SLOTS = [
    "07:30 - 08:30",
    "08:30 - 09:30",
    "10:00 - 11:00",
    "11:00 - 12:00",
    "12:30 - 01:30"
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
                <li><b>Facilities:</b> {booking_details['Facilities']}</li>
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
st.markdown("Pusat Tingkatan Enam Sengkurong")

tab_book, tab_calendar, tab_admin = st.tabs(["📝 New Booking", "📅 Interactive Calendar", "🔒 Admin Portal"])

# ------------------------------------------
# TAB 1: NEW BOOKING FORM & PREVIEW
# ------------------------------------------
with tab_book:
    st.subheader("Reserve a Smart Classroom Facility")
    
    with st.form("booking_form", clear_on_submit=False):
        col1, col2 = st.columns(2)
        
        with col1:
            name = st.text_input("Name *")
            department = st.selectbox("Department *", [
                "Computer Science", "Mathematics", "Sciences", 
                "Languages", "Humanities", "Administration"
            ])
            facility = st.selectbox("Facilities *", FACILITIES)

        with col2:
            booking_date = st.date_input("Date *", min_value=date.today())
            time_slot = st.selectbox("Time Slot *", TIME_SLOTS)

        submitted = st.form_submit_button("Submit & Confirm Reservation")

        if submitted:
            if not name:
                st.error("⚠️ Please fill in all required fields marked with *.")
            else:
                date_str = booking_date.strftime("%Y-%m-%d")
                df_existing = load_booking_data()

                # Clash Detection Logic
                clash = False
                if not df_existing.empty and {"Date", "Time_Slot", "Facilities"}.issubset(df_existing.columns):
                    matches = df_existing[
                        (df_existing["Date"].astype(str) == date_str) &
                        (df_existing["Time_Slot"] == time_slot) &
                        (df_existing["Facilities"] == facility)
                    ]
                    if not matches.empty:
                        clash = True

                if clash:
                    st.error(f"❌ **Booking Conflict:** {facility} is already booked for **{time_slot}** on **{date_str}**. Please select another slot or room.")
                else:
                    # New booking entry matching exact Google Sheet headers
                    new_entry = pd.DataFrame([{
                        "Name": name,
                        "Department": department,
                        "Date": date_str,
                        "Time_Slot": time_slot,
                        "Facilities": facility
                    }])

                    # Append to Google Sheet
                    updated_df = pd.concat([df_existing, new_entry], ignore_index=True)
                    conn.update(data=updated_df)
                    
                    st.success("🎉 Booking successfully recorded!")
                    
                    # ------------------------------------------
                    # BOOKED SMARTLAB PREVIEW CARD FORMAT
                    # ------------------------------------------
                    st.markdown("---")
                    st.markdown("### 📋 Booked SmartLab Reservation Summary")
                    
                    preview_container = st.container(border=True)
                    with preview_container:
                        p_col1, p_col2 = st.columns(2)
                        with p_col1:
                            st.markdown(f"👤 **Name:** `{name}`")
                            st.markdown(f"🏢 **Department:** `{department}`")
                            st.markdown(f"🏫 **Facility / Room:** `{facility}`")
                        with p_col2:
                            st.markdown(f"📅 **Date:** `{date_str}`")
                            st.markdown(f"⏰ **Time Slot:** `{time_slot}`")
                            st.markdown("STATUS: `CONFIRMED`")

                    # Dispatch Email Notification
                    send_notification_email(new_entry.iloc[0].to_dict())

# ------------------------------------------
# TAB 2: INTERACTIVE CALENDAR SCHEDULE VIEW
# ------------------------------------------
with tab_calendar:
    st.subheader("📅 Monthly Interactive Schedule Calendar")
    
    master_data = load_booking_data()

    # Date / Month Selection Controls
    col_m, col_y = st.columns(2)
    with col_m:
        month_names = list(calendar.month_name)[1:]
        selected_month_str = st.selectbox("Select Month", month_names, index=datetime.today().month - 1)
        selected_month = month_names.index(selected_month_str) + 1
    with col_y:
        selected_year = st.number_input("Select Year", min_value=2024, max_value=2030, value=datetime.today().year)

    # Initialize Active Selected Day in Session State
    if 'selected_calendar_day' not in st.session_state:
        st.session_state.selected_calendar_day = datetime.today().day

    if not master_data.empty:
        display_df = master_data.copy()
        display_df['datetime_obj'] = pd.to_datetime(display_df['Date'], errors='coerce')

        # Filter dataset for selected month & year
        month_data = display_df[
            (display_df['datetime_obj'].dt.month == selected_month) &
            (display_df['datetime_obj'].dt.year == selected_year)
        ]

        # Generate Calendar Matrix (Monday start)
        cal = calendar.Calendar(firstweekday=0)
        month_days = cal.monthdayscalendar(selected_year, selected_month)

        # Header Columns
        days_header = ["Mon", "Tue", "Wed", "Thu", "Fri", "Sat", "Sun"]
        cols = st.columns(7)
        for idx, header in enumerate(days_header):
            cols[idx].markdown(f"### {header}")

        st.divider()

        # Render Grid Cells
        for week in month_days:
            grid_cols = st.columns(7)
            for i, day in enumerate(week):
                with grid_cols[i]:
                    if day != 0:
                        day_str = f"{selected_year}-{selected_month:02d}-{day:02d}"
                        day_bookings = month_data[month_data['Date'].astype(str) == day_str]
                        booking_count = len(day_bookings)

                        if booking_count > 0:
                            label = f"🔴 {day:02d} ({booking_count})"
                        else:
                            label = f"⚪ {day:02d}"

                        if st.button(label, key=f"btn_day_{day}_{selected_month}_{selected_year}", use_container_width=True):
                            st.session_state.selected_calendar_day = day

        st.divider()

        # Detailed Day Inspection Table
        active_day = st.session_state.selected_calendar_day
        max_days = calendar.monthrange(selected_year, selected_month)[1]
        if active_day > max_days:
            active_day = max_days

        inspected_date_str = f"{selected_year}-{selected_month:02d}-{active_day:02d}"
        st.write(f"### 🔍 Reservations Summary for **{inspected_date_str}**")

        details_df = month_data[month_data['Date'].astype(str) == inspected_date_str]

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
