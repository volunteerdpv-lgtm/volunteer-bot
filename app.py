import os, json, requests
from flask import Flask, request, jsonify

app = Flask(__name__)

VERIFY_TOKEN = os.environ.get("VERIFY_TOKEN", "volunteer123")
WHATSAPP_TOKEN = os.environ.get("WHATSAPP_TOKEN")
PHONE_NUMBER_ID = os.environ.get("PHONE_NUMBER_ID")
ADMIN_NUMBER = "971505584713"  # Your number without +

# In-memory storage for test (Render free will reset on restart - OK for test)
sessions = {}
events = []
registrations = []

def send_msg(to, text):
    url = f"https://graph.facebook.com/v21.0/{PHONE_NUMBER_ID}/messages"
    headers = {"Authorization": f"Bearer {WHATSAPP_TOKEN}", "Content-Type": "application/json"}
    data = {"messaging_product": "whatsapp", "to": to, "type": "text", "text": {"body": text}}
    requests.post(url, headers=headers, json=data)

QUESTIONS = [
    "1. Volunteering Opportunity Name?",
    "2. Gender? (Male / Female / Male and Female)",
    "3. Venue?",
    "4. Date? (e.g. 8 Nov 2026)",
    "5. Start Time? (e.g. 8:00 AM)",
    "6. End Time? (e.g. 10:00 AM)",
    "7. Volunteers Needed? (e.g. 10)",
    "8. Report At Venue? (e.g. 7:30 AM)",
    "9. Registration? (e.g. 6 Nov to 7 Nov)"
]

@app.route("/", methods=["GET"])
def home():
    return "Volunteer Bot Running", 200

@app.route("/webhook", methods=["GET", "POST"])
def webhook():
    if request.method == "GET":
        if request.args.get("hub.verify_token") == VERIFY_TOKEN:
            return request.args.get("hub.challenge"), 200
        return "Forbidden", 403

    data = request.get_json()
    try:
        entry = data["entry"][0]["changes"][0]["value"]
        if "messages" not in entry: return jsonify({"status":"ok"}), 200
        msg = entry["messages"][0]
        from_num = msg["from"]
        text = msg.get("text", {}).get("body", "").strip()
        upper = text.upper()

        # --- ADMIN: NEW EVENT ---
        if from_num == ADMIN_NUMBER and upper in ["NEW EVENT", "NEW", "CREATE EVENT"]:
            sessions[from_num] = {"step": 0, "answers": []}
            send_msg(from_num, "✅ Let's create NEW Event.\n\n" + QUESTIONS[0])
            return jsonify({"status":"ok"}), 200

        # --- ADMIN: Answering 9 Questions ---
        if from_num == ADMIN_NUMBER and from_num in sessions:
            s = sessions[from_num]
            s["answers"].append(text)
            s["step"] += 1
            if s["step"] < 9:
                send_msg(from_num, QUESTIONS[s["step"]])
            else:
                a = s["answers"]
                preview = f"""✅ EVENT CREATED!

🟢 NEW VOLUNTEERING OPPORTUNITY

1. Volunteering Opportunity Name: {a[0]}
2. Gender: {a[1]}
3. Venue: {a[2]}
4. Date: {a[3]}
5. Start Time: {a[4]}
6. End Time: {a[5]}
7. Volunteers Needed: {a[6]}
8. Report At Venue: {a[7]}
9. Registration: {a[8]}

TO JOIN: Reply JOIN YourName

Reply CONFIRM to Save, or CANCEL to Discard"""
                send_msg(from_num, preview)
                s["step"] = 99
            return jsonify({"status":"ok"}), 200

        # --- ADMIN: CONFIRM ---
        if from_num == ADMIN_NUMBER and upper == "CONFIRM" and from_num in sessions:
            s = sessions[from_num]
            events.append(s["answers"])
            del sessions[from_num]
            send_msg(from_num, "✅ Event Saved! Volunteers can now reply JOIN YourName to register.")
            return jsonify({"status":"ok"}), 200

        if from_num == ADMIN_NUMBER and upper == "CANCEL":
            sessions.pop(from_num, None)
            send_msg(from_num, "❌ Event Cancelled.")
            return jsonify({"status":"ok"}), 200

        # --- VOLUNTEER: JOIN ---
        if upper.startswith("JOIN"):
            name = text[4:].strip() or "Volunteer"
            if not events:
                send_msg(from_num, "No active event right now. Please wait for next opportunity.")
            else:
                registrations.append({"phone": from_num, "name": name, "event": events[-1][0]})
                send_msg(from_num, f"✅ Thank you {name}! You are registered for {events[-1][0]} on {events[-1][3]} at {events[-1][2]}. Report at {events[-1][7]}. See you there!")
            return jsonify({"status":"ok"}), 200

        # --- Default ---
        if from_num == ADMIN_NUMBER:
            send_msg(from_num, "Hi Admin! Send NEW EVENT to create event.\nSend LIST to see registrations.")
        else:
            if events:
                a = events[-1]
                send_msg(from_num, f"Hi! Latest Event: {a[0]} on {a[3]} at {a[2]}. To join, reply JOIN YourName")
            else:
                send_msg(from_num, "Hi! No active event yet. You will be notified when new event is created.")
    except Exception as e:
        print(e)
    return jsonify({"status":"ok"}), 200

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=int(os.environ.get("PORT", 10000)))
