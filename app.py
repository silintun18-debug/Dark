# app.py
from flask import Flask, request, jsonify
import time
import requests
import threading

app = Flask(__name__)

# ⚙️ Configuration
BOT_TOKEN = "8778201970:AAHz1Ulh8uJM55AIm6USu_EBWNWLvLE4-Oc"
ADMIN_CHAT_ID = "7632580640"

user_sessions = {}   # User များ၏ အခြေအနေ သိမ်းဆည်းရန် memory
logout_queue = []    # Relay စက်က လာယူမည့် ဖြတ်ချရမယ့် IP စာရင်း

def send_telegram_alert(message):
    url = f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage"
    payload = {"chat_id": ADMIN_CHAT_ID, "text": message}
    try: requests.post(url, json=payload, timeout=5)
    except: pass

# ၁။ User ဖုန်းများက ၅ စက္ကန့်တစ်ခါ အချက်ပြစာ လာပို့မည့် လမ်းကြောင်း
@app.route('/heartbeat', methods=['POST'])
def heartbeat():
    data = request.json
    device_id = data.get("device_id")
    device_ip = data.get("ip")
    if device_id and device_ip:
        user_sessions[device_id] = {"ip": device_ip, "last_seen": time.time()}
        return jsonify({"status": "alive"}), 200
    return jsonify({"error": "bad data"}), 400

# ၂။ WiFi အောက်က Relay စက်က ဖြတ်ချရမည့် IP လာယူမည့် လမ်းကြောင်း
@app.route('/check_logout', methods=['GET'])
def check_logout():
    global logout_queue
    commands = list(logout_queue)
    logout_queue.clear() # ပို့ပြီးသား IP များကို ရှင်းထုတ်သည်
    return jsonify({"logout_ips": commands}), 200

# ၃။ စက္ကန့် ၄၀ ကျော် အချက်ပြစာ မလာတော့သော User ကို ဖမ်းထုတ်မည့် နောက်ကွယ်စနစ်
def monitor_users():
    while True:
        current_time = time.time()
        to_delete = []
        for dev_id, info in list(user_sessions.items()):
            # စက္ကန့် ၄၀ ကျော်သည်အထိ Heartbeat မလာတော့လျှင် (Termux ပိတ်လိုက်ပြီဟု ယူဆသည်)
            if current_time - info["last_seen"] > 40:
                if info["ip"] not in logout_queue:
                    logout_queue.append(info["ip"])
                to_delete.append(dev_id)
                send_telegram_alert(f"⚠️ User {dev_id} (IP: {info['ip']}) သည် Termux ပိတ်လိုက်သဖြင့် အင်တာနက် ဖြတ်ချလိုက်ပါပြီ။")
        
        for dev_id in to_delete:
            if dev_id in user_sessions: del user_sessions[dev_id]
        time.sleep(5)

if __name__ == '__main__':
    threading.Thread(target=monitor_users, daemon=True).start()
    app.run(host='0.0.0.0', port=5000)
