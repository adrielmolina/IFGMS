from flask import Flask, request, render_template, redirect, url_for, flash, session, jsonify, send_file, send_from_directory, abort
from flask_login import LoginManager, login_user, login_required, logout_user, current_user
from livereload import Server
from py_scripts import db_conn, tools
from datetime import date, datetime
import os
import pandas as pd
import openpyxl
from functools import wraps
from io import BytesIO
from flask import send_file



server = Flask(__name__)
server.jinja_env.auto_reload = True
server.secret_key = os.urandom(24)

# CACHE CONTROL FOR STATIC FILES
if os.getenv("FLASK_ENV") == "production":
    server.config['SEND_FILE_MAX_AGE_DEFAULT'] = 31536000
else:
    server.config['SEND_FILE_MAX_AGE_DEFAULT'] = 0


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
#! TODO redirect user to dashboard if already logged in and trying to access login page

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

# TODO disable this before deployment
@server.before_request
def auto_login():
    ''' Auto-login for development purposes. Remove or disable in production. '''
    auto_login_enabled = False if os.getenv("FLASK_ENV") == "production" else True
    
    db_session = db_conn.SessionLocal()
    if server.config.get("DEBUG_BYPASS_LOGIN", auto_login_enabled):
        if not current_user.is_authenticated:
            test_user = db_session.query(db_conn.models.Accounts).filter_by(username="adriel").first()
            login_user(test_user)


#? -------------------- LOGIN / LOGOUT -------------------- ?#

# TODO add the usernamee and pass to the route address
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
            db_conn.POST_action_log(current_user.username, current_user.user_level, 'Login Attempt', 'Success', current_user.account_id)
            return redirect(url_for('dashboard'))

        elif user.acct_status == 'pending':
            flash({
                "title": "Login Error!",
                "text": "Account not approved yet. Contact admin.",
                "redirect_url": url_for('landing_page')
            },"error")
            db_conn.POST_action_log(username, None, 'Login Attempt', 'Fail. Account status pending', None)
            return render_template('index.html')
    else:
        flash({
            "title": "Login Error!",
            "text": "Wrong username or password. Try again.",
            "redirect_url": url_for('landing_page')
        }, "error")
        db_conn.POST_action_log(username, None, 'Login Attempt', 'Fail. Wrong username/password', None)
        return render_template('index.html')


@server.route('/logout')
@login_required
def logout():
    logout_user()
    session.clear()
    return redirect(url_for("landing_page"))

#? -------------------- END -------------------- ?#

#? -------------------- NAVIGATIONS -------------------- ?#

@server.route('/')
def landing_page():
    # redirect to dashboard if already logged in
    if os.getenv("FLASK_ENV") == "production" or os.getenv("FLASK_ENV") == "staging":
        if current_user.is_authenticated:
            return redirect(url_for('dashboard'))
        
    
    if os.getenv("env") == "production":
        env = 'Live'
    elif os.getenv("env") == "staging":
        env = 'Staging'
    else:
        env = 'Development'
    
    return render_template('index.html', env=env)


@server.route('/create_account')
def create_acc():
    return render_template('create_account.html')


@server.route('/forgot_password')
def forgot_password():
    return render_template('forgot_password.html')


@server.route('/membership_register')
def membership_register():
    return render_template('membership_register.html')


@server.route('/profile_settings')
@login_required
def profile_settings():    
    return render_template('profile_settings.html')


# TODO UNUSED. REMOVE IF NOT NEEDED
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


@server.route('/declaration')
@login_required
@roles_required('admin', 'superadmin')
def declaration_page():
    
    active_dispatch = db_conn.get_current_active_dispatch()
    if active_dispatch:
        dispatch_contents = db_conn.get_current_dispatch_contents(active_dispatch.dispatch_id)
        if dispatch_contents:      
            print('current_dispatch', active_dispatch)
            print('dispatch_contents', dispatch_contents)  
            return render_template('declaration.html', active_dispatch=active_dispatch, dispatch_contents=dispatch_contents)
            
        else:
            # if empty or error
            return render_template('declaration.html', active_dispatch=active_dispatch, dispatch_contents=[])
    else:
        return render_template('declaration.html', active_dispatch=False)

@server.route('/inventory')
@login_required
def inventory():
    # TODO move to a fetch at page load
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
    # TODO move to a fetch at page load
    logs = db_conn.GET_audit_logs()
    
    return render_template('audit_trails.html', logs=logs)


@server.route('/accounts')
@login_required
@roles_required('admin', 'superadmin')
def show_user_accounts():
    return render_template('accounts.html')


@server.route('/settings')
@login_required
def settings():
    has_profile_pic = current_user.profile_pic is not None
    return render_template('settings.html', has_profile_pic=has_profile_pic)


#? -------------------- END -------------------- ?#

#? -------------------- API ROUTES -------------------- ?#

# TODO move to accounts api routes section
@server.route('/create_acc_submit', methods=['POST'])
def create_acc_submit():
    user = request.form.get('username')
    password = request.form.get('password')
    email = request.form.get('email')

    fname = request.form.get('fname').upper()
    mname = request.form.get('mname').upper()
    lname = request.form.get('lname').upper()
    suffix = request.form.get('suffix')

    bdate = request.form.get('bdate')
    contact = request.form.get('contact_no')

    acct_created = date.today().strftime("%Y-%m-%d")
    branch = request.form.get('branch')

    if (fname, mname, lname, suffix, bdate, contact, email, user, password, branch):
        create_new_acc = db_conn.create_account(user=user, password=password, email=email, fname=fname, mname=mname, lname=lname,
                            suffix=suffix, bdate=bdate, contact=contact, acct_created=acct_created, branch=branch)
    
    if not create_new_acc == True:
        flash({
            "title": "Account creation failed!",
            "text": f"{create_new_acc}. Please try again.",
            "redirect_url": url_for('create_acc')
        }, "error")
        return render_template('create_account.html')
    else:
        flash({
        "title": "Account created successfully!",
        "text": "Click continue to go back to login screen.",
        "redirect_url": url_for('landing_page')
        }, "success")
        return render_template('create_account.html')


    # TODO add condition to check if the username already exists
    # TODO fix condition to check if account creation succeeded
    # TODO fix duplicate email/username error flash message not showing up




# ========================== FORGOT PASSWORD ==========================
@server.route("/forgot_password_otp", methods=["GET", "POST"])
def forgot_password_otp():
    if request.method == "POST":
        email = request.form.get("email")

        otp = tools.generate_otp()  # Generate OTP
        save_otp = db_conn.save_otp(email, otp)  # Save OTP in otp_verifications table
        
        if save_otp:
            db_conn.send_otp_email(email, otp)  # Send OTP to user's
        # TODO add error handling if email sending fails
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

        elif result == "already_used":
            flash({
                "title": "OTP has already been used",
                "text": " Please try again.",
                "redirect_url": url_for('forgot_password')
            }, "error")
        
        # TODO fix this check the email should be checked at the first page. this should be just a check if the otp matches or not
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
# TODO continue the ORM syntax update from here
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


@server.route('/api/declaration', methods=['POST'])
def declaration_api():
    method = request.method
    data = request.get_json()

    if method == 'POST':
        dispatch_type = 'transmission' if current_user.office_location != 'Chapter' else 'declaration' 
        dispatch_origin = current_user.office_location
        dispatch_year = datetime.now().year
        dispatch_cutoff = data.get('dispatch_cutoff')
        #date_dispatched = data.get('date_dispatched')
        #dispatch_total = data.get('dispatch_total')
        late_declare = data.get('late_declare')
        dispatch_remarks = data.get('dispatch_remarks')
        
        result = db_conn.create_dispatch(dispatch_type, dispatch_origin, dispatch_year, dispatch_cutoff, late_declare, dispatch_remarks)
        return jsonify({"success": True}) if result == True else jsonify({"success": False, "error": result}), 500 
        


@server.route('/settings_save_changes', methods=['POST'])
@login_required
def settings_save_changes():
    if request.method == 'POST':
        print("=== FORM DATA RECEIVED ===")
        print(request.form)
        print("===========================")

        first_name = request.form.get('first_name', '').upper()
        middle_name = request.form.get('middle_name', '').upper()
        last_name = request.form.get('last_name', '').upper()
        birthdate = request.form.get('birthdate')
        email = request.form.get('email')
        phone = request.form.get('phone')

        if all([first_name, middle_name, last_name, birthdate, email, phone]):
            update_success = db_conn.update_user_details(
            current_user.account_id,  # ✅ actual user ID
            first_name,
            middle_name,
            last_name,
            birthdate,
            phone,
            email
            )

            if update_success:
                flash("Details updated successfully!", "success")
            else:
                flash("Update failed!", "error")

        else:
            flash("Please fill out all fields.", "error")

        return redirect(url_for('settings'))

    return redirect(url_for('settings'))

# === Upload profile picture ===
@server.route('/api/upload_profile_pic', methods=['POST'])
@login_required
def upload_profile_pic():
    try:
        # Debug print
        print("=== /api/upload_profile_pic called ===")
        if 'profile_pic' not in request.files:
            print("No 'profile_pic' in request.files. Keys:", request.files.keys())
            return jsonify({"success": False, "error": "No file part 'profile_pic'"}), 400

        file = request.files['profile_pic']
        if file.filename == '':
            print("Empty filename")
            return jsonify({"success": False, "error": "Empty filename"}), 400

        file_data = file.read()
        print(f"Received file: name={file.filename}, size={len(file_data)} bytes, content_type={file.content_type}")

        # Call DB helper to save the profile pic
        saved = db_conn.save_profile_pic(current_user.account_id, file_data)
        if saved:
            print("Saved profile pic to DB for user", current_user.account_id)
            # Return updated state (whether the user has a profile pic)
            return jsonify({"success": True, "has_profile_pic": True})
        else:
            print("db_conn.save_profile_pic returned False")
            return jsonify({"success": False, "error": "DB save failed"}), 500

    except Exception as e:
        print("Exception in upload_profile_pic:", e)
        return jsonify({"success": False, "error": str(e)}), 500

# === Fetch profile picture ===
@server.route('/api/get_profile_pic/<int:user_id>')
@login_required
def get_profile_pic(user_id):
    image_data = db_conn.get_profile_pic(user_id)
    if image_data:
        return send_file(BytesIO(image_data), mimetype='image/jpeg')
    else:
        return send_file('static/assets/pfp.jpg', mimetype='image/jpeg')

@server.route('/api/delete_profile_pic', methods=['DELETE'])
@login_required
def delete_profile_pic():
    success = db_conn.save_profile_pic(current_user.account_id, None)
    return jsonify({"success": success})

# API FOR DASHBOARD
@server.route('/api/get_pending_claims_count')
def get_pending_claims_count():
    count = db_conn.get_pending_claims_count()
    return jsonify({"pending_claims_count": count})


@server.route('/api/get_all_dispatch')
def get_dispatch_records():
    dispatch_records = db_conn.get_all_dispatch_records()
    if dispatch_records is None:
        return jsonify({"success": False, "error": "Failed to fetch dispatch records"}), 500
    print('flask_server: dispatch_records', [record.to_dict() for record in dispatch_records])
    return jsonify([record.to_dict() for record in dispatch_records])



# ====== API FOR DASHBOARD STATS ======

@server.route('/api/members/count', methods=['GET'])
def get_members_count():
    try:
        # Count all entries across all records
        total_count = 0
        all_records = db_conn.get_member_records()
        
        for record in all_records:
            entries = db_conn.get_entries(record.record_id)  # or record.id
            total_count += len(entries)
            
        return jsonify({
            'success': True,
            'total_members': total_count
        })
    except Exception as e:
        print(f"Error in get_members_count: {e}")
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500

@server.route('/api/members/expiring_soon', methods=['GET'])
def get_expiring_soon_count():
    try:
        from datetime import datetime, timedelta
        today = datetime.now().date()
        thirty_days_from_now = today + timedelta(days=30)
        last_month = today - timedelta(days=30)
        
        # Get all records and their entries
        all_records = db_conn.get_member_records()
        
        current_expiring = 0
        previous_expiring = 0
        
        for record in all_records:
            # Get entries for this record
            entries = db_conn.get_entries(record.record_id)
            
            for entry in entries:
                # Check OR_date for expiration
                if hasattr(entry, 'OR_date') and entry.OR_date:
                    # Convert to date object if it's string
                    if isinstance(entry.OR_date, str):
                        or_date = datetime.strptime(entry.OR_date, '%Y-%m-%d').date()
                    else:
                        or_date = entry.OR_date
                    
                    # Calculate expiration date (OR_date + 1 year)
                    expiration_date = or_date + timedelta(days=365)
                    
                    # Current period: expiring in next 30 days
                    if today <= expiration_date <= thirty_days_from_now:
                        current_expiring += 1
                    
                    # Previous period: expired in last 30 days
                    if last_month <= expiration_date <= today:
                        previous_expiring += 1
        
        # Calculate percentage change
        if previous_expiring > 0:
            percentage_change = ((current_expiring - previous_expiring) / previous_expiring) * 100
        else:
            percentage_change = 0
        
        return jsonify({
            'success': True,
            'expiring_soon_count': current_expiring,
            'previous_period_count': previous_expiring,
            'percentage_change': round(percentage_change, 2),
            'timeframe_days': 30
        })
    except Exception as e:
        print(f"Error in get_expiring_soon_count: {e}")
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500


# API FOR MEMBERS PAGE

# TODO fix api route names ex. /api/members/get_records

@server.route('/api/members/records', methods=['GET'])
def get_members():
    member_records = db_conn.get_member_records()
    return jsonify([record.to_dict() for record in member_records])
    '''
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
    '''
    
@server.route('/api/add_record', methods=['POST'])
def add_new_record():
    new_record_id = db_conn.add_new_record()
    return jsonify({"success": True, "record_id": new_record_id})

@server.route('/api/save_record_details', methods=['PATCH'])
def save_record_details():
    data = request.get_json()
    if data:
        db_conn.save_record_details(data)
        return jsonify({"success": True})


@server.route('/api/members/<int:record_id>/entries', methods=['GET'])
def get_entries(record_id):
    entries = db_conn.get_entries(record_id)
    return jsonify(entries)

@server.route('/api/save_entry_details', methods=['POST'])
def save_entry_details():
    data = request.get_json()
    print(data)
    if data:
        record_id = data.get('record_id')
        maab_category = data.get('maab_category')
        maab_no = data.get('maab_no')
                
        first_name = data.get('first_name').upper()
        middle_name = data.get('middle_name').upper()
        last_name = data.get('last_name').upper()
        suffix = data.get('suffix')
        
        birthdate_string = data.get('birth_date')        
        if birthdate_string:
            birthdate = datetime.strptime(birthdate_string, "%Y-%m-%d").date()
        else:
            birthdate = None
            
        age = data.get('age')
        
        sex = data.get('sex')
        if sex == "null" or sex == "":
            sex = None
            
        bloodtype = data.get('blood_type')
        if bloodtype == "null" or bloodtype == "":
            bloodtype = None
        
        contact = data.get('contact_no')
        email = data.get('email')
        address = data.get('address')
        
        id_received = data.get('id_received')
        declared = data.get('declared')
        declaration_date_string = data.get('declaration_date')
        if declaration_date_string:
            declaration_date = datetime.strptime(declaration_date_string, "%Y-%m-%d").date()
        else:
            declaration_date = None
                
        paid = data.get('paid')
        OR_num = int(data.get('OR_num')) if data.get('OR_num') else None
        OR_date_string = data.get('OR_date')
        if OR_date_string:
            OR_date = datetime.strptime(OR_date_string, "%Y-%m-%d").date()
        else:
            OR_date = None
            
        remarks = data.get('remarks')
        tags = data.get('tags')
        dispatch_ready = data.get('dispatch_ready')
        
        result = db_conn.save_entry_details(record_id, maab_category, maab_no, first_name, middle_name, last_name, suffix, birthdate, age, sex, bloodtype, contact, email, address, id_received, declared, declaration_date, paid, OR_num, OR_date, remarks, tags, dispatch_ready)

        if result:
            return jsonify({"success": True})
        else:
            return jsonify({"success": False, "error": result}), 500
    else:
        return jsonify({"success": False, "error": "No data provided"}), 400


@server.route('/api/add_to_dispatch', methods=['PATCH'])
@login_required
@roles_required('admin', 'superadmin')
def add_to_dispatch():
    data = request.get_json()  # optional — for future if you need to pass something
    try:
        result = db_conn.add_to_dispatch()
        print('add_to_dispatch result:', result)
        if result:
            return jsonify({"success": True, "added_to_dispatch_count": result})
        else:
            return jsonify({"success": False, "error": "No entries to add to dispatch"}), 500
    except Exception as e:
        return jsonify({"success": False, "error": str(e)}), 500

                        


# TODO check if a record exist for Online Registration on the same day. if yes put the entry on that record
@server.route('/api/member_register', methods=['POST'])
def member_register():
    data = request.get_json()
    print(data)
    if data:
        fname = data.get('fname').upper()
        mname = data.get('mname').upper()
        lname = data.get('lname').upper()
        suffix = data.get('suffix')
        
        birthdate_string = data.get('birthdate')
        birthdate = datetime.strptime(birthdate_string, "%Y-%m-%d").date()
        
        age = data.get('age')
        
        sex = data.get('sex')
        if sex == "null" or sex == "":
            sex = None
            
        bloodtype = data.get('bloodtype')
        if bloodtype == "null" or bloodtype == "":
            bloodtype = None
        
        contact = data.get('contact')
        email = data.get('email')
        municipality = data.get('municipality')
        
        address = data.get('address')
        maab_cat = data.get('maab_cat')
        origin = data.get('origin')
        
        result = db_conn.add_entry_content_online(fname, mname, lname, suffix, birthdate, age, sex, bloodtype, contact, email, municipality, address, maab_cat, origin)

        if result:
            return jsonify({"success": True})
        else:
            return jsonify({"success": False, "error": result}), 500
    else:
        return jsonify({"success": False, "error": "No data provided"}), 400
    
@server.route('/api/get_claim_records')
def get_claim_records():
    claim_records = db_conn.get_claim_records()
    return jsonify(claim_records)

    '''
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
    '''


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


#* -------------------- ACCOUNTS API ROUTES -------------------- *#

@server.route('/api/accounts', methods=['GET'])
@login_required
@roles_required('admin', 'superadmin')
def get_accounts():
    active_accounts = db_conn.get_accounts(status=['approved', 'archived', 'declined'])
    pending_accounts = db_conn.get_accounts(status=['pending'])

    return jsonify({"active": [acc.to_dict() for acc in active_accounts],
                    "pending": [acc.to_dict() for acc in pending_accounts]})

@server.route('/api/accounts/<id>/create', methods=['POST'])
@login_required
@roles_required('admin', 'superadmin')
def create_account(id):
    pass


@server.route('/api/accounts/approve', methods=['PATCH'])
@login_required
@roles_required('admin', 'superadmin')
def approve_account():
    data = request.get_json()
    ids = data.get('ids', [])

    for acc_id in ids:
        success = db_conn.approve_account(acc_id)

        if not success:
            return jsonify({"success": False, "error": f"Failed to approve account ID {acc_id}"}), 500

    return jsonify({"success": True})

@server.route('/api/accounts/decline', methods=['PATCH'])
@login_required
@roles_required('admin', 'superadmin')
def decline_account():
    data = request.get_json()
    ids = data.get('ids', [])

    for acc_id in ids:
        success = db_conn.decline_account(acc_id)
        
        if not success:
            return jsonify({"success": False, "error": f"Failed to decline account ID {acc_id}"}), 500

    return jsonify({"success": True})

@server.route('/api/accounts/reset', methods=['PATCH'])
@login_required
@roles_required('admin', 'superadmin')
def reset_account():
    data = request.get_json()
    ids = data.get('ids', [])

    for acc_id in ids:
        success = db_conn.reset_account(acc_id)

        if not success:
            return jsonify({"success": False, "error": f"Failed to reset password of account ID {acc_id}"}), 500
        
    return jsonify({"success": True})

@server.route('/api/accounts/update_userlvl', methods=['PATCH'])
@login_required
@roles_required('admin', 'superadmin')
def update_userlvl():
    try:
        data = request.get_json()
        id = data.get('id')
        user_level = data.get('user_level')
    
        success = db_conn.update_userlvl(id, user_level)

        if success:
            return jsonify({"success": True})
        else:
            return jsonify({"success": False, "error": "Failed to update user level"}), 500
        
    except Exception as e:
        print(f"Error updating user level: {e}")
        return jsonify({"success": False, "error": str(e)}), 500


@server.route('/api/accounts/update_ofc', methods=['PATCH'])
@login_required
@roles_required('admin', 'superadmin')
def update_ofc():
    try:
        data = request.get_json()
        id = data.get('id')
        location = data.get('office_location')
    
        success = db_conn.update_ofc(id, location)

        if success:
            return jsonify({"success": True})
        else:
            return jsonify({"success": False, "error": "Failed to update office location"}), 500
        
    except Exception as e:
        print(f"Error updating office location: {e}")
        return jsonify({"success": False, "error": str(e)}), 500


@server.route('/api/accounts/archive', methods=['PATCH'])
@login_required
@roles_required('admin', 'superadmin')
def archive_account():
    data = request.get_json()
    ids = data.get('ids', [])

    for acc_id in ids:
        success = db_conn.archive_account(acc_id)
        
        if not success:
            return jsonify({"success": False, "error": f"Failed to archive account ID {acc_id}"}), 500

    return jsonify({"success": True})

# TODO add batch account creation (tickbox + toast message)
# TODO set default password format (bdate + initials)
# TODO make an overlay page for creating accounts on the accounts page and make it auto approved
#* -------------------- END ACCOUNTS API ROUTES -------------------- *#


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
    

# ==================== API ROUTES FOR AUDIT TRAILS ====================
# SIMPLE WORKING API ROUTES
@server.route('/api/get_users', methods=['GET'])
@login_required
@roles_required('admin', 'superadmin')
def api_get_users():
    try:
        print("🔍 Getting users...")
        db_session = db_conn.SessionLocal()
        users = db_session.query(db_conn.models.Accounts).filter(
            db_conn.models.Accounts.acct_status.in_(['approved', 'staff'])
        ).all()
        
        users_list = []
        for user in users:
            users_list.append({
                'user_id': user.account_id,
                'username': user.username,
                'first_name': user.first_name,
                'last_name': user.last_name
            })
        
        print(f"✅ Found {len(users_list)} users")
        return jsonify(users_list)
        
    except Exception as e:
        print(f"❌ Error getting users: {e}")
        return jsonify([])
    finally:
        db_session.close()

@server.route('/api/get_filtered_logs', methods=['GET'])
@login_required
@roles_required('admin', 'superadmin')
def api_get_filtered_logs():
    try:
        user_id = request.args.get('user_id', '')
        filter_date = request.args.get('date', '')
        
        print(f"🔍 Filtering - User: {user_id}, Date: {filter_date}")
        
        # Get all logs
        all_logs = db_conn.GET_audit_logs()
        print(f"📋 Total logs: {len(all_logs)}")
        
        filtered_logs = []
        
        for log in all_logs:
            # Get user ID - try different attribute names
            log_user_id = getattr(log, 'account_id', None)
            if log_user_id is None:
                log_user_id = getattr(log, 'user_id', None)
            
            log_timestamp = getattr(log, 'timestamp', None)
            
            # Check user filter
            user_match = not user_id or (log_user_id and str(log_user_id) == user_id)
            
            # Check date filter
            date_match = True
            if filter_date:
                if log_timestamp:
                    if hasattr(log_timestamp, 'strftime'):
                        log_date = log_timestamp.strftime('%Y-%m-%d')
                    else:
                        log_date = str(log_timestamp)[:10]
                    date_match = (log_date == filter_date)
                else:
                    date_match = False
            
            if user_match and date_match:
                # Format timestamp
                if log_timestamp and hasattr(log_timestamp, 'strftime'):
                    timestamp_str = log_timestamp.strftime('%Y-%m-%d %H:%M:%S')
                else:
                    timestamp_str = str(log_timestamp)
                
                filtered_logs.append({
                    'log_id': getattr(log, 'log_id', ''),
                    'username': getattr(log, 'username', ''),
                    'user_level': getattr(log, 'user_level', ''),
                    'action': getattr(log, 'action', ''),
                    'details': getattr(log, 'details', ''),
                    'timestamp': timestamp_str,
                    'ip_address': getattr(log, 'ip_address', '')
                })
        
        print(f"✅ Filtered logs: {len(filtered_logs)}")
        return jsonify({
            "success": True, 
            "logs": filtered_logs,
            "filters": {"user_id": user_id, "date": filter_date}
        })
        
    except Exception as e:
        print(f"❌ Error in get_filtered_logs: {e}")
        return jsonify({
            "success": False, 
            "error": str(e),
            "logs": []
        }), 500
    
    # DEBUG ROUTE - Check if APIs are working
@server.route('/api/debug_test')
def debug_test():
    return jsonify({"message": "API is working!", "status": "success"})

# DEBUG ROUTE - Check audit logs structure
@server.route('/api/debug_logs_info')
@login_required
@roles_required('admin', 'superadmin')
def debug_logs_info():
    try:
        logs = db_conn.GET_audit_logs()
        if not logs:
            return jsonify({"message": "No logs found", "count": 0})
        
        # Check first log structure
        first_log = logs[0]
        log_attrs = {}
        for attr in dir(first_log):
            if not attr.startswith('_'):
                try:
                    value = getattr(first_log, attr)
                    log_attrs[attr] = {
                        "type": str(type(value)),
                        "value": str(value)[:100] if value else "None"
                    }
                except:
                    pass
        
        return jsonify({
            "total_logs": len(logs),
            "first_log_attributes": log_attrs,
            "sample_data": {
                "log_id": getattr(first_log, 'log_id', 'N/A'),
                "username": getattr(first_log, 'username', 'N/A'),
                "account_id": getattr(first_log, 'account_id', 'N/A'),
                "timestamp": str(getattr(first_log, 'timestamp', 'N/A'))
            }
        })
        
    except Exception as e:
        return jsonify({"error": str(e)})
#? -------------------- NOTIFICATIONS -------------------- ?#

@server.route('/api/notifications', methods=['GET'])
def get_notifications():
    try:
        from datetime import datetime, timedelta
        today = datetime.now().date()
        notifications = []
        
        print("🔍 Starting notifications check...")
        
        # Get all member records
        all_records = db_conn.get_member_records()
        print(f"📊 Found {len(all_records)} records")
        
        # 1. Check for birthdays today
        birthday_count = 0
        for record in all_records:
            try:
                # Get record ID safely
                record_id = getattr(record, 'record_id', getattr(record, 'id', None))
                if not record_id:
                    continue
                    
                # Get entries for this record
                entries = db_conn.get_entries(record_id)
                
                for entry in entries:
                    # Check if entry has birth_date
                    birth_date = getattr(entry, 'birth_date', None)
                    if birth_date:
                        # Convert to date object if string
                        if isinstance(birth_date, str):
                            try:
                                birth_date = datetime.strptime(birth_date, '%Y-%m-%d').date()
                            except:
                                continue
                        elif isinstance(birth_date, datetime):
                            birth_date = birth_date.date()
                        
                        # Check if birthday is today
                        if birth_date.month == today.month and birth_date.day == today.day:
                            first_name = getattr(entry, 'first_name', '')
                            last_name = getattr(entry, 'last_name', '')
                            email = getattr(entry, 'email', '')
                            
                            notifications.append({
                                'type': 'birthday',
                                'message': f"🎂 {first_name} {last_name} has birthday today!",
                                'member_name': f"{first_name} {last_name}",
                                'member_email': email,
                                'priority': 'high'
                            })
                            birthday_count += 1
            except Exception as e:
                print(f"❌ Error processing record: {e}")
                continue
        
        print(f"🎂 Found {birthday_count} birthdays today")
        
        # 2. Check for expiring memberships (30 days)
        expiring_count = 0
        thirty_days_from_now = today + timedelta(days=30)
        
        for record in all_records:
            try:
                record_id = getattr(record, 'record_id', getattr(record, 'id', None))
                if not record_id:
                    continue
                    
                entries = db_conn.get_entries(record_id)
                
                for entry in entries:
                    or_date = getattr(entry, 'OR_date', None)
                    if or_date:
                        # Convert to date object if string
                        if isinstance(or_date, str):
                            try:
                                or_date = datetime.strptime(or_date, '%Y-%m-%d').date()
                            except:
                                continue
                        elif isinstance(or_date, datetime):
                            or_date = or_date.date()
                        
                        # Calculate expiration (OR_date + 1 year)
                        expiration_date = or_date + timedelta(days=365)
                        days_until_expiry = (expiration_date - today).days
                        
                        # Check if expiring within 30 days
                        if 0 <= days_until_expiry <= 30:
                            first_name = getattr(entry, 'first_name', '')
                            last_name = getattr(entry, 'last_name', '')
                            email = getattr(entry, 'email', '')
                            
                            notifications.append({
                                'type': 'expiring',
                                'message': f"⏰ {first_name} {last_name} membership expires in {days_until_expiry} days",
                                'member_name': f"{first_name} {last_name}",
                                'member_email': email,
                                'additional_data': {'days_left': days_until_expiry},
                                'priority': 'medium'
                            })
                            expiring_count += 1
            except Exception as e:
                print(f"❌ Error processing record for expiring: {e}")
                continue
        
        print(f"⏰ Found {expiring_count} expiring memberships")
        print(f"📨 Total notifications: {len(notifications)}")
        
        return jsonify({
            'success': True,
            'notifications': notifications,
            'total_count': len(notifications),
            'summary': {
                'birthdays': birthday_count,
                'expiring': expiring_count
            }
        })
        
    except Exception as e:
        print(f"❌ Major error in get_notifications: {e}")
        import traceback
        traceback.print_exc()
        
        return jsonify({
            'success': False,
            'error': str(e),
            'notifications': [],
            'total_count': 0
        }), 500

# TEST ROUTE - OPTIONAL
@server.route('/api/notifications/test', methods=['GET'])
def test_notifications_route():
    return jsonify({"message": "Notifications route is working", "success": True})


#? -------------------- MISC ROUTES -------------------- ?#

@server.errorhandler(404)
def page_not_found(e):
    return render_template("404.html"), 404

@server.errorhandler(403)
def page_not_found(e):
    return render_template("403.html"), 403

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

#? -------------------- END -------------------- ?#


if __name__ == '__main__':
    
    # DEPRECATED LIVE RELOAD METHOD. REMOVE LATER
    '''
    flask_server = Server(server.wsgi_app)
    flask_server.watch('static/*.*')  # watches static files (CSS/JS)
    flask_server.watch('templates/*.html')  # watches templates
    flask_server.serve(port=5000, host="127.0.0.1")

    #server.run(debug=True, use_reloader=True, port=5000)
    '''
    print("FLASK_ENV:", os.getenv("FLASK_ENV"))
    
    if os.getenv("FLASK_ENV") == "production":
        #server.run(host="0.0.0.0", port=5000)
        pass
    else:
    #if os.getenv("FLASK_ENV") == "development":
        flask_server = Server(server.wsgi_app)
        flask_server.watch('static/*.*')
        flask_server.watch('templates/*.html')
        flask_server.serve(port=5000, host="127.0.0.1")
        

        
