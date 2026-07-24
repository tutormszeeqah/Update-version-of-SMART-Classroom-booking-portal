import streamlit as st
from PIL import Image
from streamlit_gsheets import GSheetsConnection
import pandas as pd
from datetime import datetime
import time
import calendar
import urllib.parse
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart

# Page Configuration
st.set_page_config(page_title="PTES Smart Classroom Booking", layout="wide")

# Load the PTES Logo
try:
    logo = Image.open('ptes_logo.png')
    st.sidebar.image(logo, use_container_width=True)
except Exception:
    st.sidebar.warning("Logo image 'ptes_logo.png' not found.")

st.title("PUSAT TINGKATAN ENAM SENGKURONG")
st.markdown("## 💻 Smart Classroom Booking Platform")

# 1. Database Connection
conn = st.connection("gsheets", type=GSheetsConnection)

# Admin Phone Configuration for Notifications
ADMIN_WA_NUMBER = "6737318186"

# Helper Function: Automated Email Notification to Admin
def send_admin_email(booking_details):
    """Sends an automated HTML email notification to the Admin upon new booking."""
    try:
        sender_email = st.secrets["SENDER_EMAIL"]
        sender_password = st.secrets["SENDER_PASSWORD"]
        receiver_email = st.secrets["ADMIN_RECEIVER_EMAIL"]

        subject = f"🔔 Smart Classroom Booking: {booking_details['Name']} ({booking_details['Date']})"
        
        body = f"""
        <html>
            <body>
                <h2>📌 New Smart Classroom Reservation</h2>
                <p>A new lesson/session has been registered for the Smart Classroom:</p>
                <ul>
                    <li><b>Teacher Name:</b> {booking_details['Name']}</li>
                    <li><b>Department/Organisation:</b> {booking_details['Department']}</li>
                    <li><b>Facility:</b> Smart Classroom</li>
                    <li><b>Required Devices / Equipment:</b> {booking_details['Equipment']}</li>
                    <li><b>Date:</b> {booking_details['Date']}</li>
                    <li><b>Time Slot:</b> {booking_details['Time_Slot']}</li>
                    <li><b>Lesson Title / Purpose:</b> {booking_details['Event']}</li>
                    <li><b>WhatsApp Contact:</b> {booking_details['WhatsApp']}</li>
                </ul>
                <hr>
                <p><i>This is an automated notification from the PTES Smart Classroom Booking Portal.</i></p>
            </body>
        </html>
        """

        msg = MIMEMultipart()
        msg["From"] = sender_email
        msg["To"] = receiver_email
        msg["Subject"] = subject
        msg.attach(MIMEText(body, "html"))

        # Send via Gmail SMTP Server
        server = smtplib.SMTP("smtp.gmail.com", 587)
        server.starttls()
        server.login(sender_email, sender_password)
        server.send_message(msg)
        server.quit()
        return True

    except Exception as e:
        st.warning(f"Booking saved, but background email alert failed: {e}")
        return False

# 2. Sidebar - Admin & Instructions
with st.sidebar:
    st.header("Admin Access")
    admin_password = st.text_input("Enter Password to Delete", type="password")

    st.divider()
    st.info("""
    **📜 Smart Classroom Usage Rules:**
    1. Check the monthly calendar before submitting a request.
    2. Ensure all technology devices (Smartboard, Tablets) are handled with care.
    3. For multi-day workshops, submit a separate booking for each day.
    4. Confirmed reservations can only be removed by the Admin.
    """)

# 3. Define Smart Classroom Equipment Options
equipment_list = [
    "Interactive Smartboard Only",
    "Smartboard + Student Tablets / Chromebooks",
    "Smartboard + Wireless Audio System",
    "Complete Smart Classroom Setup (Smartboard, Tablets & Audio)",
    "Presentation Only (Projector/Display)"
]

# Time Slots Mapping
time_slots = {
    "(08:00-09:30) Assembly": "Assembly",
    "(10:00-12:00) Morning": "Morning",
    "(13:30-15:30) Afternoon": "Afternoon",
    "(08:00-12:00) Whole Day": "Whole Day"
}

# 4. Tabs for Navigation
tab1, tab2 = st.tabs(["📝 Reserve Smart Classroom", "📅 View Schedule"])

# ==========================================
# TAB 1: MAKE A BOOKING
# ==========================================
with tab1:
    st.warning("⚠️ **Reminder:** For multi-day workshops or sessions, please book each day individually.")

    with st.form("booking_form"):
        col1, col2 = st.columns(2)

        with col1:
            name = st.text_input("Teacher / Lecturer Name")
            dept = st.selectbox("Organisation / Department", ["STEAM", "PIBG", "SportHouse", "Mathematics", "ICT Related", "Religious", "Administration", "Sciences", "Assembly", "Others"])
            wa_num = st.text_input("Active WhatsApp Number (e.g. +673...)")
            notify_option = st.selectbox("Notify Admin via", ["Email Notification", "WhatsApp Link", "No Notification"])

        with col2:
            event_name = st.text_input("Lesson Title / Purpose")
            equipment_choice = st.selectbox("Devices / Equipment Needed", equipment_list)
            booking_date = st.date_input("Date of Booking", min_value=datetime.today(), format="DD/MM/YYYY")
            slot_choice = st.selectbox("Time Duration", list(time_slots.keys()))

        submit = st.form_submit_button("Confirm Smart Classroom Booking")

    if submit:
        if name and event_name and wa_num:
            # Read current data from Google Sheets
            existing_data = conn.read(ttl=0)

            formatted_date = booking_date.strftime("%d/%m/%Y")
            clean_slot_db_value = time_slots[slot_choice]

            # Clash Check Logic for the Smart Classroom
            same_day_classroom = existing_data[
                (existing_data['Date'].astype(str) == formatted_date) &
                (existing_data['Room'] == "Smart Classroom")
            ]

            clash = same_day_classroom[
                (same_day_classroom['Time_Slot'] == clean_slot_db_value) |
                (same_day_classroom['Time_Slot'] == "Whole Day") |
                (clean_slot_db_value == "Whole Day")
            ]

            if not clash.empty:
                st.error(f"❌ CLASH DETECTED: The Smart Classroom is already reserved on {formatted_date} for this time slot.")
            else:
                # Appends "Smart Classroom" in Room column and logs required devices into Event description
                event_with_equipment = f"{event_name} [Equipment: {equipment_choice}]"
                
                new_entry = pd.DataFrame([{
                    "Name": name,
                    "Department": dept,
                    "WhatsApp": wa_num,
                    "Event": event_with_equipment,
                    "Room": "Smart Classroom",
                    "Date": formatted_date, 
                    "Time_Slot": clean_slot_db_value
                }])

                # Append to Google Sheet
                updated_df = pd.concat([existing_data, new_entry], ignore_index=True)
                conn.update(data=updated_df)
                
                details_payload = {
                    "Name": name,
                    "Department": dept,
                    "WhatsApp": wa_num,
                    "Event": event_name,
                    "Equipment": equipment_choice,
                    "Room": "Smart Classroom",
                    "Date": formatted_date,
                    "Time_Slot": clean_slot_db_value
                }

                st.balloons()
                st.success(f"✅ Success! Smart Classroom reserved for '{event_name}' on {formatted_date}.")

                # DYNAMIC NOTIFICATION DISPATCH
                if notify_option == "Email Notification":
                    with st.spinner("Notifying Admin via automated email..."):
                        email_sent = send_admin_email(details_payload)
                    if email_sent:
                        st.info("✉️ Admin notified via automated email.")
                    time.sleep(3)
                    st.rerun()

                elif notify_option == "WhatsApp Link":
                    message_body = (
                        f"📌 *SMART CLASSROOM BOOKING NOTIFICATION*\n\n"
                        f"👤 *Teacher:* {name}\n"
                        f"🏢 *Department:* {dept}\n"
                        f"💻 *Facility:* Smart Classroom\n"
                        f"⚙️ *Equipment:* {equipment_choice}\n"
                        f"📅 *Date:* {formatted_date}\n"
                        f"⏰ *Time Slot:* {clean_slot_db_value}\n"
                        f"📝 *Lesson/Purpose:* {event_name}\n"
                        f"📞 *Contact:* {wa_num}"
                    )
                    encoded_msg = urllib.parse.quote(message_body)
                    wa_url = f"https://wa.me/{ADMIN_WA_NUMBER}?text={encoded_msg}"
                    
                    st.markdown(f'👉 [**Click Here to Send WhatsApp Notification to Admin**]({wa_url})')
                    time.sleep(5)
                    st.rerun()

                else:  # No Notification
                    time.sleep(3)
                    st.rerun()
        else:
            st.error("Please fill in all required fields.")

# ==========================================
# TAB 2: INTERACTIVE CALENDAR SCHEDULE VIEW
# ==========================================
with tab2:
    st.subheader("📅 Smart Classroom Monthly Schedule")
    
    master_data = conn.read(ttl=0)

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
        display_df['datetime_obj'] = pd.to_datetime(display_df['Date'], format='%d/%m/%Y', errors='coerce')

        # Filter dataset for Smart Classroom bookings in selected month & year
        month_data = display_df[
            (display_df['datetime_obj'].dt.month == selected_month) &
            (display_df['datetime_obj'].dt.year == selected_year) &
            (display_df['Room'] == "Smart Classroom")
        ]

        # Generate Calendar Matrix (Monday start)
        cal = calendar.Calendar(firstweekday=0)
        month_days = cal.monthdayscalendar(selected_year, selected_month)

        # Header
        days_header = ["Mon", "Tue", "Wed", "Thu", "Fri", "Sat", "Sun"]
        cols = st.columns(7)
        for i, h in enumerate(days_header):
            cols[i].markdown(f"### {h}")

        st.divider()

        # Render Grid Cells
        for week in month_days:
            grid_cols = st.columns(7)
            for i, day in enumerate(week):
                with grid_cols[i]:
                    if day != 0:
                        day_str = f"{day:02d}/{selected_month:02d}/{selected_year}"
                        day_bookings = month_data[month_data['Date'] == day_str]
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

        inspected_date_str = f"{active_day:02d}/{selected_month:02d}/{selected_year}"
        st.write(f"### 🔍 Smart Classroom Reservations for **{inspected_date_str}**")

        details_df = month_data[month_data['Date'] == inspected_date_str]

        if not details_df.empty:
            st.success(f"Found {len(details_df)} reservation(s) for this date:")
            clean_details = details_df[['Name', 'Department', 'Time_Slot', 'Event', 'WhatsApp']]
            st.dataframe(clean_details, hide_index=True, use_container_width=True)
        else:
            st.info(f"Smart Classroom is available on {inspected_date_str}.")

        # Protected Admin Cancellation Section
        try:
            target_password = st.secrets["admin_password"]
        except KeyError:
            target_password = None

        if target_password and admin_password == target_password:  
            st.divider()
            st.write("### 🔑 Admin: Cancel a Smart Classroom Booking")
            
            sc_data = master_data[master_data['Room'] == "Smart Classroom"]
            booking_options = []
            for master_idx, row in sc_data.iterrows():
                desc = f"{row['Name']} — {row['Date']} ({row['Time_Slot']}) — {row['Event']}"
                booking_options.append((desc, master_idx))
            
            if booking_options:
                option_labels = [opt[0] for opt in booking_options]
                selected_label = st.selectbox("Select a Reservation to Cancel", options=option_labels)
                selected_master_index = [opt[1] for opt in booking_options if opt[0] == selected_label][0]
                
                if st.button("Delete Selected Booking", type="primary"):
                    updated_master_df = master_data.drop(selected_master_index)
                    conn.update(data=updated_master_df)
                    st.success("Smart Classroom booking deleted successfully.")
                    st.rerun()
            else:
                st.info("No active Smart Classroom bookings available to cancel.")
    else:
        st.info("No bookings found in database.")

# Footer
st.markdown("---")
st.markdown(
    """
    <div style="text-align: center; width: 100%;">
        <p style="font-size: 18px; font-weight: bold;">✨ PTES Smart Classroom Reservation Portal ✨</p>
    </div>
    """,
    unsafe_allow_html=True
)
