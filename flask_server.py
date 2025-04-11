from flask import Flask, request, render_template, redirect, url_for, flash
from py_scripts import db_conn, tools
from datetime import date
import os

server = Flask(__name__)
server.secret_key = os.urandom(24)

# <------------ NAVIGATIONS ------------>


@server.route('/')
def landing_page():
    return render_template('index.html')


@server.route('/create_account')
def create_acc():
    return render_template('create_account.html')


@server.route('/forgot_password')
def forgot_password():
    return render_template('forgot_password.html')


@server.route('/profile')
def profile():
    return render_template('profile.html')


# TODO fix the home being accessible without logging in
@server.route('/home')
def home():
    return render_template('dashboard.html')


@server.route('/members')
def members_page():
    return render_template('members.html')


@server.route('/declaration')
def declaration_page():
    return render_template('declaration.html')


@server.route('/inventory')
def inventory():
    return render_template('inventory.html')


@server.route('/claims')
def claims():
    return render_template('claims.html')


@server.route('/bud_v_exp')
def bud_v_exp():
    return render_template('bud_v_exp.html')


@server.route('/trg_v_act')
def trg_v_act():
    return render_template('trg_v_act.html')


@server.route('/per_district')
def per_district():
    return render_template('per_district.html')


@server.route('/audit_trails')
def audit_trails():
    return render_template('audit_trails.html')


@server.route('/accounts')
def show_user_accounts():
    active_accounts = db_conn.get_user_accounts(status=['approved', 'archived', 'declined'])
    pending_accounts = db_conn.get_user_accounts(status=['pending'])

    return render_template('accounts.html', active_accounts=active_accounts, pending_accounts=pending_accounts)


@server.route('/settings')
def settings():
    return render_template('settings.html')


# <------------ NAVIGATIONS ------------>


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


@server.route('/reset_pass_email', methods=['POST'])
def reset_pass_email():
    return render_template('members.html') #reset pass next page


@server.route('/login', methods=['POST'])
def login():
    username = request.form.get("username")
    password = request.form.get("password")

    sign_in = db_conn.sign_in(username, password)
    
    if sign_in == 'success':
        return redirect(url_for('home'))  # Redirect to home page on success
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


if __name__ == '__main__':
    server.run(debug=True, use_reloader=True)
    

