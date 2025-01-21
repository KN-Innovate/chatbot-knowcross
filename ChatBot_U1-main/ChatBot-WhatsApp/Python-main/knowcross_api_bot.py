from flask import Flask, request, jsonify
import requests
import json
import hashlib
import hmac
import time
import base64
import urllib.parse

app = Flask(__name__)

# WhatsApp Cloud API details
ACCESS_TOKEN = "EAAHEKlTvnYsBOwJPGCM0FzppOSYx2Rk5CxOICGRWTTx9g2OoQwZCnUpZBFWZCzZCsN82t9SgSCRT4yuKodOZCWRznqZCMzr32LNPJ7ajVrgzx8DCjU0AjwSBTfh5zFZA2tGK2V3vKp1X7zssPLD9LgihVbCYUpKOw9dZBiHng42FZAb5PZA1IWfDDLg86BDDi1YgMKjiEL6SJZBZBoZAKOldOmPUsXpiSuevqsN0uRGAZD"
PHONE_NUMBER_ID = "520472474476006"
VERIFY_TOKEN = "your_verify_token"

# KnowCross API details
KNOWCROSS_API_BASE_URL = "https://sd-integrationapi.knowcross.com"
KNOWCROSS_PROPERTY_ID = "3038"
KNOWCROSS_PUBLIC_KEY = "BEEEABEE-69CC-41E3-82E1-B958F0AB0D9D"
KNOWCROSS_PRIVATE_KEY = "FB2E21BD-5343-4C10-BF77-4FAD223C7CDA"

# Generate signature for KnowCross API
def generate_signature(method, endpoint):
    timestamp = str(int(time.time()))  # Current UNIX time
    full_url = f"{KNOWCROSS_API_BASE_URL}{endpoint}".lower()

    # Double-encode the URL
    encoded_url = urllib.parse.quote(full_url, safe='').lower()

    raw_data = f"{KNOWCROSS_PUBLIC_KEY}{method.upper()}{encoded_url}{timestamp}"

    # Debugging
    print("---- DEBUG SIGNATURE ----")
    print(f"Public Key: {KNOWCROSS_PUBLIC_KEY.strip()}")
    print(f"Request Method: {method.upper()}")
    print(f"Full URL (Unencoded): {full_url}")
    print(f"Encoded URL: {encoded_url}")
    print(f"Timestamp: {timestamp}")
    print(f"Raw Data for Signature: {raw_data}")

    # HMAC-SHA256 hash
    hash_digest = hmac.new(
        KNOWCROSS_PRIVATE_KEY.strip().encode("utf-8"),
        raw_data.encode("utf-8"),
        hashlib.sha256
    ).digest()

    # Base64 encoding (with padding)
    signature = base64.b64encode(hash_digest).decode('utf-8')

    print(f"HMAC Digest: {hash_digest}")
    print(f"Generated Signature (Base64): {signature}")
    print("-------------------------")

    return f"{KNOWCROSS_PUBLIC_KEY.strip()}:{signature}:{timestamp}"



# Fetch parameters from the Master API
def fetch_master_data(property_id):
    endpoint = f"/integrationapi/master/GetAllPropertyMaster?propertyid={property_id}"
    signature = generate_signature("GET", endpoint)

    headers = {
        "X-Knowcross-Access": signature,
        "Content-Type": "application/json"
    }

    try:
        response = requests.get(f"{KNOWCROSS_API_BASE_URL}{endpoint}", headers=headers)
        print(f"Response Status: {response.status_code}")
        print(f"Response Body: {response.text}")
        if response.status_code == 200:
            return response.json()
        else:
            print(f"Failed to fetch master data: {response.status_code} - {response.text}")
            return None
    except Exception as e:
        print(f"Error fetching master data: {e}")
        return None

# Register a service request
def register_service_request(remarks, attachments=None):
    master_data = fetch_master_data(KNOWCROSS_PROPERTY_ID)
    if not master_data:
        return "Failed to fetch required parameters from Master API."

    try:
        location_id = master_data["locations"][0]["id"]
        category_id = master_data["categories"][0]["id"]
        description_id = master_data["descriptions"][0]["id"]
    except (KeyError, IndexError) as e:
        print(f"Error parsing master data: {e}")
        return "Error parsing master data. Please check the API response format."

    endpoint = "/integrationapi/complain/RegisterCall"
    signature = generate_signature("POST", endpoint)

    sanitized_remarks = ''.join(e for e in remarks if e.isalnum() or e.isspace())

    headers = {
        "X-Knowcross-Access": signature,
        "Content-Type": "application/json"
    }

    payload = [
        {
            "PropertyId": KNOWCROSS_PROPERTY_ID,
            "LocationId": location_id,
            "CategoryId": category_id,
            "CallDescriptionsId": description_id,
            "Priority": 1,
            "IsGuestCall": True,
            "Remarks": sanitized_remarks,
            "Operation": 1,
            "CurrentStatus": "OPN",
            "Attachments": attachments or []
        }
    ]

    try:
        response = requests.post(f"{KNOWCROSS_API_BASE_URL}{endpoint}", headers=headers, json=payload)
        print(f"Response Status: {response.status_code}")
        print(f"Response Body: {response.text}")
        if response.status_code == 200:
            return "Service request successfully registered."
        else:
            return f"Failed to register service request: {response.status_code} - {response.text}"
    except Exception as e:
        print(f"Error registering service request: {e}")
        return "An error occurred while registering the service request."

@app.route('/webhook', methods=['GET', 'POST'])
def webhook():
    if request.method == 'GET':
        if request.args.get('hub.verify_token') == VERIFY_TOKEN:
            return request.args.get('hub.challenge'), 200
        return "Verification failed", 403

    if request.method == 'POST':
        data = request.json
        try:
            changes = data["entry"][0]["changes"][0]
            if "messages" in changes["value"]:
                message = changes["value"]["messages"][0]
                sender_id = message["from"]
                message_body = message["text"]["body"]

                if message_body.lower() == "room service":
                    response = register_service_request("Room service requested via chatbot.")
                    send_reply(sender_id, response)
                else:
                    send_reply(sender_id, "I'm sorry, I didn't understand your request.")
        except KeyError as e:
            print(f"KeyError: {e}")
        return jsonify({"status": "received"}), 200

def send_reply(recipient_id, message):
    url = f"https://graph.facebook.com/v17.0/{PHONE_NUMBER_ID}/messages"
    headers = {
        "Authorization": f"Bearer {ACCESS_TOKEN}",
        "Content-Type": "application/json"
    }
    payload = {
        "messaging_product": "whatsapp",
        "to": recipient_id,
        "text": {"body": message}
    }
    try:
        response = requests.post(url, headers=headers, json=payload)
        print(f"Reply sent: {response.status_code} - {response.text}")
    except Exception as e:
        print(f"Error sending reply: {e}")

if __name__ == "__main__":
    app.run(port=8080)
