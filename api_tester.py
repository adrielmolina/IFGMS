from py_scripts import db_conn, tools




if __name__ == "__main__":
    target_vs_actual = db_conn.get_report_target_vs_actual(2025)
    print('target vs actual:',target_vs_actual)
    
    