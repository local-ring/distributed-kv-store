import zmq
import sys
import time
import threading
import subprocess
import json


"""
Here we implement distributed key-value store server with different consistency levels. The consistency schemes we implement are:
- sequential consistency
- eventual consistency
- causal consistency
- linearizability
"""


class Cluster:
    """
    This class represents a cluster of servers. It is responsible for creating the server with the given consistency level and port number.
    We need a fully connected network of servers to implement consistency levels. That is, each server has two sockets: 
    - sending messages to other servers
    - receiving messages from other servers

    Furthermore, each server need another socket to communicate with the clients.
    """
    def __init__(self, consistency_level, num_servers, port_number):
        """
        consistency_level: str
            The consistency level of the servers in the cluster. It can be one of the following:
            - sequential
            - eventual
            - causal
            - linearizability
        num_servers: int
            The number of servers in the cluster.
        port_number: dict
            A dictionary where the key is the server number and the value is the port numbers of the server. For example:
            {0: (5000, 5011, 5012)} means that the server 0 has three ports: 
            - 5000 for sending messages and 
            - 5011 for receiving messages.
        """

        if consistency_level not in ["sequential", "eventual", "causal", "linearizability"]:
            raise ValueError("The consistency level must be one of the following: sequential, eventual, causal, linearizability.")
        if num_servers != len(port_number):
            raise ValueError("The number of servers must be equal to the number of ports.")
        
        self.num_servers = num_servers
        self.consistency_level = consistency_level
        self.servers = []
        self.port_number = port_number
        self.processes = []

        for i in port_number:
            server_process = subprocess.Popen(['python', 
                                               "server.py", 
                                               str(i), 
                                               str(port_number),
                                               consistency_level],
                            )
            self.processes.append(server_process)

    def _destroy(self):
        for process in self.processes:
            process.kill()



if __name__ == '__main__':
    test_path = sys.argv[1] # get the path of test configuration file
    with open(test_path, 'r') as f:
        test = json.load(f)

    """
    The test configuration file should have the following format:
    - num_servers: int
    - consistency_level: str
    - port_number: dict
    - clients: list of dict of each client's configuration
        e.g. {"client_number": int, "requests": list of dict of each request's configuration, "server_number": int}
        - client_number: int (its clinet id)
        - requests: list of dict of each request's configuration
            e.g. {"type": str, "key": str, "value": int}
            - type: str (get or set)
            - key: str
            - value: int
        - server_number: int (the server id to which the client is connected)  
    """

    cluster = Cluster(test["consistency_level"], test["num_servers"], test["port_number"])

    time.sleep(2) # wait for the servers to be ready

    client_processes = []

    try:
        for client in test["clients"]:
            client_process = subprocess.Popen(['python', 
                                            "client.py", 
                                            str(client["client_number"]), 
                                            str(client["server_number"]),
                                            str(client["requests"]),
                                            str(test["port_number"])]
                                            )
            client_processes.append(client_process)
    finally:
        for process in client_processes:
            process.kill()
        cluster._destroy()
    
        
    

