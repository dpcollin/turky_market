import mimetypes
import os

import mechturk

from pymongo import MongoClient
from http.server import BaseHTTPRequestHandler, HTTPServer
from urllib.parse import urlparse, parse_qs

import datetime

import smtplib

import requests
import json

from apscheduler.schedulers.background import BackgroundScheduler

scheduler = BackgroundScheduler()

hostName = "localhost"
hostPort = 8000

client = MongoClient()

db = client.sale_database

offers = db.offers

global id_tracker
id_tracker = -1
for offer in offers.find():
    id_tracker = max(id_tracker,offer['_id'])

id_tracker += 1

def email(recipient, body):
    import smtplib

    gmail_user = ''
    gmail_pwd = ''
    FROM = gmail_user
    TO = recipient if type(recipient) is list else [recipient]
    SUBJECT = 'notification'
    TEXT = body

    # Prepare actual message
    message = """\From: %s\nTo: %s\nSubject: %s\n\n%s
    """ % (FROM, ", ".join(TO), SUBJECT, TEXT)
    try:
        server = smtplib.SMTP("smtp.gmail.com", 587)
        server.ehlo()
        server.starttls()
        server.login(gmail_user, gmail_pwd)
        server.sendmail(FROM, TO, message)
        server.close()
        print('successfully sent the mail')
    except:
        print("failed to send mail")

def escrowIn(value, fromid,txid):
    escrowID = '5700b86dcd7569fb1391ad41'
    apiKey = '61289aa0a4110a45e0f16980bcc2e91e'
    merchantID = '5700bc23cd7569fb1391c8de'

    payload = {
      "type": "Savings",
      "nickname": txid,
      "rewards": 10000,
      "balance": 0
    }

    url = 'http://api.reimaginebanking.com/customers/{}/accounts?key={}'.format(escrowID,apiKey)

    response = requests.post(
	url,
	data=json.dumps(payload),
	headers={'content-type':'application/json'},
	)

    res = response.json()

    card = res['objectCreated']['_id']

    payload2 = {
      "medium": "balance",
      "payee_id": card,
      "amount": value,
      "transaction_date": "2016-04-03",
      "status": "pending",
      "description": "escrow in"
    }

    url2 = 'http://api.reimaginebanking.com/accounts/{}/transfers?key={}'.format(fromid,apiKey)

    response2 = requests.post(
	url2,
	data=json.dumps(payload2),
	headers={'content-type':'application/json'},
	)

    return card

def escrowOut(value,cardid,toid):
    apiKey = '61289aa0a4110a45e0f16980bcc2e91e'

    payload = {
      "medium": "balance",
      "payee_id": toid,
      "amount": value,
      "transaction_date": "2016-04-03",
      "status": "pending",
      "description": "escrow out"
    }

    url = 'http://api.reimaginebanking.com/accounts/{}/transfers?key={}'.format(cardid,apiKey)

    response = requests.post(
	url,
	data=json.dumps(payload),
	headers={'content-type':'application/json'},
	)

def triggerIt(id):
    scheduler.remove_job(str(id))

    target = offers.find_one({"_id": id})

    if('buyerComplaint' in target):
        if('sellerComplaint' in target):
            return

    turk(id)

def turk(id):
    url = hostName + ":" + hostPort + "/turkit?id=" + str(id)
    res = mechturk.createhit(url,id)
    scheduler.add_job(lambda: mechturk.processhit(id), 'interval', hours=24, id=str(id + 10000))


class MyServer(BaseHTTPRequestHandler):

    def do_GET(self):
        global id_tracker
        self.send_response(200)
        x = urlparse(self.path)
        print('Trying to serve ' + x.path)
        if(x.path == '/'):
            self.send_header("Content-type", "text/html")
            self.end_headers()
            self.wfile.write(open('data/home.html', 'rb').read())
        elif(x.path == '/submittedSell'):
            params = parse_qs(x.query)
            params["date"] = datetime.datetime.utcnow()
            params["_id"] = id_tracker
            params["state"] = 0
            offers.insert_one(params)
            id_tracker += 1
            self.send_header("Content-type", "text/html")
            self.end_headers()
            self.wfile.write(open('data/submittedSell.html', 'rb').read())
        elif(x.path == '/buy'):
            self.send_header("Content-type", "text/html")
            self.end_headers()
            self.wfile.write(open('data/buy_open.html', 'rb').read())
            row_tracker = 0
            for offer in offers.find():
                if(offer['state'] == 0):
                    if(row_tracker == 0): self.wfile.write(open('data/buy_row_open.html', 'rb').read())
                    self.wfile.write(bytes("<div class=\"col-md-3\"><div class=\"thumbnail\"><img src=\"", 'utf-8'))
                    self.wfile.write(bytes(offer['link'][0], 'utf-8'))
                    self.wfile.write(bytes("\" class=\"img-responsive\">", 'utf-8'))
                    self.wfile.write(bytes("<div class=\"caption\"><h3><a href=\"purchase?id=", 'utf-8'))
                    self.wfile.write(bytes(str(offer['_id']), 'utf-8'))
                    self.wfile.write(bytes("\">", 'utf-8'))
                    self.wfile.write(bytes(offer['name'][0], 'utf-8'))
                    self.wfile.write(bytes(", $", 'utf-8'))
                    self.wfile.write(bytes(offer['price'][0], 'utf-8'))
                    self.wfile.write(bytes("</a></h3><p>", 'utf-8'))
                    self.wfile.write(bytes(offer['desc'][0], 'utf-8'))
                    self.wfile.write(bytes("<p>", 'utf-8'))
                    self.wfile.write(bytes("</div></div></div>", 'utf-8'))
                    if(row_tracker == 4): self.wfile.write(open('data/buy_row_close.html', 'rb').read())
                    row_tracker += 1
                    row_tracker %= 4
            if(row_tracker != 0): self.wfile.write(open('data/buy_row_close.html', 'rb').read())

            self.wfile.write(open('data/buy_close.html', 'rb').read())
        elif(x.path == '/purchase'):
            params = parse_qs(x.query)
            id = int(params['id'][0])
            offer = offers.find_one({"_id": id})
            self.send_header("Content-type", "text/html")
            self.end_headers()
            self.wfile.write(open('data/purchase_open.html', 'rb').read())
            self.wfile.write(bytes(offer['link'][0], 'utf-8'))
            self.wfile.write(bytes('\" class=\"img-responsive\"><h3 class=\"text-center\">','utf-8'))
            self.wfile.write(bytes(offer['name'][0],'utf-8'))
            self.wfile.write(bytes(", $", 'utf-8'))
            self.wfile.write(bytes(offer['price'][0], 'utf-8'))
            self.wfile.write(bytes("</h3><p>", 'utf-8'))
            self.wfile.write(bytes(offer['desc'][0],'utf-8'))
            self.wfile.write(bytes("</p>",'utf-8'))
            self.wfile.write(bytes('<hr></div><div class="col-md-6"><form role="form" action="purchase_successful" method="get"><input type="hidden" name="id" value="','utf-8'))
            self.wfile.write(bytes(str(id),'utf-8'))
            self.wfile.write(bytes('">','utf-8'))
            self.wfile.write(open('data/purchase_close.html', 'rb').read())
        elif(x.path == '/purchase_successful'):
            params = parse_qs(x.query)
            id = int(params['id'][0])
            params.pop('id')
            target = offers.find_one({"_id": id})
            target['state']=1
            escrowID = escrowIn(int(target['price'][0]),params['buyerCCN'][0],str(id))
            target['escrow'] = escrowID

            target.update(params)
            offers.replace_one({"_id": id},target)
            self.send_header('Content-type',"text/html")
            self.end_headers()
            self.wfile.write(open('data/purchase_successful.html', 'rb').read())
            email(target['sellerEmail'][0], 'Your Item with ID ' + str(id) + ' has been purchased. Log in to get the information necessary to send it.')
        elif(x.path == '/resolve'):
            params = parse_qs(x.query)
            type = int(params['Issue'][0])
            id = int(params['id'][0])
            params.pop('id')
            target = offers.find_one({"_id": id})
            password = params['pwd'][0]
            comment = params['summary'][0]
            link = params['link'][0]
            if(type == 0):
                if(password != target['sellerPass'][0]):
                    self.send_header('Content-type',"text/html")
                    self.end_headers()
                    self.wfile.write(open('data/error404.html', 'rb').read())
                    return
                target['track'] = comment
                offers.replace_one({"_id": id},target)

                email(target['buyerEmail'][0], 'Your Item with ID ' + str(id) + ' has just recieved tracking number ' + comment + '. It should arrive soon.')
                self.send_header('Content-type',"text/html")
                self.end_headers()
                self.wfile.write(open('data/resolve.html', 'rb').read())
            elif(type == 1):
                if(password != target['buyerPassword'][0]):
                    self.send_header('Content-type',"text/html")
                    self.end_headers()
                    self.wfile.write(open('data/error404.html', 'rb').read())
                    return

                escrowOut(int(target['price'][0]),target['escrow'],target['sellerCard'][0])

                email(target['sellerEmail'][0], 'Your Item with ID ' + str(id) + ' has been accepted; funds should arrive soon.')

                self.send_header('Content-type',"text/html")
                self.end_headers()
                self.wfile.write(open('data/resolve.html', 'rb').read())

            elif(type == 2):
                if(password != target['buyerPassword'][0]):
                    self.send_header('Content-type',"text/html")
                    self.end_headers()
                    self.wfile.write(open('data/error404.html', 'rb').read())
                    return

                target['buyerComplaint'] = True
                target['buyerSummary'] = comment
                target['buyerLink'] = link

                offers.replace_one({"_id": id},target)

                if('sellerComplaint' in target):
                    turk(id)
                else:
                    email(target['sellerEmail'][0], 'Your sale with ID ' + str(id) + ' has been disputedl; you have 3 days to respond or the case will be resolved without your input.')
                    scheduler.add_job(lambda: triggerIt(id), 'interval', hours=72, id=str(id))

                self.send_header('Content-type',"text/html")
                self.end_headers()
                self.wfile.write(open('data/resolve.html', 'rb').read())
            else:
                if(password != target['sellerPass'][0]):
                    self.send_header('Content-type',"text/html")
                    self.end_headers()
                    self.wfile.write(open('data/error404.html', 'rb').read())
                    return

                target['sellerComplaint'] = True
                target['sellerSummary'] = comment
                target['sellerLink'] = link

                offers.replace_one({"_id": id},target)

                if('buyerComplaint' in target):
                    turk(id)
                else:
                    email(target['buyerEmail'][0], 'Your purchase with ID ' + str(id) + ' has been disputed; you have 3 days to respond or the case will be resolved without your input.')
                    scheduler.add_job(lambda: triggerIt(id), 'interval', hours=72, id=str(id))

                self.send_header('Content-type',"text/html")
                self.end_headers()
                self.wfile.write(open('data/resolve.html', 'rb').read())


        elif(x.path == '/turkit'):
            params = parse_qs(x.query)
            id = int(params['id'][0])
            target = offers.find_one({"_id": id})
            self.send_header('Content-type',"text/html")
            self.end_headers()
            self.wfile.write(bytes('<p>','utf-8'))
            self.wfile.write(bytes(target['name'][0],'utf-8'))
            self.wfile.write(bytes(', $','utf-8'))
            self.wfile.write(bytes(target['price'][0], 'utf-8'))
            self.wfile.write(bytes('</p>','utf-8'))
            self.wfile.write(bytes('<a href="','utf-8'))
            self.wfile.write(bytes(target['link'][0],'utf-8'))
            self.wfile.write(bytes('">Initial Image Used</a>','utf-8'))
            self.wfile.write(bytes('<p>Buyer Info</p>','utf-8'))
            self.wfile.write(bytes('<p>','utf-8'))
            self.wfile.write(bytes(target['buyerSummary'],'utf-8'))
            self.wfile.write(bytes('</p>','utf-8'))
            self.wfile.write(bytes('<a href="','utf-8'))
            self.wfile.write(bytes(target['buyerLink'],'utf-8'))
            self.wfile.write(bytes('">Buyer Additional Info</a>','utf-8'))
            self.wfile.write(bytes('<p>Seller Info</p>','utf-8'))
            self.wfile.write(bytes('<p>','utf-8'))
            self.wfile.write(bytes(target['sellerSummary'],'utf-8'))
            self.wfile.write(bytes('</p>','utf-8'))
            self.wfile.write(bytes('<a href="','utf-8'))
            self.wfile.write(bytes(target['sellerLink'],'utf-8'))
            self.wfile.write(bytes('">Seller Additional Info</a>','utf-8'))

        else:
            path = 'data' + x.path
            if(len(path.split('.')) == 1):
                path = path + '.html'

            if(os.path.isfile(path)):
                mimetype, _ = mimetypes.guess_type(path)
                self.send_header('Content-type', mimetype)
                self.end_headers()
                self.wfile.write(open(path, 'rb').read())
            else:
                self.send_header("Content-type", "text/html")
                self.end_headers()
                self.wfile.write(open('data/error404.html', 'rb').read())


        print('Served ' + x.path)

myServer = HTTPServer((hostName, hostPort), MyServer)
print(datetime.datetime.utcnow(), "Server Starts - %s:%s" % (hostName, hostPort))


try:
    myServer.serve_forever()
except KeyboardInterrupt:
    pass

myServer.server_close()
print(datetime.datetime.utcnow(), "Server Stops - %s:%s" % (hostName, hostPort))
