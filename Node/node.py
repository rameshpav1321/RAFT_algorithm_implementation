import time
import math
import socket
import json
import os
import random
import threading

class Node:

    def __init__(self):
        if os.getenv("VERBOSE") == "True":
            self.verbose = True
        else:
            self.verbose = False
        self.currentTerm = 0
        self.votedFor = None
        self.log = []
        self.heartbeat = float(os.getenv("HEARTBEAT"))
        self.timeout = self.heartbeat * random.uniform(2.5, 3.5)
        self.leader = None
        self.sender = None
        self.alive = True
        self.listener = None
        self.name = os.getenv("NAME")
        self.udp_socket = None 
        self.send = False
        self.nodeList = json.loads(os.getenv("NODELIST"))
        self.nodeList.remove(self.name)
        self.currentTermVoteCount = 0
        self.udp_socket = socket.socket(family=socket.AF_INET, type=socket.SOCK_DGRAM)
        self.udp_socket.bind((self.name, 5555))
        self.state = "FOLLOWER"
        self.commitIndex = 0
        self.lastApplied = 0

    def appendToLog(self, msg):
        entry = {
            "term": self.currentTerm,
            "key": msg["key"],
            "value": msg["value"]
        }
        self.log.append(entry)
        self.commitIndex += 1
        print(entry)

    def sendLog(self, msg):
        sendmsg = self.generateMessage("COMMITTED_LOGS")
        self.udp_socket.sendto(sendmsg, (msg["sender_name"], 5555))

    def vprint(self, inp):
        if self.verbose:
            print(inp)

    def generateMessage(self, request):
        msg = {
                "sender_name": self.name,
                "term": self.currentTerm,
                "request": request,
                "key": None,
                "value": None
                }
        if request == "LEADER_INFO":
            msg["key"] = "LEADER"
            msg["value"] = self.leader
        elif request == "COMMITTED_LOGS":
            msg["request"] = "RETRIEVE"
            msg["key"] = "COMMITTED_LOGS"
            msg["value"] = json.dumps(self.log)
        elif request == "F":
            msg["key"] = "success"
            msg["value"] = "False"
            msg["request"] = "APPEND_REPLY"
        elif request == "T":
            msg["key"] = "success"
            msg["value"] = "True"
            msg["request"] = "APPEND_REPLY"
        return json.dumps(msg).encode() 

    def leaderSender(self):
        while self.send:
            for node in self.nodeList:
                msg = self.generateMessage("APPEND_RPC")
                if self.nextIndex[node] < len(self.log):
                    msg = json.loads(msg.decode())
                    msg["leaderCommit"] = self.commitIndex
                    msg["prevLogIndex"] = self.nextIndex[node] - 1
                    msg["prevLogTerm"] = self.log[self.nextIndex[node] - 1]["term"]
                    msg["entryTerm"] = self.log[self.nextIndex[node]]["term"]
                    msg["key"] = self.log[self.nextIndex[node]]["key"]
                    msg["value"] = self.log[self.nextIndex[node]]["value"]
                    msg = json.dumps(msg).encode()
                self.udp_socket.sendto(msg, (node, 5555))
            time.sleep(self.heartbeat)

    def candidateSender(self):
        self.currentTerm += 1
        for node in self.nodeList:
            msg = self.generateMessage("VOTE_REQUEST")
            self.udp_socket.sendto(msg, (node, 5555))

    def sendVote(self, node):
        msg = self.generateMessage("VOTE_ACK")
        self.udp_socket.sendto(msg, (node, 5555))

    def convertLeader(self):
        self.leader = self.name
        self.vprint("CURRENT LEADER IS: " + self.name)
        self.currentTermVoteCount = 0
        self.state = "LEADER"
        self.send = True
        self.nextIndex = {}
        for node in self.nodeList:
            self.nextIndex[node] = len(self.log)
        self.sender = threading.Thread(target=self.leaderSender)
        self.sender.start()
    
    def convertFollower(self):
        if self.state != "FOLLOWER":
            self.vprint(self.name + " CONVERTING BACK TO FOLLOWER")
            self.send = False
            self.currentTermVoteCount = 0
            self.state = "FOLLOWER"

    def convertCandidate(self):
        self.vprint(self.name + " IS BECOMING CANDIDATE")
        self.state = "CANDIDATE"

    def threadlessListener(self):
        while self.alive:
            curtime = time.time()
            endtime = time.time() + self.timeout
            msgcount = 0
            while curtime < endtime:
                self.udp_socket.settimeout(0)
                try: 
                    msg = self.udp_socket.recv(1024)
                    msg = json.loads(msg.decode())
                    if msg["request"] == "APPEND_RPC":
                        self.append_rpc(msg)
                    elif msg["request"] == "VOTE_REQUEST":
                        self.vote_request(msg)
                    elif msg["request"] == "VOTE_ACK":
                        self.vote_ack(msg)
                    elif msg["request"] == "CONVERT_FOLLOWER":
                        self.convert_follower(msg)
                    elif msg["request"] == "TIMEOUT":
                        self.timeOut(msg)
                    elif msg["request"] == "SHUTDOWN":
                        self.shutdown(msg)
                    elif msg["request"] == "LEADER_INFO":
                        self.leader_info(msg)
                    elif msg["request"] == "STORE":
                        self.store(msg)
                    elif msg["request"] == "RETRIEVE":
                        self.retrieve(msg)
                    elif msg["request"] == "APPEND_REPLY":
                        self.append_reply(msg)
                    msgcount += 1
                except BlockingIOError:
                    pass
                curtime = time.time()
            if self.state == "FOLLOWER":
                if msgcount == 0:
                    self.convertCandidate()
            elif self.state == "CANDIDATE":
                threading.Thread(target=self.candidateSender).start()
            self.timeout = self.heartbeat * random.uniform(2.5, 3.5)

    def append_reply(self, msg):
        if self.state == 'LEADER':
            if msg["key"] == "success" and msg["value"] == "True":
                self.nextIndex[msg["sender_name"]] = self.nextIndex[msg["sender_name"]] + 1
            elif msg["key"] == "success" and msg["value"] == "False":
                self.nextIndex[msg["sender_name"]] = self.nextIndex[msg["sender_name"]] - 1
        elif self.state == 'CANDIDATE':
            pass
        elif self.state == 'FOLLOWER':
            pass

    def store(self, msg):
        if self.state == 'LEADER':
            self.appendToLog(msg)
            self.sendLeader(msg)
        elif self.state == 'CANDIDATE':
            self.sendLeader(msg)
        elif self.state == 'FOLLOWER':
            self.sendLeader(msg)

    def retrieve(self, msg):
        if self.state == 'LEADER':
            self.sendLog(msg)
        elif self.state == 'CANDIDATE':
            self.sendLeader(msg)
        elif self.state == 'FOLLOWER':
            self.sendLeader(msg)

    def append_rpc(self, msg):
        if self.state == 'LEADER':
            pass
        elif self.state == 'CANDIDATE':
            self.convertFollower()
        elif self.state == 'FOLLOWER':
            if msg["term"] < self.currentTerm:
                return
            self.leader = msg["sender_name"]
            self.currentTerm = int(msg["term"])
            if msg["key"] and msg["value"]:
                if len(self.log) < int(msg["prevLogIndex"]):
                    self.reply_false(msg)
                    return
                elif 0 < int(msg["prevLogIndex"]) < len(self.log):
                    if int(self.log[int(msg["prevLogIndex"])]["term"]) != int(msg["prevLogTerm"]):
                        self.reply_false(msg)
                        return
                self.log = self.log[:int(msg["prevLogIndex"]) + 1]
                entry = {
                    "term": msg["entryTerm"],
                    "key": msg["key"],
                    "value": msg["value"]
                }
                self.log.append(entry)
                self.commitIndex += 1
                self.reply_true(msg)

    def reply_false(self, msg):
        sendmsg = self.generateMessage("F")
        self.udp_socket.sendto(sendmsg, (msg["sender_name"], 5555))

    def reply_true(self, msg):
        sendmsg = self.generateMessage("T")
        self.udp_socket.sendto(sendmsg, (msg["sender_name"], 5555))

    def vote_request(self, msg):
        if self.state == 'LEADER':
            pass
        elif self.state == 'CANDIDATE':
            if msg['term'] > self.currentTerm:
                self.currentTerm = msg["term"]
                self.votedFor = msg["sender_name"]
                self.sendVote(msg["sender_name"])
        elif self.state == 'FOLLOWER':
            if msg['term'] > self.currentTerm:
                self.currentTerm = msg["term"]
                self.votedFor = msg["sender_name"]
                self.sendVote(msg["sender_name"])

    def vote_ack(self, msg):
        if self.state == 'LEADER':
            pass
        elif self.state == 'CANDIDATE':
            self.currentTermVoteCount += 1
            if self.currentTermVoteCount > math.floor(len(self.nodeList) / 2) + 1:
                self.convertLeader()
        elif self.state == 'FOLLOWER':
            pass

    def convert_follower(self, msg):
        if self.state == 'LEADER':
            self.convertFollower()
        elif self.state == 'CANDIDATE':
            self.convertFollower()
        elif self.state == 'FOLLOWER':
            pass

    def timeOut(self, msg):
        if self.state == 'LEADER':
            pass
        if self.state == 'CANDIDATE':
            pass
        if self.state == 'FOLLOWER':
            self.convertCandidate()

    def shutdown(self, msg):
        self.alive = False

    def leader_info(self, msg):
        self.sendLeader(msg)

    def sendLeader(self, msg):
        sendmsg = self.generateMessage("LEADER_INFO")
        self.udp_socket.sendto(sendmsg, (msg["sender_name"], 5555))

if __name__ == "__main__":
    thisNode = Node()
    thisNode.threadlessListener()
