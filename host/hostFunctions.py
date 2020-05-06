import time
import sys
sys.path.append('../')
import commonFunctions
from socket import *
import struct
import select
import random
import asyncore
import threading
import subprocess
import json

sendSem = threading.Semaphore()
recSem = threading.Semaphore()

def createHelloPacket(pkttype, seq, src):
    """
    Create a new packet based on given id
    """
    # Type(1), SEQ(4), SRCID(1) 
    hello = struct.pack('BBB', pkttype, seq, src)
    return hello

def sendHelloPacket(my_addr, pkt, dst, myLink, myID):
    helloAckFlag = False
    #extract the array of connected devices
    connectedDevice = myLink[str(myID)]
    #my_socket = socket(AF_INET, SOCK_DGRAM)    
    #my_socket.settimeout(4)
    print("Socket Timeout Set")

    while (not helloAckFlag):

        sendSem.acquire()

        my_socket = socket(AF_INET, SOCK_DGRAM)
        my_socket.setsockopt(SOL_SOCKET, SO_BROADCAST, 1) 
        my_socket.sendto(pkt, (dst, 8888))
        my_socket.close()

        sendSem.release()

        print("Sent packet to the destination: " + dst)
        #send_packet(pkt, dst)
        print("Hello Sent, waiting for ACK")
        time.sleep(1)
        #my_socket.bind((my_addr, 8889))

        recSem.acquire()

        my_socket = socket(AF_INET, SOCK_DGRAM)   
        my_socket.settimeout(4)
        my_socket.bind((my_addr, 8888))
        #Hello ACK type set as 4, listening to hear this value
        try:
            print("Listening for Hello ACK")
            data, addr = my_socket.recvfrom(1024)
            pktType = decodePktType(data)

            recSem.release()

            if (pktType[0] == 4):
                print("Hello ACK Received")
                print("Network joined")
                #take returned address, turn it into a code, append it to our linkstate
                #this is a janky solution... but it works in this implimentation, so we leave it
                rID = addr[0][10:13]
                connectedDevice.append(rID)
                graphUpdate = {str(myID): connectedDevice}
                myLink.update(graphUpdate)
                helloAckFlag = True
        except:
            recSem.release()
            continue
    return data, addr, myLink

def send_packet(pkt, dst_addr):
    """
    Sends a packet to the dest_addr using the UDP socket
    """
    my_socket = socket(AF_INET, SOCK_DGRAM)
    my_socket.sendto(pkt, (dst_addr, 8888))
    my_socket.close()
    print("Sent packet to the destination: ", dst_addr)
    return 0

def receive_packet(my_addr, port_num):
    """
    Listens at an IP:port
    """
    recSem.acquire()
    my_socket = socket(AF_INET, SOCK_DGRAM)
    my_socket.bind((my_addr, port_num))
    while True:
        data, addr = my_socket.recvfrom(1024)
        #print("Received packet", data, "from source", addr)
        recSem.release()
        break
    return data

def decodePktType(pkt):
    pktType = pkt[0:1]
    pkttype = struct.unpack('B', pktType)
    return pkttype 

def broadcastLinkState(myID, broadcastIP, myLink):

    #create the link state packet
    pktType = 2
    length = 1
    src = int(myID)
    data = json.dumps(myLink)
    data = bytes(data).encode('utf-8')

    pkt = struct.pack('BiiB', pktType, 1, len(data), src)+data
    try:
        sendSem.acquire()
        my_socket = socket(AF_INET, SOCK_DGRAM)
        my_socket.setsockopt(SOL_SOCKET, SO_BROADCAST, 1) 
        my_socket.sendto(pkt, ('192.168.1.255', 8888))
        my_socket.close()
        sendSem.release()
        time.sleep(1)
    except:
        print("Send error, trying again")

    threading.Timer(10, broadcastLinkState, [myID, broadcastIP, myLink]).start()

def sendData(dataPkt, dst, myID):
    receivedACK = False
    #want to send packet and wait for response, if not in whatever time,
    #we send again...
    while not receivedACK: 
        #send lock
        sendSem.acquire()
        try:
            my_socket = socket(AF_INET, SOCK_DGRAM)
            my_socket.sendto(dataPkt, (commonFunctions.convertID(dst), 8888))
            my_socket.close()
            print("Sent Data Packet")
            sendSem.release()
        except:
            print("Failed data send, trying again")
            sendSem.release()
            continue
        #setup timed listen for response. 
        recSem.acquire()
        print("Waiting to receive data ACK")
        try:
            my_socket = socket(AF_INET, SOCK_DGRAM)
            my_socket.settimeout(4)
            my_socket.bind(('0.0.0.0', 8888))
            data, addr = my_socket.recvfrom(1024)
            recSem.release()
            print("Data:")
            print(data)
            if(decodePktType(data)[0] == 8):
                print("Got data ACK")
                receivedACK = True
                recSem.release()
                return 1
        except:
            print("Didn't get Data ACK, trying again")
            recSem.release()