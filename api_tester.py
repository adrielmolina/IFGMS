from py_scripts import db_conn, tools, models
import socket
import time
import requests


def test_db_connection_time():
    import time

    start = time.time()
    db_session = db_conn.SessionLocal()
    
    records = db_session.query(models.Records).all()
    end = time.time()

    print(f"DB QUERY TOOK: {end - start:.4f} seconds")
    
def test_db_latency():
    host = "turntable.proxy.rlwy.net"   # from your URI
    port = 19084                        # from your URI

    t1 = time.time()
    s = socket.socket()
    try:
        s.settimeout(5)
        s.connect((host, port))
        t2 = time.time()
        latency = round(t2 - t1, 4)
        s.close()
        return {"tcp_latency_sec": latency}
    except Exception as e:
        return {"error": str(e)}

def target_vs_actual_test():
    target_vs_actual = db_conn.get_report_target_vs_actual(2025)
    print('target vs actual:',target_vs_actual)

def test_domain():

    url = "https://maab.prc-cavite.org/"
    start = time.time()
    r = requests.get(url)
    end = time.time()

    print(f"Status: {r.status_code}, Total time: {end-start:.4f}s")

def get_claim_id_test():
    claim_id = db_conn.get_claim_id()
    print("New claim ID:", claim_id)

if __name__ == "__main__":
    #test_db_connection_time()
    #print(test_db_latency())
    #test_domain()
    #get_claim_id_test()
    target_vs_actual_test()
    