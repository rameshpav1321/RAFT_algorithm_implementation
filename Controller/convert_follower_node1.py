import json
import socket
import traceback
import time

# Wait following seconds below sending the controller request
time.sleep(5)

# Read Message Template


# Initialize
sender = "Controller"
target1 = "Node1"
target2 = "Node2"
target3 = "Node3"
target4 = "Node4"
target5 = "Node5"
port = 5555

# Request
msg = json.load(open("Message.json"))
msg['sender_name'] = sender
msg['request'] = "CONVERT_FOLLOWER"

# Socket Creation and Binding
skt = socket.socket(family=socket.AF_INET, type=socket.SOCK_DGRAM)
skt.bind((sender, port))

# Send Message
try:
    # Encoding and sending the message
    msg1 = json.load(open("Message.json"))
    msg1['sender_name'] = sender
    msg1['request'] = "STORE"
    msg1['key'] = "hi"
    msg1['value'] = "yes"

    skt.sendto(json.dumps(msg1).encode('utf-8'), (target1, port))
    dat1 = skt.recv(1024)
    if json.loads(dat1.decode())["value"] == target1:
        print("Data Stored in: ", json.loads(dat1.decode())["sender_name"])
    else:
        skt.sendto(json.dumps(msg1).encode('utf-8'), (json.loads(dat1.decode())["value"], port))
        time.sleep(0.5)
        dat1 = skt.recv(1024)
        print("Data Stored in: ", json.loads(dat1.decode())["sender_name"])

    time.sleep(5)

    skt.sendto(json.dumps(msg).encode('utf-8'), (target1, port))
    skt.sendto(json.dumps(msg).encode('utf-8'), (target2, port))
    skt.sendto(json.dumps(msg).encode('utf-8'), (target3, port))
    skt.sendto(json.dumps(msg).encode('utf-8'), (target4, port))
    skt.sendto(json.dumps(msg).encode('utf-8'), (target5, port))

    print("Leader Stopped")
    time.sleep(5)

    msg1['key'] = "uh"
    msg1['value'] = "can i get uh"

    skt.sendto(json.dumps(msg1).encode('utf-8'), (target1, port))
    dat2 = skt.recv(1024)
    if json.loads(dat2.decode())["value"] == target1:
        print("Data Stored in: ", json.loads(dat2.decode())["sender_name"])
    else:
        skt.sendto(json.dumps(msg1).encode('utf-8'), (json.loads(dat2.decode())["value"], port))
        time.sleep(0.5)
        dat2 = skt.recv(1024)
        print("Data Stored in: ", json.loads(dat2.decode())["sender_name"])

    time.sleep(2)

    msg2 = json.load(open("Message.json"))
    msg2['sender_name'] = sender
    msg2['request'] = "RETRIEVE"

    skt.sendto(json.dumps(msg2).encode('utf-8'), (target1, port))
    dat = skt.recv(1024)

    time.sleep(2)

    if json.loads(dat.decode())["request"] == "RETRIEVE":
        print("Data From: ", json.loads(dat.decode())["sender_name"], " Logs: ", json.loads(dat.decode())["value"])
    else:
        time.sleep(2)
        print(json.loads(dat.decode()))
        skt.sendto(json.dumps(msg2).encode('utf-8'), (json.loads(dat.decode())["value"], port))
        time.sleep(2)
        dat = skt.recv(1024)
        print("Data From: ", json.loads(dat.decode())["sender_name"], " Logs: ", json.loads(dat.decode())["value"])

except:
    #  socket.gaierror: [Errno -3] would be thrown if target IP container does not exist or exits, write your listener
    print(f"ERROR WHILE SENDING REQUEST ACROSS : {traceback.format_exc()}")

