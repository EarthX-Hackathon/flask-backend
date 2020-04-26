from flask import Flask, request, jsonify, redirect
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


from twilio.twiml.voice_response import VoiceResponse
from twilio import twiml
import csv
import requests
import time
from twilio.rest import Client
from twilio.twiml.voice_response import Record, VoiceResponse, Gather
from xml.etree import ElementTree

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


@app.route("/voice", methods=['GET', 'POST'])
def voice():
    resp = VoiceResponse()

    g = Gather(num_digits=1, action='/handleVoice')
    g.say("Welcome, press one for English", voice='alice', language="en-US")
    g.say("Bienvenido, para español, presione 2", voice='alice', language="es-MX")
    g.say("欢迎，按3为中文", voice='alice', language="zh-CN")

    resp.append(g)

    resp.redirect('/voice')

    return str(resp)


@app.route("/handleVoice", methods=['GET', 'POST'])
def handleVoice():
    resp2 = VoiceResponse()

    if 'Digits' in request.values:
        # Get which digit the caller chose
        choice = request.values['Digits']
        phone = request.values['From']

        if choice == '1':
            gg =Gather(num_digits=1, action='/recordAndSend')
            gg.say("Hi, all our agents are busy right now. If your query is not urgent, would you like to leave a msg for us? We will get back to you with the response very soon. Press 1 to leave a msg. Press 2 to wait for the agent.", voice='alice', language="en-US")

            resp2.append(gg)

            print(resp2)
            return str(resp2)

        elif choice == '2':
            gg =Gather(num_digits=1, action='/recordAndSend')
            gg.say("Hola, todos nuestros agentes están ocupados en este momento. Si su consulta no es urgente, ¿desea dejarnos un mensaje? Nos pondremos en contacto con usted con la respuesta muy pronto. Presione 1 para dejar un mensaje. Presione 2 para esperar al agente.", voice='alice', language="es-MX")

            resp2.append(gg)

            print(resp2)
            return str(resp2)

        elif choice == '3':
            gg =Gather(num_digits=1, action='/recordAndSend')
            gg.say("嗨，我们所有的经纪人现在都在忙。如果您的查询不紧急，您想给我们留言吗？我们会尽快回复您。按1离开留言。按2等待代理。", voice='alice', language="zh-CN")

            resp2.append(gg)

            print(resp2)
            return str(resp2)

        else:
            resp2.say("Sorry, I dint understand the input")
            return ""

    return str(resp2)

@app.route("/handleVoiceResponse", methods=['GET', 'POST'])
def handleVoiceResponse():
    #resp = VoiceResponse()
    soundURL = (request.values['RecordingUrl'])
    print (request.values)
    calltext = request.values['TranscriptionText']
    caller = request.values['From']

    msgBody = chatbot.handle_message(caller, calltext)
    messaging.send_messages(caller, msgBody)

    return 'success'


@app.route("/recordAndSend", methods=['GET','POST'])
def recordAndSend():
    resp = VoiceResponse()

    if 'Digits' in request.values:
        choice = request.values['Digits']

        if choice == '1':
            resp.say("Hi, how can I help you today?", voice='alice', language="en-US")
            resp.record(maxLength = 20,timeout=10, transcribe=True, transcribeCallback="/handleVoiceResponse")

            print (resp)
            return str(resp)

        if choice == '2':
            resp.say("Please stay online.", voice='alice', language="en-US")
            resp.hangup()

    else:
        resp.say("We got your msg. Thank you.", voice='alice', language="en-US")
        resp.hangup()

    return str(resp)

'''
@app.route("/saythis", methods=['GET', 'POST'])
def saythis():
    replytext2 = request.args.get('reptext')
    resp = VoiceResponse()
    resp.say(replytext2, voice='alice', language="en-US")
    return 'ok'
'''

def twiml(resp):
    resp = flask.Response(str(resp))
    resp.headers['Content-Type'] = 'text/xml'
    return resp


if __name__ == "__main__":

    if cf_port is None:
        app.run(host='0.0.0.0', port=5000, debug=False)
    else:
        app.run(host='0.0.0.0', port=int(cf_port), debug=False)
