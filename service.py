from flask import Flask, Response
import os
import signal
import threading
import time
import requests
from datetime import datetime

log_file = "service.log"
app = Flask(__name__)

@app.route("/")
def index():
    return "<h2>ZEC Price Tracker</h2><a href='/logs'>View Logs</a> | <a href='/kill'>Kill Service</a>"

@app.route("/kill")
def kill():
    with open(log_file, "a") as f:
        f.write(f"[{datetime.now()}] Kill command received\n")
    os.kill(os.getpid(), signal.SIGTERM)
    return "Service restarting..."

@app.route("/logs")
def logs():
    try:
        with open(log_file) as f:
            data = f.readlines()[-100:]
    except:
        data = ["No logs yet\n"]
    return Response("<pre>" + "".join(data) + "</pre>", mimetype="text/html")

def heartbeat():
    while True:
        price = "N/A"
        try:
            url = "https://api.coingecko.com/api/v3/simple/price?ids=zcash&vs_currencies=usd"
            r = requests.get(url, timeout=10).json()
            price = r["zcash"]["usd"]
        except:
            pass
        
        with open(log_file, "a") as f:
            f.write(f"[{datetime.now()}] ZEC Price: ${price}\n")
        time.sleep(60)

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5050))
    with open(log_file, "a") as f:
        f.write(f"[{datetime.now()}] Service started on port {port}\n")
    threading.Thread(target=heartbeat, daemon=True).start()
    app.run(host="0.0.0.0", port=port)
