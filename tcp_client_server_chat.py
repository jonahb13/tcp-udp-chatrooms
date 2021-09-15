"""
Server-Client Chat System using TCP 
"""

import asyncio
import argparse
import struct
from datetime import datetime


async def recv_formatted_data(reader, frmt):
    """
    Receives struct-formatted data from the given reader according to the struct format given and
    returns a tuple of values.
    """
    data = await reader.read(struct.calcsize(frmt))
    return struct.unpack(frmt, data)


async def recv_single_value(reader, frmt):
    """
    Receives a single value from the given reader according to the struct format given and returns
    it.
    """
    single_value = await recv_formatted_data(reader, frmt)
    return single_value[0]


async def recv_str(reader):
    """
    Receives a string using the reader. The string must be prefixed with its length and encoded.
    """
    length = await recv_single_value(reader, '<i')
    data = await reader.read(length)
    return data.decode()


async def recv_str_list(reader):
    """
    Receives a list of strings from the reader. The list is prefixed with the length and each string
    is prefixed with recv_str().
    """
    length = await recv_single_value(reader, "<i")
    return [await recv_str(reader) for _ in range(length)]


def send_single_value(writer, frmt, value):
    """
    Sends a single value using the given writer according to the struct format given.
    """
    writer.write(struct.pack(frmt, value))


def send_str(writer, string):
    """
    Sends a string using the given writer. The string is encoded then prefixed with the length as a 4-byte
    integer.
    """
    string = string.encode()
    data = struct.pack('<i', len(string))
    data += struct.pack(str(len(string)) + 's', string)
    writer.write(data)


def send_str_list(writer, strings):
    """
    Sends a list of strings using given writer. The list is prefixed with its length as a 4-byte
    integer. Each string is send with send_str().
    """
    length = struct.pack('<i', len(strings))
    writer.write(length)
    for string in strings:
        send_str(writer, string)


class ClientTCP():
    """
    Client that can connect to TCP chat system server. Clients provide a username, and upon a successful 
    connection, they receive recent chat history. Clients are free to chat with others on the server.
    """
    
    async def start_chatting(self, reader, writer):
        """
        Connect to the server at addr:port and start chatting in chatroom.
        """

        # Initial communication to the server, saying that you are about to send your username
        # to check if it is valid
        send_single_value(writer, '<i', 471)
        await writer.drain()

        # Client sends a string, being their username for the chat room, to the server
        username = input('Enter your username for the chatroom: ')
        send_str(writer, username)
        await writer.drain()

        # If false is received, connection is aborted
        try:
            status = await recv_single_value(reader, '<?')
            if status == False:
                writer.close()
                return
        # If anything goes wrong in Entering username (?)
        except (KeyboardInterrupt, Exception):
            print('Exception during Entering username')
            writer.close()
            return

        # Receive an integer and if it follows protocol, receive the history list
        response = await recv_single_value(reader, '<i')
        if response == 371:
            past_messages_num = await recv_single_value(reader, '<i')
            if past_messages_num == 0:
                pass
            else:
                for message in range(past_messages_num):
                    past_message = await recv_str_list(reader)
                    message_data = '%s %s: %s' % (past_message[0], past_message[1], past_message[2])
                    print(message_data)
        return username


    async def send_message(self, writer, username):
        """
        Send a message in the chatroom. Message is sent to the server
        to handle sending it to all clients. 
        """
        loop = asyncio.get_running_loop()
        while True:
            message = await loop.run_in_executor(None, input)
            local_time = datetime.now()
            str_time = local_time.strftime("%H:%M:%S")
            # Client disconnects when 'enter' is pressed in the chat
            if not message:
                print('You left the chatroom. Goodbye.')
                return
            send_single_value(writer, '<i', 472)
            send_str_list(writer, [str_time, username, message])
            await writer.drain()


    async def recv_new_message(self, reader):
        """
        Receive a new message from the server that was sent from any client in the chatroom.
        """
        while True:
            try:
                new_message_response = await recv_single_value(reader, '<i')
            except Exception:
                break
            else:
                if new_message_response == 372:
                    message = await recv_str_list(reader)
                    # Print out the received message.
                    print(message[0], message[1] + ':', message[2])


    async def connect_to_server(self):
        """
        Open a connection to the server and attempt to start chatting in the 
        chatroom, and sending/receiving new messages.
        """
        reader, writer = await asyncio.open_connection('googlecloud.cslab.moravian.edu', 42069)

        valid_username = await self.start_chatting(reader, writer)
        if not valid_username:
            return

        sending_messages = asyncio.create_task(self.send_message(writer, valid_username))
        receiving_messages = asyncio.create_task(self.recv_new_message(reader))

        await sending_messages
        receiving_messages.cancel()
        try:
            await receiving_messages
        except asyncio.exceptions.CancelledError:
            pass


class ServerTCP():
    """
    TCP Chat System Server that listens for and accepts incoming connections from any number of simultaneous clients.
    New clients are provided recent chat history (up to 10 messages) and are free to chat with other clients.
    """

    def __init__(self):
        """
        Python constructor that initializes lists of writers, current usernames, 
        and recent messages.
        """
        self.WRITERS = [] # list of all writers currently connected
        self.USERNAMES_LIST = []  # contains tuples, each one containing the time, username and message
        self.RECENT_MESSAGES = [] # up to 10 recent chat messages 

    def get_history(self):
        """
        Getter method for the chat history.
        """
        return self.RECENT_MESSAGES

    def update_history(self, time,username,message):
        """
        This method has to add the three stings (username, time, text) to the table and remove the oldest one.
        """
        new_message = (time, username, message)
        if len(self.RECENT_MESSAGES) >= 10:
            self.RECENT_MESSAGES.pop(0)
        self.RECENT_MESSAGES.append(new_message)

    def send_history(self, writer, history):
        """
        Send the chat history to a new client connecting
        to the chatroom.
        """
        send_single_value(writer, '<i', 371)
        send_single_value(writer, '<i', len(history))
        if len(history) != 0:
            for message in history:
                send_str_list(writer, message)

    def send_new_message(self, message_info):
        """
        When a new message is received from a client, this function is called to
        send the message to all clients.
        """
        for writer in self.WRITERS:
            try:
                send_single_value(writer, '<i', 372)
            except KeyboardInterrupt:
                pass
            else:
                send_str_list(writer, message_info)

    async def run_server(self):
        """
        Start the server running on the given port. The server accepts clients, handles their requests,
        then goes back to accept another client (i.e. it has an infinite loop). To handle requests this
        calls the server_handle_request() function. If a client causes a problem it is reported then the
        server keeps going (i.e. if server_handle_request() raises any exception it is printed and then
        the next client is accepted).
        """
        server = await asyncio.start_server(self.server_handle_request, '', 42069)
        async with server:
            await server.serve_forever()

    async def server_handle_request(self, reader, writer):
        """
        Handles client requests using the reader and writer that were initialized
        from asyncio.start_server().
        """
        # Add new writer to the list of writers
        self.WRITERS.append(writer)
        user_info = ()
        while True:
            try:
                protocol_num = await recv_single_value(reader, '<i')
            except struct.error:
                break
            # New client is joining the chat room
            if protocol_num == 471:
                client_username = await recv_str(reader)
                for client_id in self.USERNAMES_LIST:
                    if client_username == client_id[1]:
                        send_single_value(writer, '<?', False)
                        self.WRITERS.remove(writer)
                        await writer.drain()
                        writer.close()  # close
                        return
                # Send True to the client to confirm that the name is available
                send_single_value(writer, '<?', True)
                await writer.drain()
                # Add new user to the list of active users
                addr = writer.get_extra_info('peername')[0]
                new_user = (addr, client_username)  # address, username
                user_info = new_user
                self.USERNAMES_LIST.append(new_user)
                # Send message history to the new client
                self.send_history(writer, self.get_history())
                await writer.drain()
            # The client wants to send a new message in the chatroom
            if protocol_num == 472:
                try:
                    # Get the list of username, time and message
                    message_info = await recv_str_list(reader)
                except (KeyboardInterrupt, Exception):
                    break
                # Send the message to all clients, and update the history
                else:
                    self.send_new_message(message_info)
                    await writer.drain()
                    time = message_info[0]
                    username = message_info[1]
                    message = message_info[2]
                    self.update_history(time, username, message)
        # Remove user and writer from lists, and close the writer 
        self.USERNAMES_LIST.remove(user_info)
        self.WRITERS.remove(writer)
        writer.close()
        

async def main():
    """
    The main function uses an Argument Parser to get the command-line arguments and then calls ones
    of the functions: run_server() or connect_to_server().
    """
    parser = argparse.ArgumentParser(description='Interact with TCP client-server chatroom')
    subparsers = parser.add_subparsers(title='command', dest='cmd', required=True)
    subparsers.add_parser(name='server', description='run the server')
    subparsers.add_parser(name='client', description='connect to chatroom as a client')
    args = parser.parse_args()
    if args.cmd == 'server':
        server = ServerTCP()
        await server.run_server()
    if args.cmd == 'client':
        client = ClientTCP()
        await client.connect_to_server()

asyncio.run(main())
