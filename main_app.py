import json
import re
from collections import defaultdict
from datetime import datetime
from functools import wraps
import bcrypt
import gspread
from flask import Flask, render_template, request, jsonify, redirect, url_for, flash, session
from oauth2client.service_account import ServiceAccountCredentials


app = Flask(__name__)
app.secret_key = 'your_secret_key_here'


MONTHS_EN_TO_RO = {
    "January": "Ianuarie",
    "February": "Februarie",
    "March": "Martie",
    "April": "Aprilie",
    "May": "Mai",
    "June": "Iunie",
    "July": "Iulie",
    "August": "August",
    "September": "Septembrie",
    "October": "Octombrie",
    "November": "Noiembrie",
    "December": "Decembrie",
}


def get_current_month_name():
    month_en = datetime.now().strftime('%B')
    return MONTHS_EN_TO_RO[month_en]


# Setup Google Sheets authentication
scope = ["https://spreadsheets.google.com/feeds", "https://www.googleapis.com/auth/spreadsheets",
         "https://www.googleapis.com/auth/drive.file", "https://www.googleapis.com/auth/drive"]
creds = ServiceAccountCredentials.from_json_keyfile_name("secret.json", scope)
client = gspread.authorize(creds)

# Open the Google Sheet using its ID
sheet_id = "sheet_id"
PAUZE_SHEET_ID = "PAUZE_SHEET_ID"
sheet_name = f"{get_current_month_name()} {datetime.now().year}".upper()
sheet = client.open_by_key(sheet_id).worksheet(sheet_name)


def get_current_month():
    print(get_current_month_name())


get_current_month()


def login_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if not session.get('logged_in'):
            flash('Please login first.', 'danger')
            return redirect(url_for('admin_login'))
        return f(*args, **kwargs)
    return decorated_function


def check_credentials(username, password):
    with open('credentials.json', 'r') as f:
        data = json.load(f)
        stored_username = data.get("username")
        stored_password_hash = data.get("password").encode('utf-8')
        if stored_username == username:
            return bcrypt.checkpw(password.encode('utf-8'), stored_password_hash)
        return False


@app.route('/admin_login', methods=['GET', 'POST'])
def admin_login():
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']

        # Use the hashed credentials check here
        if check_credentials(username, password):
            session['logged_in'] = True
            return redirect(url_for('admin_dashboard'))
        else:
            flash('Datele de logare sunt incorecte, va rugam incercati iar.', 'danger')

    return render_template('admin_login.html')


@app.route('/admin_dashboard', methods=['GET', 'POST'])
@login_required
def admin_dashboard():
    print("Received request to admin_dashboard")

    # Existing code to open the spreadsheet
    spreadsheet = client.open_by_key(sheet_id)

    # Get all worksheets
    worksheets = spreadsheet.worksheets()

    # Extract titles of each worksheet
    sheet_names = [ws.title for ws in worksheets]
    print(f"Sheet names: {sheet_names}")  # Debugging print statement

    # Get the data for the selected month or default to the current month
    default_month = f"{get_current_month_name()} {datetime.now().year}".upper()
    print(f"Default month: {default_month}")  # Debugging print statement

    selected_month = request.form.get('month', default_month)
    print(f"Selected month: {selected_month}")  # Debugging print statement

    worksheet = client.open_by_key(sheet_id).worksheet(selected_month)

    all_values = worksheet.get_all_values()
    all_values = [row for row in all_values if row[0] != "NUME"]  # Filter out "NUME"

    # Grouping data by user to count active days
    user_data = defaultdict(set)
    for row in all_values:
        user_data[row[0]].add(row[1])  # Using a set to count unique dates

    records = []
    for user, dates in user_data.items():
        records.append({
            'name': user,
            'checkin_time': '',
            'checkout_time': '',
            'date': selected_month,
            'activity': len(dates)
        })

    print(f"Records for admin_dashboard: {records}")  # Debugging print statement

    return render_template('admin_dashboard.html', records=records, sheet_names=sheet_names,
                           selected_month=selected_month)


@app.route('/logout')
def logout():
    session.pop('logged_in', None)
    flash('You were logged out.', 'info')
    return redirect(url_for('admin_login'))


@app.route('/null')
def null():
    print("Received request to null")
    return render_template('null.html')


@app.route('/')
def home():
    print("Received request to home")
    return render_template('index.html')


@app.route('/contact')
def contact():
    print("Received request to contact")
    return render_template('contact.html')


@app.route('/pontaj')
def pontaj():
    print("Received request to pontaj")
    # Fetch the list of employee names from Google Sheet for the dropdown
    employee_names = sheet.col_values(1)[1:]  # Assuming the names start from the second row in the first column
    return render_template('pontaj.html', employees=employee_names)


@app.route('/pauze')
def pauze():
    print("Received request to pauze")

    # Open the sheet for breaks using its ID
    break_sheet = client.open_by_key(PAUZE_SHEET_ID).get_worksheet(0)  # Assuming you want the first worksheet
    # Fetch employee names
    employee_names = break_sheet.col_values(1)[1:]  # Assuming the names start from the second row in the first column

    print(f"Fetching names from /pauze: {employee_names}")  # Debugging statement

    return render_template('pauze.html', employees=employee_names)


@app.route('/info')
def info():
    print("Received request to info")
    return render_template('info.html')


current_day = datetime.now().strftime('%d/%m/%Y')


def get_worksheet():
    # Authenticate with Google using the provided credentials
    gc = gspread.service_account(filename='secret.json')

    # Open the correct Google Sheet using the provided ID
    sh = gc.open_by_key('KEY')

    # Get the worksheet based on the selected month or default to the current month
    selected_month = request.form.get('month', f"{get_current_month_name()} {datetime.now().year}".upper())
    worksheet = sh.worksheet(selected_month)

    return worksheet


@app.route('/record_break', methods=['POST'])
def record_break():
    # Calculate the current day in the desired format (e.g., '23/10/2023')
    current_day = datetime.now().strftime('%d/%m/%Y')

    # Directly access the breaks worksheet based on the current day
    breaks_worksheet = client.open_by_key(PAUZE_SHEET_ID).worksheet(current_day)

    employee = request.form['employee'].strip()
    start_break = request.form['start_break'].strip()
    end_break = request.form['end_break'].strip()

    print(f"Received request to record break for employee: {employee}")
    print(f"Start break time: {start_break}")
    print(f"End break time: {end_break}")

    print(f"Trying to find employee: {employee}")  # Debugging statement

    # Fetch employee names from the breaks worksheet
    employee_names = breaks_worksheet.col_values(1)[1:]

    print("Fetching employee names from the breaks worksheet:")
    print(employee_names)

    # Define intervals
    intervals = [
        ("09:30 - 10:30", None, None),  # User should not set a break in this interval
        ("10:30 - 11:30", 2, 3),
        ("11:30 - 12:30", 5, 6),
        ("12:30 - 13:30", 8, 9),
        ("13:30 - 14:30", 11, 12),
        ("14:30 - 15:30", 14, 15),
        ("15:30 - 16:30", 17, 18),
        ("16:30 - 17:30", 20, 21),
        ("17:30 - 18:30", 23, 24)
    ]

    # Validation: Check if start_break or end_break is outside of intervals
    current_time = datetime.now().strftime('%H:%M')
    if current_time < "09:30" or current_time > "18:30":
        print("Break time is outside the allowed interval.")
        return jsonify(status="error", message="Nu poti incepe sau termina pauza in afara intervalului permis!")

    # Determine the current interval based on the current time
    current_interval = None
    for interval_data, start_col, end_col in intervals:
        if interval_data.split(" - ")[0] <= current_time <= interval_data.split(" - ")[1]:
            current_interval = interval_data
            break

    print(f"Current interval: {current_interval}")

    # Validation: Check if the user is trying to start/end a break outside the current interval
    if start_break and not (current_interval.split(" - ")[0] <= start_break <= current_interval.split(" - ")[1]):
        print("User is trying to start a break outside the current interval.")
        return jsonify(status="error", message=f"Nu poti incepe pauza in afara intervalului curent "
                                               f"({current_interval}).")
    if end_break and not (current_interval.split(" - ")[0] <= end_break <= current_interval.split(" - ")[1]):
        print("User is trying to end a break outside the current interval.")
        return jsonify(status="error", message=f"Nu poti termina pauza in afara intervalului curent "
                                               f"({current_interval}).")

    # Find the interval column based on start_break or end_break
    col = None
    interval = None  # Initialize interval as None
    for interval_data, start_col, end_col in intervals:
        if start_break:
            col = start_col
        elif end_break:
            col = end_col
        if interval_data.split(" - ")[0] <= current_time <= interval_data.split(" - ")[1]:
            interval = interval_data  # Assign the interval
            break

    if not interval:  # Check if the interval was not assigned
        print("Interval not found.")
        return jsonify(status="error", message="Intervalul nu a fost gasit.")

    print(f"Interval column: {col}")

    # Try to directly find the employee's row in the breaks worksheet
    row = None
    employee_names_list = []  # List to store employee names for debugging
    for r in range(2, breaks_worksheet.row_count + 1):  # Starting from 2 to skip the header
        emp_name = breaks_worksheet.cell(r, 1).value
        employee_names_list.append(emp_name)  # Add the name to the list
        if emp_name == employee:
            row = r
            break

    print("Fetching names from record_break:", employee_names_list)  # Debugging statement

    # If the row is still None, the employee wasn't found
    if row is None:
        print(f"Employee {employee} not found in the worksheet!")  # Debugging statement
        return jsonify(status="error", message="Employee not found.")

    # Check if a break has already started or ended for this interval
    existing_start_break = breaks_worksheet.cell(row, col).value if start_break else None
    existing_end_break = breaks_worksheet.cell(row, col).value if end_break else None
    if start_break and existing_start_break:
        print(f"Break already started at {existing_start_break} in the interval {interval}.")
        return jsonify(status="error",
                       message=f"Pauza ta in intervalul {interval} a fost inceputa deja la {existing_start_break}.")
    if end_break and existing_end_break:
        print(f"Break already ended at {existing_end_break} in the interval {interval}.")
        return jsonify(status="error",
                       message=f"Pauza ta in intervalul {interval} a fost finalizata deja la {existing_end_break}.")

    # Block ending a break before starting it
    if end_break and not breaks_worksheet.cell(row, col - 1).value:
        print("User is trying to end a break before starting it.")
        return jsonify(status="error", message="Nu poti termina pauza inainte de a o incepe!")

    # Update the breaks worksheet with the start_break or end_break times
    if start_break:
        breaks_worksheet.update_cell(row, col, start_break)
        print(f"Break started successfully at {start_break} in the interval {interval}.")
        return jsonify(status="success",
                       message=f"Pauza ta in intervalul {interval} a fost inceputa la {start_break}.")

    if end_break:
        breaks_worksheet.update_cell(row, col, end_break)
        total_break_time = breaks_worksheet.cell(row, col + 1).value  # Fetching the total break time for the interval
        print(f"Break ended successfully at {end_break} in the interval {interval}. "
              f"Total break time: {total_break_time}.")
        return jsonify(status="success",
                       message=f"Pauza ta in intervalul {interval} a fost finalizata la {end_break}. "
                               f"Durata pauzei a fost de {total_break_time}.")


@app.route('/record_time', methods=['POST'])
def record_time():
    employee = request.form['employee'].strip()
    checkin_time = request.form['checkin_time'].strip()
    checkout_time = request.form['checkout_time'].strip()

    print(f"Received request to record time for employee: {employee}")
    print(f"Check-in time: {checkin_time}")
    print(f"Check-out time: {checkout_time}")

    time_pattern = re.compile(r'^(?:2[0-3]|[01]?[0-9]):[0-5][0-9]$')

    if checkin_time and not time_pattern.match(checkin_time):
        print("Check-in time format is incorrect.")
        return jsonify(status="error",
                       message="<b>Ora de intrare nu este în formatul corect!</b>"
                               "<br>In cazul in care crezi ca aceasta este o eroare,<br>te rugam sa "
                               "contactezi administratorul platformei pentru a remedia "
                               "problema cat mai rapid!</br>"
                               "<b>Va multumim!</b>")

    if checkout_time and not time_pattern.match(checkout_time):
        print("Check-out time format is incorrect.")
        return jsonify(status="error",
                       message="<b>Ora de iesire nu este în formatul corect!</b>"
                               "<br>In cazul in care crezi ca aceasta este o eroare,<br>te rugam sa "
                               "contactezi administratorul platformei pentru a remedia "
                               "problema cat mai rapid!</br>"
                               "<b>Va multumim!</b>")

    # Block attempts if the user chooses the default "NAME" option
    if employee == "NUME":
        print("User selected the default 'NUME' option.")
        return jsonify(status="error", message="<b>Te rugam sa alegi numele tau inainte de a te ponta!</b>"
                                               "<br>In cazul in care crezi ca aceasta este o eroare,<br>te rugam sa "
                                               "contactezi administratorul platformei pentru a remedia "
                                               "problema cat mai rapid!</br>"
                                               "<b>Va multumim!</b>")

    # Find the employee's row
    row = sheet.findall(employee)[0].row

    print(f"Found employee's row: {row}")

    # Try to find the column for today's date
    try:
        today_date = datetime.now().strftime('%d/%m/%Y')
        col = sheet.findall(today_date)[0].col
    except IndexError:
        print("Today's date not found in the sheet.")
        return jsonify(status="error", message="<b>Ne pare rau, ziua de astazi nu a putut fi gasita!</b>"
                                               "<br>In cazul in care crezi ca aceasta este o eroare,<br>te rugam sa "
                                               "contactezi administratorul platformei<br>pentru a remedia "
                                               "problema cat mai rapid!<br>"
                                               "<b>Va multumim!</b>")

    print(f"Found today's column for date: {today_date}, column: {col}")

    status_messages = {
        "CO": "<b>Esti in concediu de odihna astazi. Nu te poti ponta!</b>",
        "CFP": "<b>Esti in concediu fara plata astazi. Nu te poti ponta!</b>",
        "CM": "<b>Esti in concediu medical astazi. Nu te poti ponta!</b>"
    }

    if checkin_time and sheet.cell(row, col).value in status_messages.keys():
        print(f"User is in a special status: {sheet.cell(row, col).value}")
        return jsonify(status="error", message=status_messages[sheet.cell(row, col).value] +
                              "<br>In cazul in care crezi ca aceasta este o eroare,<br>te rugam sa "
                              "contactezi administratorul platformei sau "
                              "seful tau de echipa pentru a remedia problema cat mai rapid!</br>"
                              "<b>Va multumim!</b>")

    if checkout_time and sheet.cell(row, col + 1).value in status_messages.keys():
        print(f"User is in a special status for checkout: {sheet.cell(row, col + 1).value}")
        return jsonify(status="error", message=status_messages[sheet.cell(row, col + 1).value] +
                       "<br>In cazul in care crezi ca aceasta este o eroare,<br>te rugam sa "
                       "contactezi administratorul platformei sau "
                       "seful tau de echipa pentru a remedia problema cat mai rapid!</br>"
                       "<b>Va multumim!</b>")

    # Check if check-in time is already present for today
    existing_checkin_time = sheet.cell(row, col).value
    if checkin_time and existing_checkin_time:
        print(f"User has already checked in at {existing_checkin_time}.")
        return jsonify(status="error", message=f"<b>Startul turei tale a fost pontat deja la ora de "
                                               f"{existing_checkin_time}!</b>"
                                               "<br>In cazul in care crezi ca aceasta este o eroare,<br>te rugam sa "
                                               "contactezi administratorul platformei<br>pentru a remedia "
                                               "problema cat mai rapid!<br>"
                                               "<b>Va multumim!</b>")

    # Block checkout if the user hasn't checked in
    if checkout_time and not existing_checkin_time:
        print("User can't set checkout time without checking in first.")
        return jsonify(status="error", message="<b>Nu poti seta ora de iesire inainte da a seta ora de intrare!</b>"
                                               "<br>In cazul in care crezi ca aceasta este o eroare,<br>te rugam sa "
                                               "contactezi administratorul platformei<br>pentru a remedia "
                                               "problema cat mai rapid!<br>"
                                               "<b>Va multumim!</b>")

    # Check if both checkin and checkout times are empty
    if not checkin_time and not checkout_time:
        print("User didn't provide check-in or check-out time.")
        return jsonify(status="error", message="<b>Te rugam sa introduci ora de intrare sau ora de iesire!</b>"
                                               "<br>In cazul in care crezi ca aceasta este o eroare,<br>te rugam sa "
                                               "contactezi administratorul platformei<br>pentru a remedia "
                                               "problema cat mai rapid!<br>"
                                               "<b>Va multumim!</b>")

    # Update the sheet with the check-in and checkout times
    if checkin_time:
        current_time = datetime.now().strftime('%H:%M')
        entry = f"{checkin_time} / {current_time}"
        sheet.update_cell(row, col, entry)
        print(f"Check-in time recorded successfully: {entry}")
        return jsonify(status="success", message="Pontarea pentru inceputul turei tale<br>"
                                                 "a fost inregistrata cu succes!<br>"
                                                 "<b>Spor la munca!</b>")

    if checkout_time:
        current_time = datetime.now().strftime('%H:%M')
        entry = f"{checkout_time} / {current_time}"
        sheet.update_cell(row, col + 1, entry)
        print(f"Check-out time recorded successfully: {entry}")
        return jsonify(status="success", message="Pontarea pentru sfarsitul turei tale<br>"
                                                 "a fost inregistrata cu succes!<br>"
                                                 "<b>O zi buna in continuare!</b>")


if __name__ == '__main__':
    app.run(debug=True)
