from flask import Flask, request, render_template, redirect, url_for, flash, session, jsonify, send_file, send_from_directory, abort
from flask_login import LoginManager, login_user, login_required, logout_user, current_user
from livereload import Server
from py_scripts import db_conn, tools, models
from py_scripts.db_conn import SessionLocal
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
    db_conn.POST_action_log(current_user.username, current_user.user_level, 'Logout', 'User logged out', current_user.account_id)
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
    user_location = current_user.office_location if current_user and current_user.office_location else 'Chapter'
    print(f"DEBUG: User location being passed to template: {user_location}")
    return render_template('members.html', user_location=user_location)


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
@server.route('/api/export_record_entries/<int:record_id>')
@login_required
def export_record_entries(record_id):
    try:
        # Fetch record details
        db_session = db_conn.SessionLocal()
        
        record = db_session.query(db_conn.models.Records).filter_by(record_id=record_id).first()
        
        if not record:
            return jsonify({'error': 'Record not found'}), 404
        
        # Fetch entries for this record
        entries = (
            db_session.query(
                db_conn.models.Entries,
                db_conn.models.Members
            )
            .join(db_conn.models.Members, db_conn.models.Entries.member_id == db_conn.models.Members.member_id)
            .filter(db_conn.models.Entries.record_id == record_id)
            .all()
        )
        
        if not entries:
            return jsonify({'error': 'No entries found for this record'}), 404
        
        # Prepare data for Excel with required fields only
        data = []
        for entry, member in entries:
            data.append({
                # Entry details
                'Category': entry.maab_category or '',
                'MAAB No': entry.maab_no or '',
                'First Name': member.first_name or '',
                'Middle Name': member.middle_name or '',
                'Last Name': member.last_name or '',
                'Suffix': member.suffix or 'NA',
                'Birthdate': member.birth_date.strftime('%Y-%m-%d') if member.birth_date else '',
                'Age': member.age or '',
                'Sex': member.sex or '',
                'Contact No': f"+63{member.contact_no}" if member.contact_no else '',
                'Email': member.email or '',
                'OR No': entry.OR_num or '',
                'OR Date': entry.OR_date.strftime('%Y-%m-%d') if entry.OR_date else '',
                'Declared': 'Yes' if entry.declared else 'No',
                'Dispatch Ready': 'Yes' if entry.dispatch_ready else 'No',
                'Dispatch ID': entry.dispatch_id or '',
                'Remarks': entry.remarks or '',
                # Record details (these will be the same for all entries in this record)
                'Declaration Date': record.declaration_date.strftime('%Y-%m-%d') if record.declaration_date else '',
                'Effectivity Date': record.effectivity_date.strftime('%Y-%m-%d') if record.effectivity_date else '',
                'Location Category': record.location_category or '',
                'Municipality': record.municipality or '',
                'District': record.district or '',
                'Origin': record.origin or ''
            })
        
        # Create DataFrame
        df = pd.DataFrame(data)
        
        # Create the record_exports folder if it doesn't exist
        export_folder = os.path.join(os.path.dirname(__file__), 'record_exports')
        os.makedirs(export_folder, exist_ok=True)
        
        # Generate filename
        loc_particular = record.location_particular or 'Unknown_Location'
        dec_date = record.declaration_date.strftime('%Y-%m-%d') if record.declaration_date else 'no_date'
        
        # Clean filename (remove special characters)
        clean_location = "".join(c for c in loc_particular if c.isalnum() or c in (' ', '-', '_')).rstrip()
        clean_location = clean_location.replace(' ', '_')
        
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        filename = f"{clean_location}_{dec_date}_{timestamp}.xlsx"
        file_path = os.path.join(export_folder, filename)
        
        # Create Excel file and save to server folder
        with pd.ExcelWriter(file_path, engine='openpyxl') as writer:
            # Write the main title first
            workbook = writer.book
            worksheet = workbook.create_sheet('Entries')
            
            # Add main title
            worksheet.merge_cells('A1:W1')
            worksheet['A1'] = f"{loc_particular} - {dec_date}"
            worksheet['A1'].font = openpyxl.styles.Font(size=16, bold=True)
            worksheet['A1'].alignment = openpyxl.styles.Alignment(horizontal='center')
            
            # Add record details as separate rows
            record_details = [
                f"Declaration Date: {record.declaration_date.strftime('%Y-%m-%d') if record.declaration_date else 'N/A'}",
                f"Effectivity Date: {record.effectivity_date.strftime('%Y-%m-%d') if record.effectivity_date else 'N/A'}",
                f"Location Category: {record.location_category or 'N/A'}",
                f"Municipality: {record.municipality or 'N/A'}",
                f"District: {record.district or 'N/A'}",
                f"Origin: {record.origin or 'N/A'}"
            ]
            
            # Write record details starting from row 2
            for i, detail in enumerate(record_details, start=2):
                worksheet[f'A{i}'] = detail
            
            # Write the DataFrame starting from row 8 (after title and record details)
            start_row = 8
            # Write headers
            for col_num, column_name in enumerate(df.columns, 1):
                cell = worksheet.cell(row=start_row, column=col_num)
                cell.value = column_name
                cell.font = openpyxl.styles.Font(bold=True)
                cell.fill = openpyxl.styles.PatternFill(start_color="DDDDDD", end_color="DDDDDD", fill_type="solid")
                cell.alignment = openpyxl.styles.Alignment(horizontal='center')
            
            # Write data rows
            for row_num, row_data in enumerate(df.values, start_row + 1):
                for col_num, cell_value in enumerate(row_data, 1):
                    worksheet.cell(row=row_num, column=col_num, value=cell_value)
            
            # Adjust column widths for all required columns
            column_widths = {
                'A': 15,  # Category
                'B': 15,  # MAAB No
                'C': 15,  # First Name
                'D': 15,  # Middle Name
                'E': 15,  # Last Name
                'F': 8,   # Suffix
                'G': 12,  # Birthdate
                'H': 6,   # Age
                'I': 8,   # Sex
                'J': 15,  # Contact No
                'K': 20,  # Email
                'L': 10,  # OR No
                'M': 10,  # OR Date
                'N': 10,  # Declared
                'O': 15,  # Dispatch Ready
                'P': 12,  # Dispatch ID
                'Q': 20,  # Remarks
                'R': 12,  # Declaration Date (record)
                'S': 12,  # Effectivity Date (record)
                'T': 20,  # Location Category (record)
                'U': 15,  # Municipality (record)
                'V': 10,  # District (record)
                'W': 12   # Origin (record)
            }
            
            for col_letter, width in column_widths.items():
                worksheet.column_dimensions[col_letter].width = width
        
        db_conn.POST_action_log(current_user.username, current_user.user_level, 'Export Record', f'Exported record {record_id} with {len(entries)} entries', current_user.account_id)
        return jsonify({
            'success': True,
            'message': f'File exported successfully to record_exports folder',
            'filename': filename,
            'file_path': file_path,
            'export_count': len(entries)
        })
        
    except Exception as e:
        print(f"Export error: {e}")
        import traceback
        traceback.print_exc()
        return jsonify({'success': False, 'error': 'Internal server error'}), 500
    finally:
        db_session.close()

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


# KEEP ONLY THIS VERSION OF THE ROUTE - REMOVE THE DUPLICATE LATER IN THE FILE
@server.route('/api/declaration', methods=['POST'])
def declaration_api():
    try:
        data = request.get_json()
        if not data:
            db_conn.POST_action_log(current_user.username, current_user.user_level, 'Create Dispatch Failed', 'No data provided', current_user.account_id)
            return jsonify({"success": False, "error": "No data provided"}), 400

        dispatch_type = 'transmission' if current_user.office_location != 'Chapter' else 'declaration' 
        dispatch_origin = current_user.office_location
        dispatch_year = datetime.now().year
        dispatch_cutoff = data.get('dispatch_cutoff')
        late_declare = data.get('late_declare')
        dispatch_remarks = data.get('dispatch_remarks')
        
        result = db_conn.create_dispatch(dispatch_type, dispatch_origin, dispatch_year, dispatch_cutoff, late_declare, dispatch_remarks)
        
        if result == True:
            db_conn.POST_action_log(current_user.username, current_user.user_level, 'Create Dispatch', f'Created {dispatch_type} dispatch from {dispatch_origin}', current_user.account_id)
            return jsonify({"success": True})
        else:
            db_conn.POST_action_log(current_user.username, current_user.user_level, 'Create Dispatch Failed', f'Failed: {result}', current_user.account_id)
            return jsonify({"success": False, "error": result}), 500
            
    except Exception as e:
        print(f"Declaration API error: {e}")
        db_conn.POST_action_log(current_user.username, current_user.user_level, 'Create Dispatch Error', f'Error: {str(e)}', current_user.account_id)
        return jsonify({"success": False, "error": "Internal server error"}), 500


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
                db_conn.POST_action_log(current_user.username, current_user.user_level, 'Update Profile', 'Updated personal profile information', current_user.account_id)
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
            db_conn.POST_action_log(current_user.username, current_user.user_level, 'Upload Profile Picture', 'Uploaded new profile picture', current_user.account_id)
            return jsonify({"success": True, "has_profile_pic": True})
        else:
            print("db_conn.save_profile_pic returned False")
            return jsonify({"success": False, "error": "DB save failed"}), 500

    except Exception as e:
        print("Exception in upload_profile_pic:", e)
        return jsonify({"success": False, "error": str(e)}), 500

@server.route('/api/members/filter_options', methods=['GET'])
@login_required
def get_member_filter_options():
    db_session = SessionLocal()
    try:
        # Get distinct years from records
        years = db_session.query(models.Records.year).distinct().filter(models.Records.year.isnot(None)).order_by(models.Records.year.desc()).all()
        years_list = [year[0] for year in years]
        
        # Get distinct origins from records
        origins = db_session.query(models.Records.origin).distinct().filter(models.Records.origin.isnot(None)).order_by(models.Records.origin).all()
        origins_list = [origin[0] for origin in origins]
        
        return jsonify({
            'years': years_list,
            'origins': origins_list
        })
        
    except Exception as e:
        print(f"Error fetching filter options: {e}")
        return jsonify({'years': [], 'origins': []}), 500
    finally:
        db_session.close()

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
    db_conn.POST_action_log(current_user.username, current_user.user_level, 'Delete Profile Picture', 'Deleted profile picture', current_user.account_id)
    return jsonify({"success": success})

# API FOR DASHBOARD

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


# API FOR MEMBERS PAGE

# TODO fix api route names ex. /api/members/get_records

@server.route('/api/members/records', methods=['GET'])
def get_members():
    try:
        status = request.args.get('status', 'active')
        print(f"DEBUG: Fetching member records with status: {status}")
        
        member_records = db_conn.get_member_records(status=status)
        print(f"DEBUG: Records fetched: {len(member_records) if member_records else 'None'}")
        
        if member_records is None:
            print("DEBUG: No records returned from database")
            return jsonify({"error": "Failed to fetch member records"}), 500
            
        records_list = []
        for record in member_records:
            try:
                record_dict = record.to_dict()
                records_list.append(record_dict)
            except Exception as e:
                print(f"DEBUG: Error converting record to dict: {e}")
                continue
                
        print(f"DEBUG: Returning {len(records_list)} records")
        return jsonify(records_list)
        
    except Exception as e:
        print(f"DEBUG: Error in get_members: {str(e)}")
        import traceback
        traceback.print_exc()
        return jsonify({"error": "Internal server error"}), 500
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

@server.route('/api/archive_record', methods=['PATCH'])
@login_required
def archive_record():
    try:
        data = request.get_json()
        record_id = data.get('record_id')
        
        if not record_id:
            db_conn.POST_action_log(current_user.username, current_user.user_level, 'Archive Record Failed', 'No record ID provided', current_user.account_id)
            return jsonify({"success": False, "error": "No record ID provided"}), 400
        
        # Use the new function that handles both archiving and logging in one session
        success = db_conn.archive_member_record_with_log(record_id, current_user.account_id)
        
        if success:
            db_conn.POST_action_log(current_user.username, current_user.user_level, 'Archive Record', f'Archived record ID: {record_id}', current_user.account_id)
            return jsonify({"success": True})
        else:
            db_conn.POST_action_log(current_user.username, current_user.user_level, 'Archive Record Failed', f'Failed to archive record ID: {record_id}', current_user.account_id)
            return jsonify({"success": False, "error": "Failed to archive record"}), 500
            
    except Exception as e:
        print(f"Error archiving record: {e}")
        import traceback
        traceback.print_exc()
        db_conn.POST_action_log(current_user.username, current_user.user_level, 'Archive Record Error', f'Error: {str(e)}', current_user.account_id)
        return jsonify({"success": False, "error": "Internal server error"}), 500
    
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
            db_conn.POST_action_log(current_user.username, current_user.user_level, 'Add Entry', f'Added entry for {first_name} {last_name}', current_user.account_id)
            return jsonify({"success": True})
        else:
            db_conn.POST_action_log(current_user.username, current_user.user_level, 'Add Entry Failed', f'Failed to add entry for {first_name} {last_name}', current_user.account_id)
            return jsonify({"success": False, "error": result}), 500
    else:
        db_conn.POST_action_log(current_user.username, current_user.user_level, 'Add Entry Failed', 'No data provided', current_user.account_id)
        return jsonify({"success": False, "error": "No data provided"}), 400


@server.route('/api/save_entry_update', methods=['POST'])
@login_required
def save_entry_update():
    try:
        data = request.get_json()
        print("=== ENTRY UPDATE API CALL ===")
        print(f"Request data: {data}")
        print(f"Data types: { {k: type(v) for k, v in data.items()} }")
        
        if not data:
            db_conn.POST_action_log(current_user.username, current_user.user_level, 'Update Entry Failed', 'No data provided', current_user.account_id)
            return jsonify({"success": False, "error": "No data provided"}), 400
            
        entry_id = data.get('entry_id')
        print(f'Processing update for entry_id: {entry_id}')
        
        result = db_conn.save_entry_updates(data)
        
        if result:
            db_conn.POST_action_log(current_user.username, current_user.user_level, 'Update Entry', f'Updated entry ID: {entry_id}', current_user.account_id)
            print("✅ Entry update successful")
            return jsonify({"success": True})
        else:
            db_conn.POST_action_log(current_user.username, current_user.user_level, 'Update Entry Failed', f'Failed to update entry ID: {entry_id}', current_user.account_id)
            print("❌ Entry update failed in db_conn")
            return jsonify({"success": False, "error": "Database update failed"}), 500
            
    except Exception as e:
        print(f"💥 Exception in save_entry_update route: {e}")
        import traceback
        traceback.print_exc()
        return jsonify({"success": False, "error": str(e)}), 500


@server.route('/api/get_report/target_vs_actual/<int:year>', methods=['GET'])
def target_vs_actual(year):
    if not year:
        return jsonify({"success": False, "error": "Year parameter is required"}), 400

    report_data = db_conn.get_report_target_vs_actual(year)
    if report_data is None:
        return jsonify({"success": False, "error": "Failed to fetch report data"}), 500

    return jsonify(report_data)


@server.route('/api/inventory/add_stock', methods=['POST'])
@login_required
@roles_required('admin', 'superadmin')
def add_inventory_stock():
    try:
        # ✅ FIX: Save user data to variables first
        user_id = current_user.account_id
        username = current_user.username
        user_level = current_user.user_level
        
        data = request.get_json()
        
        # Extract form data
        category = data.get('category')
        prefix = data.get('prefix')
        start_num = data.get('start_num')
        count = data.get('count')
        
        # Validate required fields
        if not all([category, prefix, start_num, count]):
            db_conn.POST_action_log(username, user_level, 'Add Inventory Failed', 'Missing required fields', user_id)
            return jsonify({
                "success": False, 
                "error": "All fields are required"
            }), 400
        
        # Convert to integers
        try:
            start_num = int(start_num)
            count = int(count)
        except ValueError:
            return jsonify({
                "success": False, 
                "error": "Invalid number format"
            }), 400
        
        # Validate count
        if count <= 0:
            return jsonify({
                "success": False, 
                "error": "Count must be greater than 0"
            }), 400
        
        # Validate count isn't too large (performance protection)
        if count > 10000:
            return jsonify({
                "success": False,
                "error": "Cannot add more than 10,000 IDs at once"
            }), 400
        
        # Call the database function
        result = db_conn.add_inventory_ids(category, prefix, start_num, count)
        
        if result["success"]:
            db_conn.POST_action_log(username, user_level, 'Add Inventory', f'Added {result["added_count"]} {category} IDs starting from {prefix}{start_num}', user_id)
            
            response_data = {
                "success": True,
                "message": f"Successfully added {result['added_count']} ID(s) for {category} category",
                "details": result
            }
            
            # Add warning if there were duplicates
            if result['duplicate_count'] > 0:
                response_data["warning"] = f"Skipped {result['duplicate_count']} duplicate ID(s)"
                
            return jsonify(response_data)
        else:
            db_conn.POST_action_log(username, user_level, 'Add Inventory Failed', f'Failed to add {category} IDs: {result.get("error")}', user_id)
            return jsonify({
                "success": False,
                "error": result.get("error", "Failed to add IDs to inventory")
            }), 500
            
    except Exception as e:
        print(f"Error adding inventory stock: {e}")
        # ✅ FIX: Use the saved variables here too
        db_conn.POST_action_log(username, user_level, 'Add Inventory Error', f'Error: {str(e)}', user_id)
        return jsonify({
            "success": False,
            "error": "Internal server error"
        }), 500
# ============================================================
# 🔹 ASSIGN ID TO MEMBER - USING allocated_to FOR MEMBER NAMES
# ============================================================

@server.route('/api/inventory/assign_id', methods=['POST'])
@login_required
def assign_id_to_member():
    try:
        data = request.get_json()
        print(f"🔍 Assign ID Request Data: {data}")  # Debug log
        
        # Validate required fields
        required_fields = ['category', 'id_number', 'member_name']
        for field in required_fields:
            if field not in data or not data[field]:
                print(f"❌ Missing field: {field}")
                return jsonify({
                    'success': False,
                    'error': f'Missing required field: {field}'
                }), 400
        
        category = data['category']
        id_number = data['id_number']
        member_name = data['member_name']
        
        print(f"🔍 Processing assignment: {id_number} to {member_name} in category {category}")
        
        # Validate MAAB number format
        import re
        if not re.match(r'^(PC|PB|PS|PG|PP|PEP|S|SP)\d{7}$', id_number):
            print(f"❌ Invalid MAAB format: {id_number}")
            return jsonify({
                'success': False,
                'error': 'Invalid MAAB number format'
            }), 400
        
        # Check if ID exists and is available
        db_session = SessionLocal()
        
        try:
            # Check if the ID exists and is available
            inventory_item = db_session.query(models.Inventory).filter(
                models.Inventory.maab_no == id_number,
                models.Inventory.maab_category == category
            ).first()
            
            print(f"🔍 Found inventory item: {inventory_item}")
            
            if not inventory_item:
                return jsonify({
                    'success': False,
                    'error': f'ID {id_number} not found in category {category}'
                }), 400
            
            # Check if already used (used = 1 means used, 0 means available)
            if inventory_item.used == 1:
                return jsonify({
                    'success': False,
                    'error': f'ID {id_number} is already assigned to {inventory_item.allocated_to}'
                }), 400
            
            # Update the inventory item - use allocated_to for member name
            inventory_item.used = 1  # Set to used
            inventory_item.allocated_to = member_name  # Store member name here
            
            db_session.commit()
            
            print(f"✅ Successfully assigned {id_number} to {member_name}")
            
            # Log the action
            db_conn.POST_action_log(
                current_user.username, 
                current_user.user_level, 
                'Assign ID', 
                f'Assigned {id_number} to {member_name}', 
                current_user.account_id
            )
            
            return jsonify({
                'success': True,
                'message': f'ID {id_number} successfully assigned to {member_name}'
            })
            
        except Exception as e:
            db_session.rollback()
            print(f"❌ Database error in assign_id_to_member: {e}")
            import traceback
            traceback.print_exc()
            return jsonify({
                'success': False,
                'error': f'Database error: {str(e)}'
            }), 500
            
        finally:
            db_session.close()
            
    except Exception as e:
        print(f"❌ Error in assign_id_to_member route: {e}")
        import traceback
        traceback.print_exc()
        return jsonify({
            'success': False,
            'error': f'Internal server error: {str(e)}'
        }), 500

# ============================================================
# 🔹 GET AVAILABLE IDs FOR CATEGORY
# ============================================================

@server.route('/api/inventory/available_ids/<category>', methods=['GET'])
@login_required
def get_available_ids(category):
    try:
        count = request.args.get('count', 1, type=int)
        
        print(f"🔍 Getting {count} available IDs for category: {category}")
        
        db_session = SessionLocal()
        
        try:
            # Get available IDs for the category - used = 0 means available
            available_ids = db_session.query(models.Inventory).filter(
                models.Inventory.maab_category == category,
                models.Inventory.used == 0  # 0 = available, 1 = used
            ).limit(count).all()
            
            ids_list = [item.maab_no for item in available_ids]
            
            print(f"✅ Found {len(ids_list)} available IDs: {ids_list}")
            
            return jsonify({
                'success': True,
                'available_ids': ids_list,
                'count': len(ids_list)
            })
            
        except Exception as e:
            print(f"❌ Database error in get_available_ids: {e}")
            import traceback
            traceback.print_exc()
            return jsonify({
                'success': False,
                'error': 'Database error occurred'
            }), 500
            
        finally:
            db_session.close()
            
    except Exception as e:
        print(f"❌ Error in get_available_ids route: {e}")
        import traceback
        traceback.print_exc()
        return jsonify({
            'success': False,
            'error': 'Internal server error'
        }), 500
    
    # ============================================================
# 🔹 GET ASSIGNED IDs (For Verification)
# ============================================================

@server.route('/api/inventory/assigned_ids', methods=['GET'])
@login_required
def get_assigned_ids():
    try:
        db_session = SessionLocal()
        
        try:
            # Get assigned IDs (used = 1)
            assigned_ids = db_session.query(models.Inventory).filter(
                models.Inventory.used == 1
            ).all()
            
            result = []
            for item in assigned_ids:
                result.append({
                    'maab_no': item.maab_no,
                    'category': item.maab_category,
                    'allocated_to': item.allocated_to,
                    'remarks': item.remarks
                })
            
            return jsonify({
                'success': True,
                'assigned_ids': result,
                'count': len(result)
            })
            
        except Exception as e:
            print(f"❌ Database error in get_assigned_ids: {e}")
            return jsonify({
                'success': False,
                'error': 'Database error occurred'
            }), 500
            
        finally:
            db_session.close()
            
    except Exception as e:
        print(f"❌ Error in get_assigned_ids route: {e}")
        return jsonify({
            'success': False,
            'error': 'Internal server error'
        }), 500
    
    # ============================================================
# 🔹 TEST INVENTORY ASSIGNMENT
# ============================================================

@server.route('/api/debug/test_assignment', methods=['POST'])
@login_required
def test_assignment():
    """Test route to check if assignment works"""
    try:
        db_session = SessionLocal()
        
        # Get one available ID
        available_item = db_session.query(models.Inventory).filter(
            models.Inventory.used == 0
        ).first()
        
        if not available_item:
            return jsonify({'success': False, 'error': 'No available IDs found'})
        
        test_data = {
            'category': available_item.maab_category,
            'id_number': available_item.maab_no,
            'member_name': 'TEST MEMBER'
        }
        
        return jsonify({
            'success': True,
            'test_data': test_data,
            'message': 'Use this data to test assignment'
        })
        
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)})
    finally:
        db_session.close()
    
@server.route('/api/add_to_dispatch', methods=['PATCH'])
@login_required
@roles_required('admin', 'superadmin')
def add_to_dispatch():
    data = request.get_json()  # optional — for future if you need to pass something
    try:
        result = db_conn.add_to_dispatch()
        print('add_to_dispatch result:', result)
        if result:
            db_conn.POST_action_log(current_user.username, current_user.user_level, 'Add to Dispatch', f'Added {result} entries to dispatch', current_user.account_id)
            return jsonify({"success": True, "added_to_dispatch_count": result})
        else:
            return jsonify({"success": False, "error": "No entries to add to dispatch"}), 500
    except Exception as e:
        return jsonify({"success": False, "error": str(e)}), 500

                        

# FIXED EXPORT DISPATCH ROUTE - ONLY ONE VERSION
@server.route('/api/export_dispatch', methods=['POST'])
@login_required
@roles_required('admin', 'superadmin')
def export_dispatch():
    try:
        data = request.get_json()
        if not data:
            db_conn.POST_action_log(current_user.username, current_user.user_level, 'Export Data Failed', 'No JSON data provided', current_user.account_id)
            return jsonify({"success": False, "error": "No JSON data provided"}), 400
            
        selected_rows = data.get('selected_rows', [])
        
        if not selected_rows:
            db_conn.POST_action_log(current_user.username, current_user.user_level, 'Export Data Failed', 'No rows selected', current_user.account_id)
            return jsonify({"success": False, "error": "No rows selected"}), 400

        # Create DataFrame from selected rows
        df_data = []
        for i, row in enumerate(selected_rows, 1):
            df_data.append({
                'No.': i,
                'Name': row.get('name', ''),
                'Category': row.get('category', ''),
                'Effectivity': row.get('effectivity', ''),
                'Birthday': row.get('birthday', ''),
                'Location': row.get('location', '')
            })

        df = pd.DataFrame(df_data)

        # Define the export folder path
        export_folder = os.path.join(os.path.dirname(__file__), 'exports', 'dispatch_reports')
        
        # Create folder if it doesn't exist
        os.makedirs(export_folder, exist_ok=True)

        # Generate filename with timestamp
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        filename = f"Dispatch_Report_{timestamp}.xlsx"
        file_path = os.path.join(export_folder, filename)

        # Create Excel writer with styling
        with pd.ExcelWriter(file_path, engine='xlsxwriter') as writer:
            # Write the data
            df.to_excel(writer, sheet_name='Dispatch Report', index=False, startrow=2)
            
            # Get workbook and worksheet
            workbook = writer.book
            worksheet = writer.sheets['Dispatch Report']
            
            # Add title
            title_format = workbook.add_format({
                'bold': True,
                'size': 16,
                'align': 'center',
                'valign': 'vcenter'
            })
            
            worksheet.merge_range('A1:F1', 'DISPATCH REPORT', title_format)
            
            # Header format
            header_format = workbook.add_format({
                'bold': True,
                'align': 'center',
                'valign': 'vcenter',
                'bg_color': '#D3D3D3',
                'border': 1
            })
            
            # Apply header format
            for col_num, value in enumerate(df.columns.values):
                worksheet.write(2, col_num, value, header_format)
            
            # Set column widths
            worksheet.set_column('A:A', 5)   # No.
            worksheet.set_column('B:B', 30)  # Name
            worksheet.set_column('C:C', 15)  # Category
            worksheet.set_column('D:D', 12)  # Effectivity
            worksheet.set_column('E:E', 12)  # Birthday
            worksheet.set_column('F:F', 25)  # Location
            
            # Center the number column
            number_format = workbook.add_format({'align': 'center'})
            worksheet.set_column('A:A', 5, number_format)

        db_conn.POST_action_log(current_user.username, current_user.user_level, 'Export Data', f'Exported dispatch report with {len(selected_rows)} entries', current_user.account_id)
        return jsonify({
            "success": True, 
            "message": "File saved successfully",
            "filename": filename,
            "file_path": file_path
        })

    except Exception as e:
        print(f"Export error: {e}")
        db_conn.POST_action_log(current_user.username, current_user.user_level, 'Export Data Error', f'Error: {str(e)}', current_user.account_id)
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
    claim_records = list(reversed(claim_records))  # reverse the list
    #print('flask_server: claim_records', claim_records)
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
    # ACTIVE accounts should only be 'approved' status (EXCLUDE archived)
    active_accounts = db_conn.get_accounts(status=['approved'])
    # PENDING accounts
    pending_accounts = db_conn.get_accounts(status=['pending'])

    return jsonify({
        "active": [acc.to_dict() for acc in active_accounts],
        "pending": [acc.to_dict() for acc in pending_accounts]
    })

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
        db_conn.POST_action_log(current_user.username, current_user.user_level, 'Approve Accounts', f'Approved {len(ids)} account(s)', current_user.account_id)

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
    try:
        data = request.get_json()
        ids = data.get('ids', [])
        
        print(f"🔍 RESET PASSWORD API CALLED")
        print(f"📋 Account IDs to reset: {ids}")
        
        if not ids:
            db_conn.POST_action_log(current_user.username, current_user.user_level, 'Reset Password Failed', 'No account IDs provided', current_user.account_id)
            return jsonify({"success": False, "error": "No account IDs provided"}), 400

        success_count = 0
        failed_ids = []
        
        for acc_id in ids:
            print(f"🔄 Processing account ID: {acc_id}")
            
            success = db_conn.reset_account(acc_id)
            
            if success:
                success_count += 1
                print(f"✅ Successfully reset password for account {acc_id}")
            else:
                failed_ids.append(acc_id)
                print(f"❌ Failed to reset password for account {acc_id}")
                db_conn.POST_action_log(current_user.username, current_user.user_level, 'Reset Password Failed', f'Failed to reset password for account ID {acc_id}', current_user.account_id)
        
        print(f"📊 Reset summary: {success_count} successful, {len(failed_ids)} failed")
        
        if success_count > 0:
            db_conn.POST_action_log(current_user.username, current_user.user_level, 'Reset Passwords', f'Reset passwords for {success_count} account(s)', current_user.account_id)
            response = {
                "success": True, 
                "reset_count": success_count,
                "message": f"Passwords reset for {success_count} account(s)!"
            }
            if failed_ids:

                response["warning"] = f"Failed to reset {len(failed_ids)} account(s)"
            return jsonify(response)
        else:
            db_conn.POST_action_log(current_user.username, current_user.user_level, 'Reset Password Failed', f'Failed to reset passwords for all {len(ids)} account(s)', current_user.account_id)
            return jsonify({
                "success": False, 
                "error": f"Failed to reset passwords for all {len(ids)} account(s)"
            }), 500
            
    except Exception as e:
        db_conn.POST_action_log(current_user.username, current_user.user_level, 'Reset Password Error', f'Error: {str(e)}', current_user.account_id)
        print(f"❌ ERROR in reset_account route: {e}")
        import traceback
        traceback.print_exc()
        return jsonify({
            "success": False, 
            "error": f"Internal server error: {str(e)}"
        }), 500
    
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
            db_conn.POST_action_log(current_user.username, current_user.user_level, 'Update User Level', f'Updated user level to {user_level} for account {id}', current_user.account_id)
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
            db_conn.POST_action_log(current_user.username, current_user.user_level, 'Update Office Location', f'Updated office location to {location} for account {id}', current_user.account_id)
            return jsonify({"success": True})
        else:
            return jsonify({"success": False, "error": "Failed to update office location"}), 500
        
    except Exception as e:
        print(f"Error updating office location: {e}")
        return jsonify({"success": False, "error": str(e)}), 500
# UPDATE YOUR FLASK ROUTES

@server.route('/create_acc_submit', methods=['POST'])
@login_required
@roles_required('admin', 'superadmin')
def create_account_submit():
    
    def username_exists(username):
        """Check if username already exists in database using SQLAlchemy"""
        db_session = db_conn.SessionLocal()
        try:
            existing_user = db_session.query(db_conn.models.Accounts).filter(
                db_conn.models.Accounts.username == username
            ).first()
            return existing_user is not None
        finally:
            db_session.close()

    def email_exists(email):
        """Check if email already exists in database using SQLAlchemy"""
        if not email:  # Email is optional
            return False
            
        db_session = db_conn.SessionLocal()
        try:
            existing_email = db_session.query(db_conn.models.Accounts).filter(
                db_conn.models.Accounts.email == email
            ).first()
            return existing_email is not None
        finally:
            db_session.close()

    try:
        data = request.get_json()
        print("=== CREATE ACCOUNT DEBUG ===")
        print("Received data:", data)
        
        # Validate required fields - UPDATED: removed password from required fields
        required_fields = ['username', 'fname', 'lname', 'contact_no', 'branch']
        missing_fields = [field for field in required_fields if not data.get(field)]
        if missing_fields:
            print(f"Missing fields: {missing_fields}")
            # ADD FAILED LOG:
            db_conn.POST_action_log(current_user.username, current_user.user_level, 'Create Account Failed', f'Missing required fields: {", ".join(missing_fields)}', current_user.account_id)
            return jsonify({
                "success": False, 
                "message": f"Missing required fields: {', '.join(missing_fields)}"
            }), 400

        # Validate birthdate - NEW: birthdate is now required
        bdate = data.get('bdate')
        if not bdate:
            print("Birthdate is missing")
            # ADD FAILED LOG:
            db_conn.POST_action_log(current_user.username, current_user.user_level, 'Create Account Failed', 'Birthdate is required', current_user.account_id)
            return jsonify({
                "success": False, 
                "message": "Birthdate is required"
            }), 400

        user = data.get('username')
        password = data.get('password')  # This is now auto-generated from frontend
        email = data.get('email')

        fname = data.get('fname').upper()
        mname = data.get('mname', '').upper()
        lname = data.get('lname').upper()
        suffix = data.get('suffix', 'NA')

        contact = data.get('contact_no')
        acct_created = date.today().strftime("%Y-%m-%d")
        branch = data.get('branch')

        print(f"Processing account creation for: {fname} {lname} ({user})")
        print(f"Auto-generated password: {password}")

        # Check if username already exists
        print(f"Checking if username exists: {user}")
        if username_exists(user):
            print(f"Username already exists: {user}")
            # ADD FAILED LOG:
            db_conn.POST_action_log(current_user.username, current_user.user_level, 'Create Account Failed', f'Username already exists: {user}', current_user.account_id)
            return jsonify({
                "success": False, 
                "message": "Username already exists. Please choose a different username."
            }), 400

        # Check if email already exists (if email provided)
        if email:
            print(f"Checking if email exists: {email}")
            if email_exists(email):
                print(f"Email already exists: {email}")
                # ADD FAILED LOG:
                db_conn.POST_action_log(current_user.username, current_user.user_level, 'Create Account Failed', f'Email already exists: {email}', current_user.account_id)
                return jsonify({
                    "success": False, 
                    "message": "Email address already exists. Please use a different email."
                }), 400

        # Create account using db_conn
        print("Calling db_conn.create_account...")
        create_new_acc = db_conn.create_account(
            user=user, 
            password=password, 
            email=email, 
            fname=fname, 
            mname=mname, 
            lname=lname,
            suffix=suffix, 
            bdate=bdate, 
            contact=contact, 
            acct_created=acct_created, 
            branch=branch
        )
        
        print(f"db_conn.create_account returned: {create_new_acc}")
    
        if create_new_acc is True:
            print("Account creation successful!")
            # ADD SUCCESS LOG:
            db_conn.POST_action_log(current_user.username, current_user.user_level, 'Create Account', f'Created account for {fname} {lname} (Username: {user})', current_user.account_id)
            return jsonify({
                "success": True,
                "message": "Account created successfully!"
            })
        else:
            print(f"Account creation failed with: {create_new_acc}")
            # ADD FAILED LOG:
            db_conn.POST_action_log(current_user.username, current_user.user_level, 'Create Account Failed', f'Database error: {create_new_acc}', current_user.account_id)
            return jsonify({
                "success": False, 
                "message": f"Account creation failed: {create_new_acc}"
            }), 500

    except Exception as e:
        print(f"Error creating account: {str(e)}")
        import traceback
        print(f"Traceback: {traceback.format_exc()}")
        # ADD FAILED LOG FOR EXCEPTION:
        db_conn.POST_action_log(current_user.username, current_user.user_level, 'Create Account Error', f'Exception: {str(e)}', current_user.account_id)
        return jsonify({
            "success": False, 
            "message": "An unexpected error occurred. Please try again."
        }), 500
    
@server.route('/api/accounts/archive', methods=['PATCH'])
@login_required
@roles_required('admin', 'superadmin')
def archive_account():
    try:
        data = request.get_json()
        ids = data.get('ids', [])
        
        print(f"🔍 ARCHIVE REQUEST - IDs: {ids}")
        
        if not ids:
            return jsonify({"success": False, "error": "No account IDs provided"}), 400

        # Use SINGLE session for ALL operations
        db_session = SessionLocal()
        success_count = 0
        failed_ids = []
        
        try:
            # BULK UPDATE - archive all accounts in one query
            result = db_session.query(models.Accounts).filter(
                models.Accounts.account_id.in_(ids)
            ).update({
                models.Accounts.acct_status: 'archived'
            }, synchronize_session=False)
            
            db_session.commit()
            success_count = result
            
            print(f"✅ Successfully archived {success_count} accounts in one operation")
            db_conn.POST_action_log(current_user.username, current_user.user_level, 'Archive Accounts', f'Archived {success_count} account(s)', current_user.account_id)
            
            # Log the bulk action
            if success_count > 0:
                try:
                    archiver = db_session.query(models.Accounts).filter(
                        models.Accounts.account_id == current_user.account_id
                    ).first()
                    
                    if archiver:
                        db_conn.POST_action_log(
                            archiver.username,
                            archiver.user_level,
                            "Bulk Archive Accounts",
                            f"Archived {success_count} account(s): {ids}",
                            current_user.account_id
                        )
                except Exception as log_error:
                    print(f"⚠️ Logging failed but archive succeeded: {log_error}")
            
        except Exception as e:
            db_session.rollback()
            raise e
        finally:
            db_session.close()
        
        print(f"📊 Archive summary: {success_count}/{len(ids)} successful")
        
        if success_count > 0:
            return jsonify({"success": True, "archived_count": success_count})
        else:
            return jsonify({"success": False, "error": "Failed to archive any accounts"}), 500
            
    except Exception as e:
        print(f"❌ Error in archive_account: {e}")
        return jsonify({"success": False, "error": str(e)}), 500
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