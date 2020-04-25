from flask import Flask, request, jsonify
from twilio.twiml.messaging_response import MessagingResponse
import json
import twilio_messaging as messaging
import chatbot
import db
import connect
import os
import statefarm_handler as statefarm
from time import sleep
from threading import Thread

with open('config.json') as config_file:
    config = json.load(config_file)

app = Flask(__name__)

flag_connected = 0

cf_port = os.getenv("PORT")

@app.route('/')
def route():
    return "Hey.... You have reached State Farm API"

@app.route("/middleware/receive", methods=['GET', 'POST'])
def listen_input():
    message = request.values.get('Body', None)
    from_no = request.values.get('From', None)
    print(message, from_no)

    #Handling Media content
    num_media = int(request.values.get("NumMedia"))
    if num_media > 0:
        media_url = request.values.get(f'MediaUrl0')
        mime_type = request.values.get(f'MediaContentType0')
        print(media_url, mime_type)
        if num_media > 1:
            messaging.send_message(from_no, "Multiple media cannot be sent. Sending only first media")

    #Handling @statefarm commands
    if statefarm.is_statefarm_request(message):
        t = Thread(target=statefarm.handle_statefarm_request, args=(from_no, message,))
        t.start()
        # statefarm.handle_statefarm_request(from_no, message)
        return str(MessagingResponse())

    receiver = db.getReceiver(from_no)
    if receiver == db.IBM_RECEIVER:
        if statefarm.is_command(message):
            t = Thread(target=statefarm.handle_command, args=(from_no, message))
            t.start()
            return str(MessagingResponse())
        elif num_media > 0:
            reply = "Sorry! Our Automated chatbot doesn't support Media at this point."
        elif message == "":
            reply = "Invalid format. Your message is empty!"
        else:
            replies = chatbot.handle_message(from_no, message)
            if len(replies) > 1:
                t = Thread(target=messaging.send_messages, args=(from_no, replies))
                t.start()
                return(str(MessagingResponse()))
            else:
                reply = replies[0]
        resp = MessagingResponse()
        resp.message(reply)
        return str(resp)
    else:
        if num_media > 0:
            messaging.send_message_with_media(from_no, receiver, message, media_url, mime_type)
        elif message == "":
            messaging.send_message(from_no, "Invalid message. Can't be sent")
        else:
            messaging.send_message(receiver, message)
        return str(MessagingResponse())

@app.route("/middleware/connect_expert", methods=['GET', 'POST'])
def connectExpert():
    sessionID = request.values.get('sessionID', None)
    type = request.values.get('type', None)
    userID = db.getUserID(sessionID)
    if userID:
        expert = connect.connect_expert(userID, type)
        return str(expert)
    return str("Invalid Session")

@app.route("/middleware/send_message", methods=['GET', 'POST'])
def sendMessage():
    userID = request.values.get('userID', None)
    message = request.values.get('message', None)
    expert = messaging.send_message(userID, message)
    return str("Success")

if __name__ == "__main__":

    if cf_port is None:
        app.run(host='0.0.0.0', port=5000, debug=False)
    else:
        app.run(host='0.0.0.0', port=int(cf_port), debug=False)
