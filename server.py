import zmq
import sys
import time
import threading
import subprocess



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
            {0: (5000, 5011)} means that the server 0 has two ports: 5000 for sending messages and 5011 for receiving messages.
        """

        if consistency_level not in ["sequential", "eventual", "causal", "linearizability"]:
            raise ValueError("The consistency level must be one of the following: sequential, eventual, causal, linearizability.")
        if num_servers != len(port_number):
            raise ValueError("The number of servers must be equal to the number of ports.")
        
        self.num_servers = num_servers
        self.consistency_level = consistency_level
        self.servers = []
        self.port_number = port_number


    def create_server(self, server_number, port_number):
        """
        Create a server with the given server number and port number.
        """
        server = Server(server_number, port_number, self.consistency_level, self.port_number)
        self.servers.append(server)



class Server:
    """
    This class represents a server in the cluster. It is responsible for handling the requests from the clients and other servers.
    It will handle the following requests from the clients:
    - set(key, value)
    - get(key)

    It will handle the following requests from the other servers: # TODO: this is the critical part
    - update(key, value)
    """
    def __init__(self, server_number, port_number, consistency_level, contacts):
        """
        The server need to initialize the key-value store and the sockets for sending and receiving messages.
        The contacts contains port numbers of the other servers in the cluster.
        """
        self.kv_store = {}
        self.server_number = server_number
        self.recv_port, self.send_port = port_number
        self.consistency_level = consistency_level


