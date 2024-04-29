import zmq
import sys
import json
import time
import random
import threading
from collections import defaultdict
import heapq



if __name__ == '__main__':
    client_number, server_number, requests, port_number = sys.argv[1:]
    # client_number = int(client_number)
    # server_number = int(server_number)
    port_number = eval(port_number)
    requests = eval(requests)
    # print(requests)
    

    context = zmq.Context()
    socket = context.socket(zmq.REQ)
    socket.connect(f"tcp://localhost:{port_number[server_number][2]}")
    print(f"Client {client_number} is connected to the server {server_number}")

    for request in requests:
        if request["type"] == "sleep": # we emulate a slow network by introducing delay
            duration = random.random() 
            print(f"Client {client_number} is sleeping for {duration} seconds")
            time.sleep(duration)
        else:
            socket.send_json({"type": request["type"],
                                "key": request["key"], 
                                "value": request["value"]})
            print(f"Client {client_number} sent request: {request}, waiting for response...")
            response = socket.recv_string()
            # while 1:
            #     response = socket.recv_string(zmq.NOBLOCK)
            #     if response == "ping":
            #         socket.send_string("pong")
            #     else:
            #         socket.send_string("gotcha")
            #         break
            
            # the feedback will be displayed in green color!
            print(f"\033[32mClient {client_number} received response: {response}\033[0m")

    




