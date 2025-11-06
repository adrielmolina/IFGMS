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

def get_district_from_municipality(municipality_name):
    """Return the district number based on the municipality name."""
    districts = {
        '1': {'Cavite City', 'Kawit', 'Noveleta', 'Rosario'},
        '2': {'Bacoor'},
        '3': {'Imus'},
        '4': {'Dasmariñas'},
        '5': {'Carmona', 'General Mariano Alvarez (GMA)', 'Silang'},
        '6': {'General Trias'},
        '7': {'Amadeo', 'Indang', 'Tanza', 'Trece Martires'},
        '8': {'Alfonso', 'Gen. Emilio Aguinaldo (Bailen)', 'Magallanes', 'Maragondon', 'Mendez', 'Naic', 'Tagaytay City', 'Ternate'},
    }
    
    for district, municipalities in districts.items():
        if municipality_name in municipalities:
            return int(district)
    return 'Unknown District/Invalid Input'  # if not found

if __name__ == '__main__':  # Example usage
    pass