import json
import ibm_watson
import json
import db
from ibm_cloud_sdk_core.authenticators import IAMAuthenticator

INTENT_DOCTOR = 'Register_Agent'
INTENT_COMMUNITY = 'Register_Community'

model_name = "en_core_web_sm"

import spacy
import csv
from spacy.cli.download import download
download(model_name)
#from spacy.cli import link
#from spacy.util import get_package_path
#package_path = get_package_path(model_name)
#link(model_name, model_name, force=True, package_path=package_path)

nlp = spacy.load('en_core_web_sm')

import logging
logging.getLogger("scapy.runtime").setLevel(logging.ERROR)

replytext ='empty msg'

with open('config.json') as config_file:
    config = json.load(config_file)

authenticator = IAMAuthenticator(config["ibm_assistant"]["iam_apikey"])
service = ibm_watson.AssistantV2(
    version='2020-04-01',
    authenticator=authenticator
)

service.set_service_url(config["ibm_assistant"]["url"])

def handle_message(from_no, message):
    reply =  get_response(from_no, message)
    #print(json.dumps(response, indent=2))

    #Split message on <#>
    replies = reply.split('<#>')
    return replies



def get_response(from_no, message):
    gotreply = False
    global replytext
    with open('FAQ.csv', encoding="utf8") as csv_file:
        csv_reader=csv.reader(csv_file , delimiter=',')

        for row in csv_reader:
            similarity = nlp(row[0].lower()).similarity(nlp(message.lower()))
            #print (similarity)
            #print (str(message), str(row[0]))
            if similarity > 0.70:
                gotreply = True
                replytext = str(row[1])

    if gotreply==False:
        replytext = "Jake was not able to answer your query. Our agents will reach you soon."

    print("what caller said--------", message)
    print("reply text is ------", replytext)
    
    msgBody = "Hi! This is Jake from State farm. Answer to your query - " + replytext

    return msgBody

def new_session():
    response = service.create_session(
        assistant_id=config["ibm_assistant"]["assistant_id"]
    ).get_result()
    print(json.dumps(response, indent=2))
    session = response["session_id"]
    return session
