import bcrypt
from pathlib import Path
from datetime import datetime as dt


def hash_password(password=''):
    salt = bcrypt.gensalt()

    hashed_pass = bcrypt.hashpw(password.encode('utf-8'), salt)

    return hashed_pass


def check_password(input_password, stored_hashed_password):
    converted_to_byte_pass = stored_hashed_password.encode('utf-8')

    return bcrypt.checkpw(input_password.encode('utf-8'), converted_to_byte_pass)


def action_log(action=None, desc=None):
    """ for logging actions """
    conn = db_conn.db_conn()
    now = dt.now()
    current_date_time = now.strftime('%Y-%m-%d %H:%M:%S')

    with conn.cursor() as cursor:
        cursor.execute('INSERT INTO audit_trails VALUES (%s, %s, %s, %s, %s, %s)',
                       (None, current_date_time, current_user, current_user_lvl, action, desc))
        conn.commit()


if __name__ == '__main__':
    hash = hash_password('josh123')
    print(hash)
