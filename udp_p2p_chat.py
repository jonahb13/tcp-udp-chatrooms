"""
P2P Chat System using UDP
"""

import asyncio
from datetime import datetime
import pickle
import socket

PORT = 5238

def get_ip():
    """Gets the local IP of the current machine."""
    with socket.socket(socket.AF_INET, socket.SOCK_DGRAM) as s:
        try:
            s.connect(('10.255.255.255', 1)) # random IP address, doesn't have to be reachable
            return s.getsockname()[0] # get the outgoing IP address on the machine
        except:
            return '127.0.0.1'

class ChatProtocol(asyncio.DatagramProtocol):
    
    USERNAME = ""
    NEW_USER = True
    BROADCAST = ("255.255.255.255", PORT)
    RECENT_MESSAGES = []
    
    def __init__(self):
        """Python constructor."""
        # Set user info and port 
        self.USERNAME = input("Enter your username for the chatroom: ")
        self.on_con_lost = asyncio.get_running_loop().create_future()
        
    def format_message(self, username, message):
        """Format a new message to be printed."""
        current_time = datetime.now().strftime("%H:%M:%S")
        return '> %s %s: %s' % (current_time, username, message)
    
    def pack_message(self, protocol_num, username, message):
        """Pickle a message to be sent."""
        return pickle.dumps({"protocol_num" : protocol_num, "username" : username, "message" : message})
    
    def unpack_message(self, message_data):
        """Unpickle a message that was received."""
        return pickle.loads(message_data)
        
    def send_history(self, username, addr):
        """Check if username is valid. If valid, send the message history to 
        the new peer. Otherwise, tell the peer that the username is taken."""
        if username != self.USERNAME:
            response = self.pack_message(371, self.USERNAME, self.RECENT_MESSAGES)
        else:
            response = self.pack_message(370, "", "")
        self.transport.sendto(response, (addr[0], PORT))

    def connection_made(self, transport):
        """Method called when the connection is initially made."""
        self.transport = transport        
        # Starts getting messages as a task in the asyncio loop
        asyncio.create_task(self.get_messages())

    async def get_messages(self):
        """
        Loop forever getting new inputs from the user and then broadcasting them.
        If the input is the empty string (i.e. just an enter) than it stops the program.
        """
        loop = asyncio.get_running_loop()
        # Broadcast new user's name to all other chatters
        new_name = self.pack_message(471, self.USERNAME, "")
        self.transport.sendto(new_name, self.BROADCAST)
        while True:
            # Get the message from the user
            message = await loop.run_in_executor(None, input)
            if not message:
                self.transport.close()
                break
            # Broadcast a new message
            new_message = self.pack_message(472, self.USERNAME, message)
            self.transport.sendto(new_message, self.BROADCAST)

    def connection_lost(self, exc):
        """Method called whenever the transport is closed."""
        self.on_con_lost.set_result(True)

    def datagram_received(self, data, addr):
        """Method called whenever a datagram is recieved."""
        # Unpack the user's new message
        message_data = self.unpack_message(data)
        protocol_num = message_data["protocol_num"]
        username = message_data["username"]
        message = message_data["message"]
        
        if protocol_num == 370: # If you do not have a valid username
            self.transport.close()
        if protocol_num == 371: # If you have a valid username
            if self.NEW_USER == True:
                self.RECENT_MESSAGES = message
                for message in self.RECENT_MESSAGES:
                    print(message)
                self.NEW_USER = False
        if protocol_num == 471: # If the message contains the username of a new chatter
            if addr[0] != get_ip():
                self.send_history(username, addr)
        if protocol_num == 472: # If you receive a new message in the chat
            new_message = self.format_message(username, message)
            if len(self.RECENT_MESSAGES) >= 10:
                self.RECENT_MESSAGES.pop(0)
            self.RECENT_MESSAGES.append(new_message)
            print(new_message)

    def error_received(self, exc):
        """Method called whenever there is an error with the underlying communication."""
        print('Error received:', exc)

async def main():
    # Setup the socket we will be using - enable broadcase and recieve message on the given port
    # Normally, this wouldn't be necessary, but with broadcasting it is needed
    sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    sock.setsockopt(socket.SOL_SOCKET, socket.SO_BROADCAST, True)
    sock.bind(('', PORT))
    
    # Create the transport and protocol with our pre-made socket
    # If not provided, you would instead use local_addr=(...) and/or remote_addr=(...)
    loop = asyncio.get_running_loop()
    transport, protocol = await loop.create_datagram_endpoint(ChatProtocol, sock=sock)

    # Wait for the connection to be closed/lost
    try:
        await protocol.on_con_lost
    finally:
        transport.close()

asyncio.run(main())
