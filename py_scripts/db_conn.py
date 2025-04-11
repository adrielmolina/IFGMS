import os
from dotenv import load_dotenv
from pathlib import Path
from sqlalchemy import create_engine, text
from sqlalchemy.exc import OperationalError
from sqlalchemy.orm import sessionmaker, Session
import cryptography
from datetime import date
from py_scripts import tools
from py_scripts import models

current_dir = Path(__file__).parent
parent_dir = current_dir.parent
env_loc = parent_dir/'creds.env'

print("ENV File Location:", env_loc)

load_dotenv(env_loc)

SQL_HOST = os.getenv('SQL_HOST')
SQL_USER = os.getenv('SQL_USER')
SQL_PASS = os.getenv('SQL_PASS')
SQL_DB = os.getenv('SQL_DB')
print(f'SQL CONNECTION DEBUG\nHost={SQL_HOST}\nUser={SQL_USER}\nPass={SQL_PASS}\nDB={SQL_DB}')

def conn_init():
    try:
        db_url = f"mysql+pymysql://{SQL_USER}:{SQL_PASS}@{SQL_HOST}/{SQL_DB}"
        engine = create_engine(db_url)
        conn = engine.connect()

        print('Database Connection Success')
        return conn
    except OperationalError:
        try:
            print('Database doesn\'t exist. Creating one...')
            engine = create_engine(f"mysql+pymysql://{SQL_USER}:{SQL_PASS}@{SQL_HOST}")
            db_init_script = Path(parent_dir/'sql/ifgms_db.sql')
            init_val_script = Path(parent_dir/'sql/init_data.sql')

            with engine.connect() as conn:
                conn.execute(text(f"CREATE DATABASE {SQL_DB};"))
                print(f"Database '{SQL_DB}' created successfully!")

                # Function to execute SQL scripts
                def execute_sql_script(script_path, engine):
                    if script_path.exists():
                        with open(script_path, "r") as file:
                            sql_script = file.read()

                        print(f"Executing {script_path.name}...")
                        with engine.connect() as conn:
                            for statement in sql_script.split(";"):  # Split script into individual statements
                                statement = statement.strip()
                                if statement:  # Ignore empty statements
                                    conn.execute(text(statement))
                            conn.commit()
                        print(f"{script_path.name} executed successfully!")
                    else:
                        print(f"SQL script '{script_path}' not found!")

                # Reconnect with the new database
                db_url_with_db = f"mysql+pymysql://{SQL_USER}:{SQL_PASS}@{SQL_HOST}/{SQL_DB}"
                engine_with_db = create_engine(db_url_with_db)

                # Execute both SQL scripts
                execute_sql_script(db_init_script, engine_with_db)
                execute_sql_script(init_val_script, engine_with_db)

                # Final connection
                conn = engine_with_db.connect()
                print("Database connection successful!")
                return conn
        except Exception as e:
            print(f"Error: {e}")


def create_account(**kwargs):
    """ arguments must be the same name as in the sql query """
    conn = conn_init()

    try:
        with conn.begin():
            query = text(f"INSERT INTO accounts VALUES"
                         " (NULL, :user, :hashed_pass, :email, :fname, :mname, :lname, :suffix,"
                         " :bdate, :contact, :acct_created, :branch, DEFAULT, DEFAULT, NULL)")
            conn.execute(query, kwargs)
            conn.commit()
    except Exception as e:
        print(f"Error: {e}")


def sign_in(username=None, password=None):
    conn = conn_init()
    Session = sessionmaker(bind=conn)

    with Session() as session:
        query = text("SELECT password, acct_status FROM accounts WHERE username = :username AND (acct_status = 'approved' OR acct_status = 'pending')")
        result = session.execute(query, {"username": username}).fetchone()

    if result and tools.check_password(password, result[0]) and result[1] == 'approved':
        return 'success'
    elif result and tools.check_password(password, result[0]) and result[1] == 'pending':
        return 'pending'
    else:
        return 'fail'

def get_user_accounts(status):
    conn = conn_init()

    with conn:
        query = text("SELECT * FROM accounts WHERE acct_status IN :status")
        result = conn.execute(query, {'status': tuple(status)})
        accounts = result.fetchall()
        return accounts

def account_action(selected_ids, action):    
    Session = sessionmaker(bind=conn_init())
    session = Session()
    
    try:
        affected_accounts = session.query(models.Accounts).filter(models.Accounts.account_id.in_(selected_ids)).all()
        
        if action == 'create':
            pass
        elif action == 'archive':
            for account in affected_accounts:
                account.acct_status = 'archived'
                session.add(account)
        elif action == 'reset':
            for account in affected_accounts:          
                if account.birth_date:
                    bdate = str(account.birth_date).replace('-', '')
                else:
                    bdate = '00000000'
                initials = (account.first_name[:1] + account.middle_name[:1] + account.last_name[:1]).lower().strip()
       
                reset_pass = bdate + initials
                print(reset_pass)
                hashed_pass = tools.hash_password(reset_pass)
                    
                account.password = hashed_pass
                session.add(account)            
        elif action == 'approve':
            for account in affected_accounts:
                account.acct_status = 'approved'
                session.add(account)
        elif action == 'decline':
            for account in affected_accounts:
                account.acct_status = 'declined'
                session.add(account)
            
            
            
        session.commit()
    except Exception as e:
        session.rollback()
        raise e
    finally:
        session.close
    return None
    
    




'''
def sign_in(empid_input, password_input):
    # check if emp id and pass matches in db
    conn = db_conn()
    with conn.cursor() as cursor:
        query = 'SELECT * FROM accounts WHERE employee_id = %s'
        cursor.execute(query, (empid_input, ))
        result = cursor.fetchone()

        if result is not None:
            # debug result print
            userlvl, empfname, emplname, emp_pass, emp_id = result[2], result[3], result[4], result[5], result[1]
            print(
                __name__,
                f' - User Level: {userlvl},',
                f'Employee First Name: {empfname.upper()},',
                f'Employee Last Name: {emplname.upper()}'
            )
            gen_fun.current_id = result[1]  # * store the id of current user
            match = gen_fun.check_password(password_input, emp_pass)
            if match:
                return userlvl, empfname, emplname, emp_id
            else:
                return None
        else:
            return None
'''

def get_total_donations_for_today():
    """Fetches the total number of donations for today from the inventory table"""
    connection = db_conn()
    if connection:
        cursor = connection.cursor()
        query = """
            SELECT COUNT(*) 
            FROM inventory 
            WHERE DATE(collection_date) = CURDATE()
        """
        cursor.execute(query)
        result = cursor.fetchone()
        cursor.close()
        connection.close()
        return result[0] if result else 0
    return 0

def get_total_released_for_today():
    """Fetches the total number of blood bags released for today"""
    connection = db_conn()
    if connection:
        cursor = connection.cursor()
        query = """
            SELECT COUNT(*) 
            FROM inventory 
            WHERE DATE(release_date) = CURDATE()
        """
        cursor.execute(query)
        result = cursor.fetchone()
        cursor.close()
        connection.close()
        return result[0] if result else 0
    return 0


def get_nearly_expired_blood_bags():
    connection = db_conn()
    cursor = connection.cursor()

    # SQL query to get the collection date of the blood bags
    query = """
    SELECT blood_bag_no, blood_type, collection_date
    FROM inventory
    WHERE status = 'available'
    """
    cursor.execute(query)
    blood_bags = cursor.fetchall()

    nearly_expired_bags = []

    # Calculate the expiration and nearly expiry dates
    for bag in blood_bags:
        blood_bag_no, blood_type, collection_date = bag  # collection_date is already a datetime.date object
        expiration_date = collection_date + dt.timedelta(days=35)  # Add 35 days to get expiration
        nearly_expiry_date = expiration_date - dt.timedelta(days=7)  # Subtract 7 days for nearly expiry

        if nearly_expiry_date <= dt.datetime.now().date():  # Compare with today's date
            nearly_expired_bags.append(f"{nearly_expiry_date.strftime('%m-%d-%y')}  {blood_bag_no} {blood_type}")

    connection.close()
    return nearly_expired_bags


def transaction_insert(*args):
    pass
    # for transactions 


def get_user_details(emp_id):
    print(f"Getting details for emp_id: {emp_id}")  # Debugging line
    conn = db_conn()
    try:
        with conn.cursor() as cursor:
            query = "SELECT fname, lname, email FROM accounts WHERE employee_id = %s"
            cursor.execute(query, emp_id)
            result = cursor.fetchone()
            return result
    finally:
        conn.close()

if __name__ == '__main__':
    conn_init()
