from flask import Flask, request, render_template, redirect, url_for, flash, session, jsonify, send_file, send_from_directory, abort
from flask_login import LoginManager, login_user, login_required, logout_user, current_user
from livereload import Server
from py_scripts import db_conn, tools
from datetime import date, datetime
import os
import pandas as pd
import openpyxl
from functools import wraps


server = Flask(__name__)
server.jinja_env.auto_reload = True
server.secret_key = os.urandom(24)

login_manager = LoginManager()
login_manager.init_app(server)
login_manager.login_view = 'landing_page'
login_manager.login_message = {
    "title": "Login Required",
    "text": "You must log in to view this page.",
    "redirect_url": "/"
}
# TODO remove all flash template and use another dialog box
# TODO try toastr for the dialogs
login_manager.login_message_category = "warning"

# TODO put @login_required on all template and api routes

# for closing the session after requests
@server.teardown_appcontext
def cleanup(exception=None):
    db_conn.shutdown_session()

# f0r the login 
@login_manager.user_loader
def load_user(user_id):
    db_session = db_conn.SessionLocal()
    return db_session.query(db_conn.models.Accounts).get(int(user_id))

    
def roles_required(*roles):
    '''  Decorator to restrict access to users with a specific role.'''
    def wrapper(fn):
        @wraps(fn)
        def decorated_view(*args, **kwargs):
            if not current_user.is_authenticated:
                return login_manager.unauthorized()
            if current_user.user_level not in roles:
                abort(403)
            return fn(*args, **kwargs)
        return decorated_view
    return wrapper


# ?TODO LIST-------------------------------
# TODO add the summary per month to the module list or wherever


# <------------ NAVIGATIONS ------------>

@server.route('/')
def landing_page():
    return render_template('index.html')


@server.route('/login', methods=['POST'])
def login():
    username = request.form.get("username")
    password = request.form.get("password")

    user = db_conn.sign_in(username, password)

    if user:
        # print('\nCurrent User:\n')
        # print({c.name: getattr(user, c.name) for c in user.__table__.columns})# Debugging line. remove after testing
        if user.acct_status == 'approved':
            login_user(user)
            return redirect(url_for('dashboard'))
        elif user.acct_status == 'pending':
            flash({
                "title": "Login Error!",
                "text": "Account not approved yet. Contact admin.",
                "redirect_url": url_for('landing_page')
            },"error")
            return render_template('index.html')
    else:
        flash({
            "title": "Login Error!",
            "text": "Wrong username or password. Try again.",
            "redirect_url": url_for('landing_page')
        }, "error")
        return render_template('index.html')
    
    '''
    if sign_in == 'success':
        user_details = db_conn.get_user_details_by_username(username)

        if user_details:
            session['username'] = username
            session['full_name'] = f"{user_details['first_name']} {user_details['middle_name']} {user_details['last_name']}"
            session['email'] = user_details['email']
            session['phone'] = user_details['contact_no']
            session['birthdate'] = user_details['birth_date']
            session['password'] = user_details['password']
            session['user_level'] = user_details['user_level']
            
            return redirect(url_for('home'))  # success redirect
        else:
            flash({
                "title": "Login Error!",
                "text": "User details could not be fetched.",
                "redirect_url": url_for('landing_page')
            }, "error")
            return render_template('index.html')
    
    elif sign_in == 'pending':
        flash({
            "title": "Login Error!",
            "text": "Account not approved yet. Contact admin.",
            "redirect_url": url_for('landing_page')
        }, "error")
        return render_template('index.html')
    
    else:
        flash({
            "title": "Login Error!",
            "text": "Wrong username or password. Try again.",
            "redirect_url": url_for('landing_page')
        }, "error")
        return render_template('index.html')
    '''

@server.route('/logout')
@login_required
def logout():
    logout_user()
    session.clear()
    return redirect(url_for("landing_page"))


@server.route('/profile_settings')
@login_required
def profile_settings():
    '''
    if 'username' not in session:
        flash({
            "title": "Not Logged In",
            "text": "Please log in to access your profile.",
            "redirect_url": url_for('landing_page')
        }, "error")
        return redirect(url_for('landing_page'))

    username = session['username']
    user_details = db_conn.get_user_details_by_username(username)
    '''
    
    return render_template('profile_settings.html')


@server.route('/create_account')
def create_acc():
    return render_template('create_account.html')


@server.route('/forgot_password')
def forgot_password():
    return render_template('forgot_password.html')


@server.route('/profile')
@login_required
def profile():
    return render_template('profile.html')


@server.route('/dashboard')
@login_required
def dashboard():
    return render_template('dashboard.html')


@server.route('/members')
@login_required
def members_page():
    return render_template('members.html')
    
    # return render_template('test_row_editor.html')
    # remove this when done testing


@server.route('/declaration')
@login_required
@roles_required('admin', 'superadmin')
def declaration_page():
    return render_template('declaration.html')


@server.route('/inventory')
@login_required
def inventory():
    # Fetch inventory entries from the database
    inventory_data = db_conn.get_inventory_entries()  # Ensure this returns data correctly
    
    # Print or log the data to verify it's being passed correctly
    print(inventory_data)
    
    # Pass data to the template
    return render_template('inventory.html', inventory_data=inventory_data)

@server.route('/claims')
@login_required
def claims():
    return render_template('claims.html')


@server.route('/reports')
@login_required
@roles_required('admin', 'superadmin')
def bud_v_exp():
    return render_template('reports.html')


@server.route('/audit_trails')
@login_required
@roles_required('admin', 'superadmin')
def audit_trails():
    return render_template('audit_trails.html')


@server.route('/accounts')
@login_required
@roles_required('admin', 'superadmin')
def show_user_accounts():
    active_accounts = db_conn.get_user_accounts(status=['approved', 'archived', 'declined'])
    pending_accounts = db_conn.get_user_accounts(status=['pending'])

    return render_template('accounts.html', active_accounts=active_accounts, pending_accounts=pending_accounts)


@server.route('/settings')
@login_required
def settings():
    # Use Flask-Login’s current_user instead of session
    user_details = db_conn.get_user_details_by_username(current_user.username)
    return render_template('settings.html', user_details=user_details)


# <------------ /NAVIGATIONS ------------>


@server.route('/create_acc_submit', methods=['POST'])
def create_acc_submit():
    user = request.form.get('username')
    passw = request.form.get('password')
    email = request.form.get('email')

    fname = request.form.get('fname').upper()
    mname = request.form.get('mname').upper()
    lname = request.form.get('lname').upper()
    suffix = request.form.get('suffix')

    bdate = request.form.get('bdate')
    contact = request.form.get('contact_no')

    acct_created = date.today().strftime("%Y-%m-%d")
    branch = request.form.get('branch')

    if (fname, mname, lname, suffix, bdate, contact, email, user, passw, branch):
        #print(fname, mname, lname, suffix, bdate, contact, email, user, passw, branch) #todo remove afer development
        hashed_pass = tools.hash_password(passw)

        db_conn.create_account(user=user, hashed_pass=hashed_pass, email=email, fname=fname, mname=mname, lname=lname,
                               suffix=suffix, bdate=bdate, contact=contact, acct_created=acct_created, branch=branch)
    else:
        pass

    flash({
        "title": "Account created successfully!",
        "text": "Click continue to go back to login screen.",
        "redirect_url": url_for('landing_page')
    }, "success")
    return render_template('create_account.html')




# ========================== FORGOT PASSWORD ==========================
@server.route("/forgot_password_otp", methods=["GET", "POST"])
def forgot_password_otp():
    if request.method == "POST":
        email = request.form.get("email")

        otp = db_conn.generate_otp()  # Generate OTP
        db_conn.save_otp(email, otp)  # Save OTP in otp_verifications table
        db_conn.send_otp_email(email, otp)  # Send OTP to user's

        session["email"] = email
        flash({
            "title": "OTP Sent!",
            "text": "OTP has been sent to your email.",
            "redirect_url": url_for('verify_otp')
        }, "info")

    return render_template("forgot_password.html")


# ========================== VERIFY OTP ==========================
@server.route('/verify_otp', methods=['GET', 'POST'])
def verify_otp(): 
    if request.method == 'POST':
        email = request.form.get('email')  # Get email from form
        otp_input = request.form.get('otp')  # Get OTP from form

        # Call the database function to verify OTP
        result = db_conn.verifying_otp(email, otp_input)

        if result == "success":
            flash({
                "title": "OTP Verified Successfully!",
                "text": "You can now proceed to reset your password.",
                "redirect_url": url_for('reset_password')
            }, "success")  # Redirect to reset password page

        elif result == "expired":
            flash({
                "title": "OTP Error",
                "text": "OTP has expired. Please try again.",
                "redirect_url": url_for('forgot_password')
            }, "error")

        elif result == "email_not_found":
            flash({
                "title": "Email is not registered",
                "text": " Please check your email or create an account.",
                "redirect_url": url_for('forgot_password')
            }, "error")

        else:
            flash({
                "title": "Invalid OTP",
                "text": "Please try again.",
                "redirect_url": url_for('verify_otp')
            }, "error")

    email = session.get("email")
    return render_template('verify_otp.html', email=email)  # Render OTP verification page


# ========================== RESET PASSWORD ==========================
@server.route("/reset_password", methods=["GET", "POST"])
def reset_password():
    email = session.get("email")
    if not email:
        flash({
            "title": "Session expired",
            "text": "Please try again.",
            "redirect_url": url_for('forgot_password_otp')
        }, "error")

    if request.method == "POST":
        new_password = request.form["new_password"]
        confirm_password = request.form["confirm_password"]

        if new_password != confirm_password:
            flash("Passwords do not match. Please try again.", "error")
        else:
            db_conn.update_password(email, new_password)  
            session.pop("email", None) 
            flash({
                "title": "Password Reset Successfully!",
                "text": "You can now log in with your new password.",
                "redirect_url": url_for('landing_page')
            }, "success")
        
    return render_template("reset_password.html")


# API FOR DASHBOARD
@server.route('/api/get_pending_claims_count')
def get_pending_claims_count():
    count = db_conn.get_pending_claims_count()
    return jsonify({"pending_claims_count": count})


# API FOR MEMBERS PAGE


@server.route('/api/get_records')
def get_members():
    records = db_conn.get_member_records()
    members_list = []

    for row in records:
        record = dict(row._mapping)

        for key in ['id_received', 'declared', 'paid']:
            if key in record:
                record[key] = bool(record[key])

        for key in ['declaration_date', 'effectivity_date']:
            if key in record and record[key]:
                record[key] = record[key].strftime('%Y-%m-%d')

        members_list.append(record)

    return jsonify(members_list)


@server.route('/api/add_record', methods=['POST'])
def add_new_record():
    new_record_id = db_conn.add_new_record()
    return jsonify({"success": True, "record_id": new_record_id})

@server.route('/api/save_record_details', methods=['POST'])
def save_record_details():
    data = request.get_json()
    if data:
        db_conn.save_record_details(data)
        return jsonify({"success": True})


@server.route('/api/get_entries', methods=['POST'])
def get_entries():
    data = request.get_json()
    record_id = data.get('record_id')
    # Use record_id to filter your SQL query
    entries = db_conn.get_entries(record_id)
    return jsonify(entries)


@server.route('/api/get_claim_records')
def get_claim_records():
    records = db_conn.get_claim_records()
    claims_list = []

    for row in records:
        record = dict(row._mapping)

        for key in ['same_as_insured', 'picked_up']:
            if key in record:
                record[key] = bool(record[key])

        for key in ['date_filed', 'date_of_loss', 'date_released', 'date_picked_up', 'effectivity_date']:
            if key in record and record[key]:
                record[key] = record[key].strftime('%Y-%m-%d')

        claims_list.append(record)
    return jsonify(claims_list)


@server.route('/api/add_claim_record', methods=['POST'])
def add_claim_record():
    new_claim_id = db_conn.add_claim_record()
    return jsonify({"success": True, "claim_id": new_claim_id})


@server.route('/api/verify_maab_no', methods=['POST'])
def verify_maab_no():
    data = request.get_json()
    maab_no = data.get('maab_no')
    if not maab_no:
        return jsonify({"exists": False, "error": "No MAAB No. provided"}), 400

    result = db_conn.verify_maab_no(maab_no)
    if result is None:
        return jsonify({"exists": False})
    return jsonify(result)


@server.route('/api/save_claim_record', methods=['POST'])
def save_claim_record():
    data = request.get_json()
    if data:
        db_conn.save_claim_record(data)
        return jsonify({"success": True})


@server.route('/api/delete_claim_record', methods=['DELETE'])
def delete_claim_record():
    data = request.get_json()
    claim_id = data.get('claim_id')
    if not claim_id:
        return jsonify({"success": False, "error": "No claim ID provided"}), 400

    success = db_conn.delete_claim_record(claim_id)
    if success:
        return jsonify({"success": True})
    else:
        return jsonify({"success": False, "error": "Failed to delete claim record"}), 500



@server.route('/account_action', methods=['POST'])
def account_action():
    action = request.form.get('action')
    
    if action == 'create':
        selected_ids = request.form.getlist('active_checkbox')
        print("create:", selected_ids)
        db_conn.account_action(selected_ids, action)
        
        return redirect(url_for('create_acc'))
        # TODO redirect to the create account page but the admin version(auto approve)
        # TODO add batch account creation (tickbox + toast message)
        # TODO set default password format (bdate + initials)
        # TODO fix the back button to go back to accounts instead when clicked from there
    elif action == 'archive':
        selected_ids = request.form.getlist('active_checkbox')
        print("archive:", selected_ids)
        db_conn.account_action(selected_ids, action)
    elif action == 'reset':
        selected_ids = request.form.getlist('active_checkbox')
        print("reset:", selected_ids)
        db_conn.account_action(selected_ids, action)
    elif action == 'approve':
        selected_ids = request.form.getlist('pending_checkbox')
        print("approve:", selected_ids)
        db_conn.account_action(selected_ids, action)
    elif action == 'decline':
        selected_ids = request.form.getlist('pending_checkbox')
        print("decline:", selected_ids)
        db_conn.account_action(selected_ids, action)
    
    return redirect(url_for('show_user_accounts'))


@server.route('/inventory_action', methods=['POST'])
def inventory_action():
    pass


# ! TEST FUNCTIONS GO HERE
@server.route('/api/hot-update', methods=['POST'])
def hot_update_data():
    updates = request.json  # List of row dicts
    conn = db_conn.conn_init()
    cursor = conn.cursor()
    for row in updates:
        cursor.execute(
            "UPDATE people SET name = %s, age = %s WHERE id = %s",
            (row['name'], row['age'], row['id'])
        )
    conn.commit()
    conn.close()
    return jsonify({"status": "success"})


# declaration report
@server.route('/generate_report', methods=['POST'])
def generate_report():
    try:
        # Get the date inputs
        from_date = request.form.get('fromdate')
        to_date = request.form.get('todate')

        # Validate the input dates (optional)
        if not from_date or not to_date:
            flash("Please select both from and to dates.", "error")
            return render_template('declaration.html')

        # Generate the report file name with timestamp
        report_filename = f"report_{datetime.now().strftime('%Y%m%d_%H%M%S')}.xlsx"
        report_folder = os.path.join(os.path.dirname(__file__), "reports")
        report_path = os.path.join(report_folder, report_filename)

        # Ensure the _reports folder exists
        os.makedirs(report_folder, exist_ok=True)
        print(f"Report will be saved to: {report_path}")

        # Your report generation logic here, for example, using pandas
        data = [
            {"Transaction No.": 1001, "Year": 2025, "MAAB No.": "MAAB001", "Member ID": "M1234", "Effectivity Date": "2025-01-10",
            "Expiry Date": "2026-01-10", "Particular Location": "Location A", "Location Category": "Urban", "Municipality": "City A",
            "District": "D1", "OR Number": 123456, "OR Date": "2025-01-15", "Paid": "Yes", "Remarks": "Active Member",
            "Origin": "Branch 1", "Count in Group": 3, "ID Received": "Yes", "Declared": "Yes", "Tags": "Renewal", "Declaration Date": "2025-01-10"},
            {"Transaction No.": 1002, "Year": 2025, "MAAB No.": "MAAB002", "Member ID": "M1235", "Effectivity Date": "2025-02-05",
            "Expiry Date": "2026-02-05", "Particular Location": "Location B", "Location Category": "Rural", "Municipality": "City B",
            "District": "D2", "OR Number": 123457, "OR Date": "2025-02-07", "Paid": "Yes", "Remarks": "Pending Update",
            "Origin": "Branch 2", "Count in Group": 2, "ID Received": "Yes", "Declared": "No", "Tags": "New Member", "Declaration Date": "2025-02-05"}
        ]

        # Create a DataFrame
        df = pd.DataFrame(data)

        # Save the DataFrame to an Excel file
        df.to_excel(report_path, index=False)

        flash(f"Report generated and saved as {report_filename}!", "success")
        return redirect(url_for('declaration_page'))  # Redirect back to the page

    except Exception as e:
        print(f"Error generating report: {e}")
        flash("Error generating the report. Please try again later.", "error")
        return render_template('error_page.html')  # Render an error page


###? MISC ROUTES ?###

# TODO make a 4040 page
@server.errorhandler(404)
def page_not_found(e):
    return render_template("404.html"), 404

ROOT_STATIC_FILES = {
    "robots.txt",
    "humans.txt",
    "security.txt"
}
@server.route('/<path:filename>')
def root_static_files(filename):
    if filename in ROOT_STATIC_FILES:
        return send_from_directory(server.static_folder, filename)
    abort(404)
    
# Favicon
@server.route('/favicon.ico')
def favicon():
    return send_from_directory(server.static_folder, 'assets/favicon.ico')

###? MISC ROUTES ?#################################################

if __name__ == '__main__':
    flask_server = Server(server.wsgi_app)
    flask_server.watch('static/*.*')  # watches static files (CSS/JS)
    flask_server.watch('templates/*.html')  # watches templates
    flask_server.serve(port=5000, host="127.0.0.1")

    #server.run(debug=True, use_reloader=True, port=5000)
