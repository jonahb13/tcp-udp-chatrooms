# Chat Room Implementations

## Client/Server Chat Room Using TCP

Protocol:

* Client sends the protocol number as an integer, being 471, to the server. Client then sends a string, being their desired username for the chatroom
    * If the server receives the protocol number and it is equal to 471, then it receives the client’s username as a string
        * Server sends false to client if their username is already taken, and their connection is terminated
        * Server sends true to client if their username is available
            * If available, server sends an integer, 371, to client, an integer representing how many lists it will be sending, and up to 10 lists containing a time (as a string), username (as a string) and message (as a string) 
* Once the client is up to date with all recent messages, it can now send new messages or/and receive messages from other clients
    * If a client sends a message in the chatroom, an integer, 472, and a list containing the time (as a string), username (as a string) and message (as a string) to the server
    * Server sends an integer, 372, then the list containing the time (as a string), username (as a string) and the user’s new message (as a string), to all clients

Note: Strings are sent as a 4-byte integer for the string length (after encoding) then the encoded string data. Lists of strings are sent as a 4-byte integer for the list length then each string is sent as above. 

## P2P Chat Room Using UDP

Protocol:

* New peer broadcasts a pickled dictionary containing: protocol number of 471 (as an integer), username being the new username of the client (as a string), and an empty string for the message
    * Once a new message is unpickled:
        * If a peer has the same username, they send a 370 to the new peer and their connection is terminated
        * If a peer does not have the same username, they send a pickled dictionary containing: protocol number of 371 (as an integer), username being the user’s new name (as a string), and the message being the chat history back to the new peer (as a list of strings)
* When a client sends a new message in the chat, the client broadcasts a picked dictionary containing: protocol number of 472 (as an integer), username being their name in the chatroom (as a string), and the message being the new message that they sent (as a string)

Note: This protocol uses Pickle protocol version 5, which was added in Python 3.8. Note that pickle can only be used with python protocols.