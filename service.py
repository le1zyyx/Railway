from flask import Flask, Response
import os, signal, threading, time, requests
from datetime import datetime
from prometheus_client import Gauge, Counter, generate_latest
from influxdb_client import InfluxDBClient, Point
from influxdb_client.client.write_api import SYNCHRONOUS
import hvac

log_file = "service.log"
app = Flask(__name__)

ZEC_PRICE     = Gauge('zec_price_usd', 'Current price of Zcash in USD')
REQ_COUNT     = Counter('http_requests_total', 'HTTP requests', ['endpoint'])
SCRAPE_ERRORS = Counter('zec_scrape_errors_total', 'Scrape errors')

def log(msg):
    with open(log_file, "a") as f:
        f.write(f"[{datetime.now()}] {msg}\n")

def get_influx_token():
    try:
        c = hvac.Client(url="http://localhost:8200", token="root")
        return c.secrets.kv.v2.read_secret_version(path="influxdb", mount_point="secret")["data"]["data"]["token"]
    except Exception as e:
        log(f"Vault fallback: {e}")
        return "mytoken"

@app.route("/")
def index():
    REQ_COUNT.labels(endpoint="/").inc()
    return "<h2>ZEC Price Tracker</h2><a href='/logs'>Logs</a> | <a href='/kill'>Kill</a> | <a href='/metrics'>Metrics</a>"

@app.route("/kill")
def kill():
    REQ_COUNT.labels(endpoint="/kill").inc()
    log("Kill command received")
    os.kill(os.getpid(), signal.SIGTERM)
    return "Restarting..."

@app.route("/logs")
def logs():
    REQ_COUNT.labels(endpoint="/logs").inc()
    try:
        data = open(log_file).readlines()[-100:]
    except:
        data = ["No logs\n"]
    return Response("<pre>" + "".join(data) + "</pre>", mimetype="text/html")

@app.route("/metrics")
def metrics():
    REQ_COUNT.labels(endpoint="/metrics").inc()
    return Response(generate_latest(), mimetype="text/plain")

def heartbeat():
    time.sleep(5)
    token = get_influx_token()
    write_api = InfluxDBClient(url="http://localhost:8086", token=token, org="myorg").write_api(write_options=SYNCHRONOUS)
    while True:
        price = 0
        try:
            r = requests.get("https://api.coingecko.com/api/v3/simple/price?ids=zcash&vs_currencies=usd", timeout=10).json()
            price = r["zcash"]["usd"]
            ZEC_PRICE.set(price)
            write_api.write(bucket="crypto", record=Point("crypto_price").tag("coin","zcash").field("price_usd", float(price)))
        except Exception as e:
            SCRAPE_ERRORS.inc()
            log(f"Error: {e}")
        log(f"ZEC Price: ${price}")
        time.sleep(60)

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5050))
    log(f"Service started on port {port}")
    threading.Thread(target=heartbeat, daemon=True).start()
    app.run(host="0.0.0.0", port=port)
