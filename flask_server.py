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

if __name__ == '__main__':
    server.run(debug=True, use_reloader=True)
    
