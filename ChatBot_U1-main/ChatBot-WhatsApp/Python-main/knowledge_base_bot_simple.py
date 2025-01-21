from flask import Flask, request, jsonify
import requests
import json

app = Flask(__name__)

# WhatsApp Cloud API Access Token (replace with your valid access token)
ACCESS_TOKEN = "EAAHEKlTvnYsBOzCWN6T9RJ38vmB2V43JSugvDkSXqr56VlZB8dKGidc1HY8SNPrrSUDFpAk5hGBniPO2AnZAWWgz7yZCiJGXMpMGMVehzKGdNK00W9sPvCTARxZAj3Kwed8txg5Y7hGHMRGuDCEckKIjlmDHX6L0FLjZCe5WGdkcEVeXD0oQZCTbVsGSug4ZAjiiZAGmo5iHILZCLrdnIq2bkvnAMmSgyZCaGzGrwZD"

# WhatsApp Phone Number ID (replace with your phone number ID from webhook payload)
PHONE_NUMBER_ID = "520472474476006"  # Replace with actual phone number ID from webhook metadata

# Load the knowledge base from the JSON file
def load_knowledge_base():
    with open("knowledge_base.json", "r") as file:
        return json.load(file)

knowledge_base = load_knowledge_base()

# Route to verify webhook
@app.route('/webhook', methods=['GET'])
def verify_webhook():
    verify_token = "your_verify_token_2"  # Replace with your token
    if request.args.get('hub.verify_token') == verify_token:
        return request.args.get('hub.challenge'), 200
    return "Verification failed", 403

# Route to handle incoming POST requests
@app.route('/webhook', methods=['POST'])
def handle_webhook():
    data = request.json  # Capture incoming JSON data
    print("Incoming Webhook Data:", data)  # Log the payload

    try:
        changes = data["entry"][0]["changes"][0]
        if "messages" in changes["value"]:
            message = changes["value"]["messages"][0]
            sender_id = message["from"]
            message_body = message["text"]["body"].lower()

            # Log the received message
            print(f"Message from {sender_id}: {message_body}")

            # Handle menu-based interaction
            if message_body == "menu":
                send_reply(sender_id, "Welcome! Choose an option:\n1. Room Service\n2. Spa\n3. Help Desk")
            elif message_body == "1":
                send_reply(sender_id, "Room service menu:\n1. Food\n2. Cleaning\nReply with the option number.")
            elif message_body == "2":
                send_reply(sender_id, "Spa booking options:\n1. Massage\n2. Facial\nReply with the option number.")
            elif message_body in knowledge_base:
                # Respond from the knowledge base
                send_reply(sender_id, knowledge_base[message_body])
            else:
                # Commenting out OpenAI LLM for now
                # ai_response = get_ai_response(message_body)
                send_reply(sender_id, "I'm sorry, I couldn't process your request at the moment.")
    except KeyError as e:
        print(f"KeyError: {e} - Incoming data may not match expected format.")

    return jsonify({"status": "received"}), 200

# Function to send a reply
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
    response = requests.post(url, headers=headers, json=payload)
    print("Reply sent:", response.status_code, response.text)

# Function to get a response from OpenAI's LLM (commented out for now)
# def get_ai_response(user_input):
#     try:
#         response = openai.ChatCompletion.create(
#             model="gpt-3.5-turbo",  # Using the turbo model
#             messages=[
#                 {"role": "system", "content": "You are a helpful assistant for hotel guests."},
#                 {"role": "user", "content": user_input}
#             ],
#             temperature=0.7  # Adjust for creativity
#         )
#         return response.choices[0].message["content"]
#     except Exception as e:
#         print(f"OpenAI API Error: {e}")
#         return "I'm sorry, I couldn't process your request at the moment."

if __name__ == "__main__":
    app.run(port=8080)
