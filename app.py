import threading
import time
import requests
from datetime import datetime, timedelta
from flask import Flask, request, jsonify

app = Flask(__name__)

BOT_TOKEN = "8778201970:AAHz1Ulh8uJM55Aim6USu_EBWNWLvLE4-0c"
ADMIN_CHAT_ID = "7632580640"

user_sessions = {}   
logout_queue = []    
active_users = set()  

def get_current_mm_time():
    mm_time = datetime.utcnow() + timedelta(hours=6, minutes=30)
    return mm_time.strftime("%d-%m-%Y %I:%M:%S %p")

def send_telegram_alert(message):
    url = f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage"
    payload = {"chat_id": ADMIN_CHAT_ID, "text": message}
    try:
        requests.post(url, json=payload, timeout=5)
    except:
        pass

@app.route('/heartbeat', methods=['POST'])
def heartbeat():
    data = request.json or {}
    device_id = data.get("device_id")

    device_ip = data.get("ip")
    if not device_ip or device_ip == "Unknown" or device_ip.startswith("127."):
        device_ip = request.remote_addr

    if device_id and device_ip:
        current_time = time.time()

        if device_id not in active_users:
            active_users.add(device_id)
            time_str = get_current_mm_time()
            send_telegram_alert(f"🔔 Voucher Client [{device_id}] is now ONLINE!\n📍 Registered IP: {device_ip}\n⏰ Time: {time_str}")

        user_sessions[device_id] = {"ip": device_ip, "last_seen": current_time}
        return jsonify({"status": "alive", "registered_ip": device_ip}), 200

    return jsonify({"error": "bad data"}), 400

@app.route('/check_logout', methods=['GET'])
def check_logout():
    global logout_queue
    commands = list(logout_queue)
    logout_queue.clear()  
    return jsonify({"logout_ips": commands}), 200

@app.route('/active_clients', methods=['GET'])
def active_clients():
    clients_list = []
    for dev_id, info in user_sessions.items():
        clients_list.append({
            "device_id": dev_id,
            "ip": info["ip"]
        })
    return jsonify({"clients": clients_list}), 200

@app.route('/remove_client', methods=['POST'])
def remove_client():
    data = request.json or {}
    target_ip = data.get("ip")
    if target_ip:
        to_remove = [dev_id for dev_id, info in user_sessions.items() if info["ip"] == target_ip]
        for dev_id in to_remove:
            if dev_id in user_sessions:
                del user_sessions[dev_id]
            if dev_id in active_users:
                active_users.remove(dev_id)
        return jsonify({"success": True}), 200
    return jsonify({"error": "Missing IP"}), 400

def monitor_users():
    while True:
        current_time = time.time()
        to_delete = []

        for dev_id, info in list(user_sessions.items()):
            if current_time - info["last_seen"] > 35:
                target_ip = info["ip"]
                if target_ip and target_ip not in logout_queue:
                    logout_queue.append(target_ip)
                to_delete.append(dev_id)

                if dev_id in active_users:
                    active_users.remove(dev_id)
                    time_str = get_current_mm_time()
                    send_telegram_alert(f"❌ Voucher Client [{dev_id}] is now OFFLINE (Termux Closed)!\n📍 Disconnecting IP: {target_ip}\n⏰ Closed At: {time_str}")

        for dev_id in to_delete:
            if dev_id in user_sessions:
                del user_sessions[dev_id]

        time.sleep(5)

threading.Thread(target=monitor_users, daemon=True).start()

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000)