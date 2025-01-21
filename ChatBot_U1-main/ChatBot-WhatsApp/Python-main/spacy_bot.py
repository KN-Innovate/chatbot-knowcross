import spacy
from flask import Flask, request, jsonify
import requests
import json

app = Flask(__name__)

# Load the spaCy model for natural language processing (NLP)
nlp = spacy.load("en_core_web_sm")

# WhatsApp Cloud API Access Token (replace with your valid access token)
ACCESS_TOKEN = "EAAHEKlTvnYsBO01vgtQdxQlKnZBMRQdOCpPZBvZCePwzES3UABSy6h8gRC3CHhm0geFx5EFrOpyEdnwOQrmbPjLEhGl00fQMOVvGtjIhob7mFII6mi9EXw0YoWuJt2mCZA47gjcFwUpPxZC7xtqZBbseknyiNHYyuWUruC9kv5ADcvLVD7SRtBZCINyRT0X5gOPstqCkmSM5la4OKg7OPMCZCIFS0SpUIHNvPvTV"

# WhatsApp Phone Number ID (replace with your phone number ID from webhook payload)
PHONE_NUMBER_ID = "520472474476006"  # Replace with actual phone number ID from webhook metadata

# Load the knowledge base from the JSON file
def load_knowledge_base():
    with open("knowledge_base.json", "r") as file:
        return json.load(file)

knowledge_base = load_knowledge_base()

# Preprocessing for user input
def preprocess_input(text):
    return text.lower().strip()

# Function to find the best match for a query in the knowledge base
def find_best_match(user_input):
    user_doc = nlp(preprocess_input(user_input))  # Process user input with spaCy
    best_match = None
    highest_similarity = 0.0

    for key in knowledge_base.keys():
        key_doc = nlp(preprocess_input(key))  # Process knowledge base key
        similarity = user_doc.similarity(key_doc)  # Calculate similarity
        print(f"Comparing '{user_input}' with '{key}': Similarity = {similarity}")  # Log similarity scores
        if similarity > highest_similarity:
            highest_similarity = similarity
            best_match = key

    # Return the best match if similarity exceeds a reduced threshold
    if highest_similarity >= 0.3:  # Adjusted threshold
        return best_match

    # Fallback suggestion when no match is found
    suggestions = ", ".join(knowledge_base.keys())
    return f"I'm not sure what you mean. You can ask about: {suggestions}"


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
            message_body = message["text"]["body"]

            # Log the received message
            print(f"Message from {sender_id}: {message_body}")

            # Handle numeric menu-based interaction explicitly
            if message_body.strip().lower() == "menu":
                send_reply(sender_id, "Welcome! Choose an option:\n1. Room Service\n2. Spa\n3. Help Desk")
            elif message_body.strip() == "1":
                send_reply(sender_id, "Room service menu:\n1. Food\n2. Cleaning\nReply with the option number.")
            elif message_body.strip() == "2":
                send_reply(sender_id, "Spa booking options:\n1. Massage\n2. Facial\nReply with the option number.")
            elif message_body.strip() == "3":
                send_reply(sender_id, "You can contact the help desk directly at +1-234-567-890 or reply with your issue.")
            else:
                # Use spaCy for nuanced matching
                matched_key = find_best_match(message_body)
                if matched_key:
                    send_reply(sender_id, knowledge_base[matched_key])
                else:
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

if __name__ == "__main__":
    app.run(port=8080)
