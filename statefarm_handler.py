import connect
import db
import twilio_messaging as messaging
import chatbot

def is_statefarm_request(message):
    if message.startswith("@statefarm"):
        return True
    else:
        return False

def is_register_command(message):
    if message.startswith("register as"):
        return True
    else:
        return False

def is_command(message):
    if connect.is_stop_requested(message):
        return True
    elif message == "list commands":
        return True
    elif connect.is_connect_requested(message):
        return True
    elif is_register_command(message):
        return True
    else:
        return False

def handle_command(from_no, message):
    receiver = db.getReceiver(from_no)
    if connect.is_connect_requested(message):
        if receiver == db.IBM_RECEIVER:
            connect.connect(from_no, message)
        else:
            messaging.send_messages(from_no, ["You are already connected to a statefarm agent.","To disconnect first message\n@statefarm disconnect"])
    elif connect.is_stop_requested(message):
        if receiver != db.IBM_RECEIVER:
            connect.disconnect(from_no, receiver)
        else:
            messaging.send_messages(from_no, ["You are not connected to any statefarm agent.","To connect first message\nconnect agent/community"])
    elif is_register_command(message):
        if message == "register as agent":
            db.updateUserType(from_no, db.TYPE_AGENT)
            messaging.send_messages(from_no, ["You are now registered as statefarm agent.","We will connect you to the user when asked for"])
        elif message == "register as user":
            db.updateUserType(from_no, db.TYPE_USER)
            messaging.send_messages(from_no, ["You are now a user.","You can talk to our chatbot or conenct to statefarm agent"])
        else:
            messaging.send_message(from_no, "We cannot understand your command.\nMessage @statefarm list commands to get the commands")
    elif message == "list commands":
        messaging.send_messages(from_no, ["Statefarm is here to help you", "Use @statefarm to send statefarm commands\n\"@statefarm connect to agent\" \tConnects you to agent\n\"@statefarm connect to community\" \tConnects you to community\n\"@statefarm disconnect\" \tDisconnects you\n\"@statefarm register as agent\" \Registers you as agent\n\"@statefarm register as user\" \Registers you as user\n"])
    else:
        messaging.send_message(from_no, "We cannot understand your command.\nMessage @statefarm list commands to get the commands")

def handle_statefarm_request(from_no, statefarm_message):
    message = statefarm_message.split(' ', 1)[1].strip() # Remove first word (@statefarm here)
    if is_command(message):
        handle_command(from_no, message)
    else:
        replies = chatbot.handle_message(from_no, message)
        messaging.send_messages(from_no, replies)
