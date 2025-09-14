import bcrypt
from pathlib import Path
from datetime import datetime as dt
from random import randint

def hash_password(password=''):
    salt = bcrypt.gensalt()

    hashed_pass = bcrypt.hashpw(password.encode('utf-8'), salt)

    return hashed_pass

def check_password(input_password, stored_hashed_password):
    converted_to_byte_pass = stored_hashed_password.encode('utf-8')

    return bcrypt.checkpw(input_password.encode('utf-8'), converted_to_byte_pass)

def generate_otp():
    """Generate a random 6-digit OTP."""
    return str(randint(100000, 999999))




if __name__ == '__main__':
    pass
