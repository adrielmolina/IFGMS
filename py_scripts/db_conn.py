import os
from dotenv import load_dotenv
from pathlib import Path

current_dir = Path(__file__).parent
parent_dir = current_dir.parent
env_loc = parent_dir/'db_login.env'

print("env file locatoin:", env_loc)

load_dotenv(env_loc)

SQL_HOST = os.getenv('SQL_HOST')
SQL_USER = os.getenv('SQL_USER')
SQL_PASS = os.getenv('SQL_PASS')
SQL_DB = os.getenv('SQL_DB')
print(f'SQL CONNECTION DEBUG\nHost={SQL_HOST}\nUser={SQL_USER}\nPass={SQL_PASS}\nDB={SQL_DB}')


# todo leave only one sample data
def db_conn():
    try:
        conn = pymysql.connect(
            host=SQL_HOST,
            user=SQL_USER,
            password=SQL_PASS,
            database=SQL_DB
        )
        return conn
    except:
        print('Database doesn\'t exist. Creating one...' )
        conn = pymysql.connect(
            host=SQL_HOST,
            user=SQL_USER,
            password=SQL_PASS
        )
        try:
            with conn.cursor() as cursor:
                cursor.execute('CREATE DATABASE IF NOT EXISTS blood_well_sys;')
                print('Database successfully created')
                conn.commit()
                db_init()
        except pymysql.err.OperationalError as e:
            print('Error:', e)
        finally:
            conn.close()

        conn = pymysql.connect(
            host=SQL_HOST,
            user=SQL_USER,
            password=SQL_PASS,
            database=SQL_DB
        )
        return conn

def db_test_connection():
    """ use this for testing connection """
    conn = db_conn()
    try:
        # test connection
        with conn.cursor() as cursor:
            cursor.execute('SELECT VERSION()')
            version = cursor.fetchone()
            print('Database Version:', version[0])
            print('SQL successfully connected')

            cursor.execute('SELECT * FROM accounts')


    except pymysql.err.OperationalError as e:
        print('Database connection error:', e)
    finally:
        conn.close()

def db_init():
    """ used to initialize db and tables on first run """
    conn = db_conn()
    with conn.cursor() as cursor:
        # * accounts table
        cursor.execute('''CREATE TABLE IF NOT EXISTS `accounts` (
                        `acc_no` INT(10) NOT NULL AUTO_INCREMENT,
                        `employee_id` INT(10) NOT NULL DEFAULT 0,
                        `user_level` VARCHAR(100) NOT NULL DEFAULT 'user',
                        `fname` VARCHAR(100) NOT NULL DEFAULT '0',
                        `lname` VARCHAR(100) NOT NULL DEFAULT '0',
                        `acc_pass` VARCHAR(100) NOT NULL DEFAULT '0',
                        `email` VARCHAR(100) NOT NULL DEFAULT '0',
                        `acc_created` DATE NOT NULL DEFAULT '2024-01-01',
                        PRIMARY KEY (acc_no)
                        );
        ''')

        cursor.execute('''CREATE TABLE IF NOT EXISTS `archived_accounts` (
                                `acc_no` INT(10) NOT NULL AUTO_INCREMENT,
                                `employee_id` INT(10) NOT NULL DEFAULT 0,
                                `user_level` VARCHAR(100) NOT NULL DEFAULT 'user',
                                `fname` VARCHAR(100) NOT NULL DEFAULT '0',
                                `lname` VARCHAR(100) NOT NULL DEFAULT '0',
                                `acc_pass` VARCHAR(100) NOT NULL DEFAULT '0',
                                `email` VARCHAR(100) NOT NULL DEFAULT '0',
                                `acc_created` DATE NOT NULL DEFAULT '2024-01-01',
                                PRIMARY KEY (acc_no)
                                );
        ''')

        # * placeholder accounts
        cursor.execute('''INSERT INTO accounts
                        VALUES 
                                (NULL, 2024000, 'admin','adriel', 'panganiban', '$2b$12$qrtAbrmYxbctNAP5KKno9.S6KDzFvX8jU4vHCmASBV47TULFceFzG', 'adrielmolina99@gmail.com', '2024-12-30'),
                                (NULL, 2024001, 'admin','abegail', 'montejo', '$2b$12$O.LLRZ1Pwhr7g9uyJFsj3.JII0lXHPHU8SjL3HNtt5FCfKhxCUkNy', 'abysadaba@gmail.com', '2024-10-21'),
                                (NULL, 2024002, 'user','jb', 'custodio', '$2b$12$X2j.eiLysB6TTC0IfUNoseXyBVw6unCDkXsdjgyc1h1Q2sOKV2//O', 'jb@gmail.com', '2024-06-19'),
                                (NULL, 2024003, 'user','louis', 'sanorjo', '$2b$12$F3muIFxCwba2Jv5brPrGr.5jk6DSzDFVXYi3NQAJGGKsNED9Ycjki', 'louis@gmail.com', '2024-03-31'),
                                (NULL, 2024004, 'user','josh', 'crisostomo', '$2b$12$sqDafxRaqp6K.536TuQiQONAWgVNH4U9bbl02nxTF.d5tdTODVT12', 'josh@gmail.com', '2024-11-26');
        ''')

        # * reservations table
        cursor.execute('''CREATE TABLE IF NOT EXISTS `reservations` (
                        `rsrv_no` INT(10) NOT NULL AUTO_INCREMENT,
                        `name` VARCHAR(100) NOT NULL,
                        `contact_no` VARCHAR(100) NOT NULL,
                        `email` VARCHAR(100) NOT NULL,
                        `rsrv_date` DATE,
                        PRIMARY KEY (`rsrv_no`)
                        );
        ''')

        # * void reservations table
        cursor.execute('''CREATE TABLE IF NOT EXISTS `void_reservations` (
                                `rsrv_no` INT(10) NOT NULL AUTO_INCREMENT,
                                `name` VARCHAR(100) NOT NULL,
                                `contact_no` VARCHAR(100) NOT NULL,
                                `email` VARCHAR(100) NOT NULL,
                                `rsrv_date` DATE,
                                PRIMARY KEY (`rsrv_no`)
                                );
        ''')

        # * inventory table
        cursor.execute('''CREATE TABLE IF NOT EXISTS inventory (
                                blood_unit_id INT(10) NOT NULL AUTO_INCREMENT,
                                blood_bag_no VARCHAR(15), 
                                blood_type VARCHAR(10) NOT NULL,
                                collection_date DATE NOT NULL,
                                release_date DATE,
                                status VARCHAR(50) NOT NULL,
                                handling_staff VARCHAR(100) NOT NULL,
                                PRIMARY KEY (blood_unit_id)
                                );
        ''')

        # * inventory archive table
        cursor.execute('''CREATE TABLE IF NOT EXISTS archived_inventory (
                                        blood_unit_id INT(10) NOT NULL AUTO_INCREMENT,
                                        blood_bag_no VARCHAR(15), 
                                        blood_type VARCHAR(10) NOT NULL,
                                        collection_date DATE NOT NULL,
                                        release_date DATE,
                                        status VARCHAR(50) NOT NULL,
                                        handling_staff VARCHAR(100) NOT NULL,
                                        PRIMARY KEY (blood_unit_id)
                                        );
        ''')

        # * inventory placeholder values
        cursor.executemany('''
            INSERT INTO inventory (blood_bag_no, blood_type, collection_date, release_date, status, handling_staff)
            VALUES (%s, %s, %s, %s, %s, %s)
        ''', [
            ('A20241223', 'A+', '2024-12-01', '2024-12-15', 'Available', 'John Doe'),
            ('A20241224', 'O-', '2024-12-02', None, 'Reserved', 'Jane Smith'),
            ('A20241225', 'B+', '2024-11-28', '2024-12-05', 'Released', 'Alice Johnson'),
            ('A20241226', 'AB-', '2024-11-30', None, 'Available', 'Robert Brown'),
            ('A20241227', 'A-', '2024-12-03', '2024-12-20', 'Expired', 'Emily Davis'),
        ])

        # * donor info table
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS donor_info (
                donor_id INT(10) NOT NULL AUTO_INCREMENT,
                first_name VARCHAR(100) NOT NULL,
                middle_name VARCHAR(100),
                last_name VARCHAR(100) NOT NULL,
                suffix VARCHAR(100) DEFAULT 'N/A',
                birthdate DATE NOT NULL,
                contact VARCHAR(100) NOT NULL,
                sex VARCHAR(100) NOT NULL,
                blood_type VARCHAR(5) NOT NULL,
                extract_date DATE,
                bleeder VARCHAR(100) NOT NULL,
                remarks TEXT,
                PRIMARY KEY (donor_id)
            );
        ''')

        # * archived donor info table
        cursor.execute('''
                    CREATE TABLE IF NOT EXISTS archived_donor_info (
                        donor_id INT(10) NOT NULL AUTO_INCREMENT,
                        first_name VARCHAR(100) NOT NULL,
                        middle_name VARCHAR(100),
                        last_name VARCHAR(100) NOT NULL,
                        suffix VARCHAR(100) DEFAULT 'N/A',
                        birthdate DATE NOT NULL,
                        contact VARCHAR(100) NOT NULL,
                        sex VARCHAR(100) NOT NULL,
                        blood_type VARCHAR(5) NOT NULL,
                        extract_date DATE,
                        bleeder VARCHAR(100) NOT NULL,
                        remarks TEXT,
                        PRIMARY KEY (donor_id)
                    );
        ''')

        # * donor info placeholder values
        cursor.executemany('''
            INSERT INTO donor_info (first_name, middle_name, last_name, suffix, birthdate, contact, sex, blood_type, extract_date, bleeder, remarks)
            VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
        ''', [
            ('John', 'A.', 'Doe', 'N/A', '1990-05-15', 3427867456, 'Male', 'O+', '2024-01-10', 'Dr. House', 'No complications'),
            ('Jane', None, 'Smith', 'N/A', '1985-08-20', 564653484, 'Female', 'A-', '2024-01-11', 'Dr. JB', 'Slight dizziness after donation')
        ])

        # * audit trails table
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS audit_trails (
                action_id INT(10) NOT NULL AUTO_INCREMENT,
                date DATETIME NOT NULL,
                staff_name VARCHAR(100) NOT NULL,
                user_level ENUM('admin', 'user') NOT NULL,
                action_name VARCHAR(255) NOT NULL,
                `description` TEXT NOT NULL,
                PRIMARY KEY (action_id)
            );
        ''')

        # * audit trails placeholder values
        cursor.executemany('''
            INSERT INTO audit_trails (date, staff_name, user_level, action_name, `description`)
            VALUES (%s, %s, %s, %s, %s)
        ''', [
            ('2024-12-01 09:30:00', 'John Doe', 'admin', 'Login', 'Administrator logged into the system.'),
        ])

        # * void transactions table
        cursor.execute('''CREATE TABLE IF NOT EXISTS `void_transactions` (
                        `transaction_no` INT(10) NOT NULL AUTO_INCREMENT,
                        `staff_name` VARCHAR(100) NOT NULL,
                        `transaction_date` DATE NOT NULL,
                        `transaction_time` TIME NOT NULL,
                        `first_name` VARCHAR(100) NOT NULL,
                        `middle_name` VARCHAR(100),
                        `last_name` VARCHAR(100) NOT NULL,
                        `suffix` VARCHAR(20),
                        `birthdate` DATE,
                        `age` INT(3),
                        `sex` VARCHAR(10),
                        `province` VARCHAR(100),
                        `municipality` VARCHAR(100),
                        `barangay` VARCHAR(100),
                        `street` VARCHAR(100),
                        `id_type` VARCHAR(50),
                        `id_no` VARCHAR(50),
                        `contact_no` VARCHAR(15),
                        `email` VARCHAR(100),
                        `indigent` VARCHAR(10),
                        `paid_amount` DECIMAL(10, 2),
                        `blood_type` VARCHAR(5),
                        `blood_bag_no` VARCHAR(50),
                        `remarks` TEXT,
                        PRIMARY KEY (`transaction_no`)
                        );
        ''')

        # * transactions table
        cursor.execute('''CREATE TABLE IF NOT EXISTS `transactions` (
                        `transaction_no` INT(10) NOT NULL AUTO_INCREMENT,
                        `staff_name` VARCHAR(100) NOT NULL,
                        `transaction_date` DATE NOT NULL,
                        `transaction_time` TIME NOT NULL,
                        `first_name` VARCHAR(100) NOT NULL,
                        `middle_name` VARCHAR(100),
                        `last_name` VARCHAR(100) NOT NULL,
                        `suffix` VARCHAR(20),
                        `birthdate` DATE,
                        `age` INT(3),
                        `sex` VARCHAR(10),
                        `province` VARCHAR(100),
                        `municipality` VARCHAR(100),
                        `barangay` VARCHAR(100),
                        `street` VARCHAR(100),
                        `id_type` VARCHAR(50),
                        `id_no` VARCHAR(50),
                        `contact_no` VARCHAR(15),
                        `email` VARCHAR(100),
                        `indigent` VARCHAR(10),
                        `paid_amount` DECIMAL(10, 2),
                        `blood_type` VARCHAR(5),
                        `blood_bag_no` VARCHAR(50),
                        `remarks` TEXT,
                        PRIMARY KEY (`transaction_no`)
                        );
        ''')

        # * transactions placeholder values
        cursor.execute('''INSERT INTO `transactions` (
                            `staff_name`, `transaction_date`, `transaction_time`,
                            `first_name`, `last_name`, `middle_name`, `suffix`,
                            `birthdate`, `age`, `sex`, `province`, `municipality`,
                            `barangay`, `street`, `indigent`, `id_type`, `id_no`,
                            `contact_no`, `email`, `paid_amount`, `blood_type`,
                            `blood_bag_no`, `remarks`
                        )
                        VALUES
                            ('John Doe', '2024-01-01', '08:30:00', 
                             'Jane', 'Smith', 'A.', 'Jr.', 
                             '1990-05-15', 34, 'Female', 'Example Province', 
                             'Sample Municipality', 'Test Barangay', '123 Test St.', 
                             TRUE, 'PWD', 'P123456789', '1234567890', 
                             'jane.smith@example.com', 1500.50, 'O+', 
                             'BB12345', 'No known medical history');                 
        ''')

        # table for otp codes
        cursor.execute("""
                CREATE TABLE IF NOT EXISTS `otp_codes` (
                    `id` int NOT NULL AUTO_INCREMENT,
                    `email` varchar(255) NOT NULL,
                    `otp_code` varchar(6) NOT NULL,
                    `timestamp` datetime NOT NULL,
                    `status` enum('unused', 'used') DEFAULT 'unused',
                    PRIMARY KEY (`id`)
                ) ENGINE=InnoDB AUTO_INCREMENT=8 DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_ai_ci;
                """
        )

        # placeholder data for otp codes
        cursor.execute("""
                INSERT INTO `otp_codes` (id, email, otp_code, timestamp, status)
                VALUES 
                    (NULL, 'abegailmontejo9@gmail.com', '133780', '2025-01-08 18:03:59', 'unused'),
                    (NULL, 'abegailmontejo9@gmail.com', '841035', '2025-01-08 18:10:12', 'unused'),
                    (NULL, 'ABEGAILMONTEJO9@GMAIL.COM', '693700', '2025-01-08 18:16:30', 'unused'),
                    (NULL, 'abegailmontejo9@gmail.com', '164488', '2025-01-08 18:20:19', 'unused'),
                    (NULL, 'abegailmontejo9@gmail.com', '958928', '2025-01-08 18:36:58', 'unused'),
                    (NULL, 'abegailmontejo9@gmail.com', '382286', '2025-01-08 18:37:59', 'unused'),
                    (NULL, 'abegailmontejo9@gmail.com', '440804', '2025-01-08 18:41:29', 'used');
                """
        )

        conn.commit()


def get_exsiting_reservations():
    """ called by the reservations module to get all existing reservations """
    conn = db_conn()
    with conn.cursor() as cursor:
        cursor.execute("SELECT `rsrv_date` FROM reservations")
        rows = cursor.fetchall()

    conn.close()

    all_dates = set()
    for row in rows:
        rsrv_date = row[0]
        if rsrv_date:
            all_dates.add(rsrv_date)

    return all_dates


def get_reservee_name_by_date(date_str):
    conn = db_conn()  # Ensure this function establishes a database connection
    with conn.cursor() as cursor:
        try:
            # Parse the date string to a datetime.date object
            reservation_date = dt.datetime.strptime(date_str, "%Y-%m-%d").date()

            # Query the reservations table for all records matching the date
            cursor.execute("""
                    SELECT `rsrv_no`, `name`, `contact_no`, `email`, `rsrv_date`
                    FROM reservations
                    WHERE `rsrv_date` = %s
                """, (reservation_date,))

            # Fetch all matching records
            results = cursor.fetchall()

            # Return the list of records
            if results:
                return results
            else:
                return []

        finally:
            conn.close()

def void_transaction(transaction_no):
    """ used by void transaction func in transaction history. this archives transactions """
    try:
        conn = db_conn()
        with conn.cursor() as cursor:
            cursor.execute('''INSERT INTO void_transactions SELECT * FROM transactions
                                    WHERE `transaction_no` = %s''', (transaction_no,)
                           )
            cursor.execute('''DELETE FROM transactions WHERE `transaction_no` = %s''',
                               (transaction_no,)
                           )
        conn.commit()
        return 1
    except Exception as e:
        conn.rollback()
        print(f"Error voiding transaction: {e}")
        return 0
    finally:
        conn.close()

def select():
    # testing
    conn = db_conn()
    with conn.cursor() as cursor:
        cursor.execute('SELECT * FROM accounts')
        tets = cursor.fetchone()
        print(tets)
        conn.close()

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
    #test lines here
    #db_test_connection()
    #select()
    #pass
    db_init()
