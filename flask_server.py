from flask import Flask, request, render_template, jsonify, redirect, url_for
from py_scripts import db_conn

server = Flask(__name__)


@server.route('/')
def landing_page():
    return render_template('index.html')


@server.route('/index', methods=['POST'])
def login():
    username = request.form.get("username")
    password = request.form.get("password")

    sign_in = db_conn.sign_in(username, password)
    
    if sign_in == 'success':
        return redirect(url_for('home'))  # Redirect to home page on success
    else:
        return '''
        <script>
            alert("Invalid username or password! Try again.");
            window.location.href = "/";
        </script>
        '''  # Shows an alert and redirects back to login

@server.route('/home')
def home():
    return render_template('home.html')

@server.route('/members')
def members():
    return render_template('members.html')

@server.route('/create_account')
def create_account():
    return render_template('create_account.html')

server.secret_key = 'ifgms'  

# Route to render the Forgot Password page
@server.route('/forgot_password', methods=['GET', 'POST'])
def forgot_password():
    if request.method == 'POST':
        email = request.form['email']
        
        # Check if email exists in the database
        from db_conn import conn_init
        conn = conn_init()
        cursor = conn.cursor()
        cursor.execute("SELECT email FROM accounts WHERE email = %s", (email,))
        user = cursor.fetchone()

        if user:
            otp = generate_otp()  # Generate OTP
            save_otp(email, otp)  # Save OTP to the database
            send_otp_email(email, otp)  # Send OTP to the user's email

            # Store the email in the session to verify OTP later
            session['email'] = email

            flash('OTP sent to your email. Please check your inbox.', 'info')
            return redirect(url_for('verify_otp'))  # Redirect to OTP verification page
        else:
            flash('Email not found in our records.', 'error')
            return redirect(url_for('forgot_password'))

    return render_template('forgot_password.html')

# Route to render OTP verification page
@server.route('/verify_otp', methods=['GET', 'POST'])
def verify_otp():
    if request.method == 'POST':
        otp = request.form['otp']
        email = session.get('email')

        # Verify the OTP
        result = verify_otp(email, otp)

        if result == "success":
            flash('OTP verified! Please reset your password.', 'success')
            return redirect(url_for('reset_password'))  # Redirect to reset password page
        elif result == "expired":
            flash('OTP expired. Please request a new one.', 'error')
            return redirect(url_for('forgot_password'))
        else:
            flash('Invalid OTP. Please try again.', 'error')
            return redirect(url_for('verify_otp'))

    return render_template('verify_otp.html')

# Route to render Reset Password form
@server.route('/reset_password', methods=['GET', 'POST'])
def reset_password():
    if request.method == 'POST':
        email = session.get('email')
        new_password = request.form['new_password']

        # Update the password in the database
        update_password(email, new_password)
        flash('Your password has been reset successfully!', 'success')
        session.pop('email', None)  # Clear the session
        return redirect(url_for('login'))  # Redirect to login page after resetting password

    return render_template('reset_password.html')

if __name__ == '__main__':
    server.run(debug=True, use_reloader=True)
    
