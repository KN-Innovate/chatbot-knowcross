import openai
from openai import OpenAI
from flask import Flask, request, jsonify
import requests
import os
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.metrics.pairwise import cosine_similarity
import json

app = Flask(__name__)

# Set environment variables for the API keys - I should create a separate env file 
#add you own variables for the api keys. The access token, phone number id, and verify token all connect with the meta developer account.
os.environ["OPENAI_API_KEY"] = "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"
os.environ["ACCESS_TOKEN"] = "EAAHEKlTvnYsBO9ZBEOu2t3Kh5pb8IJGYaZAvi8zmrBoAM3vZCJW7HOfvZBVly3ydXt7bKqqaK3shw7Qyyg6K1302f2IX08fgh4ujnvmPHKUF7dB5S8BcBGpZCeFd0BIhEi09SBgWCfuJKcSNLsSfqZC87u2qKQVjzZAQI6MeWjxIXJjpLToTQVLh6JiBWNnMW5KlCfn6Xna8ZAQAP9n6P15cHWnCY7td3QqC3FAZD"
os.environ["PHONE_NUMBER_ID"] = "520472474476006"
os.environ["VERIFY_TOKEN"] = "your_verify_token_2"

# OpenAI API Key - called from line 10
openai.api_key = os.getenv("OPENAI_API_KEY")

# Load the knowledge base
with open("knowledge_base.json", "r") as kb_file:
    knowledge_base = json.load(kb_file)

# In-memory state to track pending confirmations
pending_confirmations = {}

# Function to search the knowledge base
def search_knowledge_base(query, knowledge_base):
    # Extract issues from the knowledge base
    entries = [(item["issue"], item["response"]) for dept in knowledge_base.values() for item in dept]
    issues = [entry[0] for entry in entries]
    responses = [entry[1] for entry in entries]

    # Create and fit the vectorizer
    vectorizer = TfidfVectorizer()
    issue_vectors = vectorizer.fit_transform(issues)

    # Transform the query into the same vector space
    query_vec = vectorizer.transform([query])

    # Compute similarity scores
    similarities = cosine_similarity(query_vec, issue_vectors).flatten()

    # Get the top match above a similarity threshold
    top_index = similarities.argsort()[-1]  # Top match
    if similarities[top_index] > 0.2:
        return issues[top_index], responses[top_index], similarities[top_index]
    else:
        return None, None, None

# Function to send a message back to WhatsApp
def send_whatsapp_message(recipient_id, message):
    url = f"https://graph.facebook.com/v17.0/{os.getenv('PHONE_NUMBER_ID')}/messages"
    headers = {
        "Authorization": f"Bearer {os.getenv('ACCESS_TOKEN')}",
        "Content-Type": "application/json"
    }
    payload = {
        "messaging_product": "whatsapp",
        "to": recipient_id,
        "text": {"body": message}
    }
    response = requests.post(url, headers=headers, json=payload)
    print(f"Reply sent: {response.status_code}, {response.text}")

# Route to verify the webhook
@app.route('/webhook', methods=['GET'])
def verify_webhook():
    verify_token = os.getenv("VERIFY_TOKEN")  # Use environment variable for verification token
    if request.args.get('hub.verify_token') == verify_token:
        return request.args.get('hub.challenge'), 200
    return "Verification failed", 403

# Route to handle incoming POST requests from WhatsApp
@app.route('/webhook', methods=['POST'])
def handle_webhook():
    data = request.json
    print("Incoming Webhook Data:", data)

    try:
        if 'messages' in data["entry"][0]["changes"][0]["value"]:
            message = data["entry"][0]["changes"][0]["value"]["messages"][0]
            sender_id = message["from"]
            message_body = message["text"]["body"]
            print(f"Message from {sender_id}: {message_body}")

            # Process the user query
            response_message = process_openai_response(sender_id, message_body)

            # Send the processed response back to WhatsApp
            send_whatsapp_message(sender_id, response_message)
        else:
            print("Error: No messages field in incoming webhook data.")

    except KeyError as e:
        print(f"Error processing the incoming message: {e}")

    return jsonify({"status": "received"}), 200

# Function to interact with OpenAI
def process_openai_response(sender_id, user_input):
    # Check if a confirmation is pending for the user
    if sender_id in pending_confirmations:
        if user_input.lower() == "yes":
            # Retrieve the predefined response and clear the pending confirmation
            response = pending_confirmations.pop(sender_id)
            return response  # Return the predefined response
        else:
            # Clear the pending confirmation and return clarification message
            pending_confirmations.pop(sender_id)
            return "I'm sorry, I couldn't find an appropriate answer to your request. Could you please provide us with more details?"

    # If no confirmation is pending, process the new query
    issue, response, similarity = search_knowledge_base(user_input, knowledge_base)

    if issue:
        # Store the pending confirmation and send confirmation message
        pending_confirmations[sender_id] = response
        return f"Just confirming, do you need assistance with '{issue}'? Please reply 'yes' or 'no'."
    else:
        return "I'm sorry, I couldn't find a relevant entry in the knowledge base for your query. Could you please provide more details?"

if __name__ == "__main__":
    app.run(port=8080)
