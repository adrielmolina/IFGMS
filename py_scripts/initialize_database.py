import os
from dotenv import load_dotenv
from pathlib import Path
from sqlalchemy import create_engine, text


current_dir = Path(__file__).parent
parent_dir = current_dir.parent
env_loc = parent_dir/'creds.env'

print("ENV File Location:", env_loc)

load_dotenv(env_loc)

DB_CONNECTION_MODE = os.getenv('DB_CONNECTION_MODE', 'local').lower()

# FOR AIVEN DB CONNECTION
AIVEN_URI = os.getenv('AIVEN_URI')

# FOR LOCAL DB CONNECTION
SQL_HOST = os.getenv('SQL_HOST')
SQL_USER = os.getenv('SQL_USER')
SQL_PASS = os.getenv('SQL_PASS')
SQL_DB = os.getenv('SQL_DB')

#? TODO: add support for aiven db creation
def create_database():
    ''' create the database and run the initialization scripts. '''
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
            return None
    except Exception as e:
        print(f"Error: {e}")
        
if __name__ == '__main__':
    create_database()
    