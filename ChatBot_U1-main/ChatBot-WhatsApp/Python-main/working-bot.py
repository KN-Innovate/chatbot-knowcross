from flask import Flask, request, jsonify, session
import requests
import json
import os
from openai import OpenAI
import re

# Create the OpenAI client with base URL and API key
client = OpenAI(
    base_url="https://zkr2juu683zw2a-8000.proxy.runpod.net/v1",  # Your base URL
    api_key="dW9nO2pQ5"  # Your API key
)

app = Flask(__name__)

# Set environment variables for the API keys
os.environ["ACCESS_TOKEN"] = "EAAHEKlTvnYsBO5mzfgZApi3H6sbIvk6rPyQ3vqr63wlbVm6ChUXUT0WSRldz3RVfRRHBpTEBj45v2bmzNodICzYpDrgxTpFlHMNIHvDYMFcq1ZC5DCEnUvZAOUlr47zuER9Pz1BLNrBww0bZANGXrecZAp9475rXMGjBN8wceIhaIVT8h7RKEX60EDp1e3Pc7uL1rEahQxay1rvWRhncWo9ZCEKLTfRPmmXnsZD"
os.environ["PHONE_NUMBER_ID"] = "520472474476006"
os.environ["VERIFY_TOKEN"] = "your_verify_token"
app.secret_key = os.urandom(24)  # Used for storing session data

# Define the food menu items
menu_items = {
    "main_course": {
        "cheeseburger": 34,
        "cheese sandwich": 22,
        "chicken burgers": 23,
        "spicy chicken": 33,
        "hot dog": 24
    },
    "appetizers": {
        "fruit salad": 13,
        "cocktails": 12,
        "nuggets": 14,
        "sandwich": 13,
        "french fries": 15
    },
    "beverages": {
        "milk shake": 3,
        "iced tea": 2,
        "orange juice": 4,
        "lemon tea": 3,
        "coffee": 5
    }
}

# Quantity words mapping
quantity_words = {
    "one": 1, "two": 2, "three": 3, "four": 4, "five": 5,
    "six": 6, "seven": 7, "eight": 8, "nine": 9, "ten": 10,
    "eleven": 11, "twelve": 12, "thirteen": 13, "fourteen": 14, "fifteen": 15
}

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

# Function to extract user input, detect order, and manage context
def extract_intent_and_entities(user_input):
    user_input = user_input.lower()
    ordered_items = []

    for category, items in menu_items.items():
        for item, price in items.items():
            # Detect quantity, both in word or number form
            quantity = 1  # default quantity if none is found
            # Check for numeric quantity (e.g., "2 cheeseburgers")
            match_numeric = re.search(r'(\d{1,2})\s+' + re.escape(item), user_input)
            if match_numeric:
                quantity = int(match_numeric.group(1))
            
            # Check for word-based quantity (e.g., "three cheeseburgers")
            match_word = re.search(r'(' + '|'.join(quantity_words.keys()) + r')\s+' + re.escape(item), user_input)
            if match_word:
                quantity = quantity_words[match_word.group(1)]
            
            # If the item and quantity are detected, add to the list
            if item in user_input:
                ordered_items.append((item, quantity, price * quantity))

    if ordered_items:
        return "order_room_service", ordered_items
    else:
        return "ask_about_hotel", {}

# Function to interact with DeepSeek API (OpenAI)
def process_openai_response(sender_id, user_input):
    try:
        # Clean the user input
        prompt = user_input.strip()

        # Apply hotel context if needed
        if "room service" in user_input.lower():
            response = "Absolutely! You can easily order room service from your room, hallway, or through our concierge service. Our menu features a variety of options to choose from. Would you like to browse our menu, or do you know what you'd like to order already?"
        elif "menu" in user_input.lower():
            response = "Sure! Here's our menu: \n\n**Main Course**\n- Cheeseburger $34\n- Cheese Sandwich $22\n- Chicken Burger $23\n- Spicy Chicken $33\n- Hot Dog $24\n\nWould you like to place an order from any of these?"
        else:
            # Send the instruction to the model if the input is not specific to room service
            completion = client.chat.completions.create(
                model="deepseek-ai/DeepSeek-R1-Distill-Qwen-7B",  # Use the appropriate model
                messages=[
                    {
                        "role": "user",
                        "content": f"Respond professionally and clearly, without any slang or informal expressions. Be concise and direct. Do not use any tags like <think> or any intermediate reasoning. Only provide the final, clean response to: '{prompt}'"
                    }
                ]
            )

            # Extract and clean up the response
            response = completion.choices[0].message.content.strip()

        # Remove any unexpected tags like <think> or other processing information
        if "<think>" in response:
            response = response.split("</think>")[-1].strip()

        return response

    except Exception as e:
        print(f"Error with OpenAI API: {e}")
        return "Sorry, I couldn't process your request."

# Route to verify the webhook
@app.route('/webhook', methods=['GET'])
def verify_webhook():
    verify_token = os.getenv("VERIFY_TOKEN")
    if request.args.get('hub.verify_token') == verify_token:
        return request.args.get('hub.challenge'), 200
    return "Verification failed", 403

# Function to process maintenance requests more smoothly
def process_maintenance_request(sender_id, message_body):
    response_message = ""

    if "extra towels" in message_body:
        # Confirm the request for towels
        response_message = "Just to confirm, you need extra towels delivered to your room, correct?"
        
    elif "shower" in message_body and ("not working" in message_body or "broken" in message_body):
        # Request clarification for the shower issue
        response_message = "I’m sorry to hear that! Could you please provide more details about the issue with the shower?"
    
    else:
        # If it’s a maintenance request, reassure the user
        response_message = "Thank you for your request. We will send someone to take care of the issue right away."

    return response_message

# Function to handle incoming POST requests from WhatsApp
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

            # Check for maintenance-related messages
            if "towels" in message_body or "shower" in message_body:
                response_message = process_maintenance_request(sender_id, message_body)
            else:
                # If it’s not related to maintenance, fallback to the previous flow
                response_message = process_openai_response(sender_id, message_body)

            # Send the processed response back to WhatsApp
            send_whatsapp_message(sender_id, response_message)
        else:
            print("Error: No 'messages' field in incoming webhook data.")

    except KeyError as e:
        print(f"Error processing the incoming message: {e}")

    return jsonify({"status": "received"}), 200

if __name__ == "__main__":
    app.run(port=8080)
