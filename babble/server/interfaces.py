from zope.interface import Interface 

class IChatService(Interface):
    """ 
        All the public methods return JSON dicts. Each JSON dict will have a
        'status' field, that can contain one of the following integer values:

        SUCCESS = 0
        AUTH_FAIL = -1
        TIMEOUT = 1
        ERROR = SERVER_FAULT = 2
        NOT_FOUND = 3
    """

    def createChatRoom(self, username, password, path, participants):
        """ Chat rooms, unlike members, don't necessarily have unique IDs. They
            do however have unique paths. We hash the path to get a unique id.

            username:       string
            password:       string
            path:           string  (path to the chatroom)
            participants:   list of strings
        """


    def addChatRoomParticipant(self, username, password, path, participant):
        """ Add another user as a participant in a chat room

            username:       string
            password:       string
            path:           string  (path to the chatroom)
            participants:   strings
        """

    def editChatRoom(self, username, password, id, participants):
        """ Set a chatroom's participants 
        
            username:       string
            password:       string
            id:             string  (the chat room's id)
            participants:   list of strings
        """

    def removeChatRoom(self, username, password, id):
        """ Delete a chatroom """

    def confirmAsOnline(self, username):
        """ Confirm that the user is currently online by updating the 'user
            access dict'
        """

    def register(self, username, password):
        """ Register a user with the babble.server's acl_users
        """

    def isRegistered(self, username):
        """ Check whether the user is registered via acl_users """

    def setUserPassword(self, username, password):
        """ Set the user's password """

    def getOnlineUsers(self):
        """ Determine and return the (probable) online users from the 'user access dict'.
        """

    def sendMessage(self, username, password, fullname, recipient, message):
        """ Sends a message to recipient
        
            username:   string
            password:   string
            fullname:   string (The sender's full name)
            recipient:  string (The message recipient)
            message:    string
        """

    def sendChatRoomMessage(self, username, password, fullname, room_name, message):
        """ Sends a message to a chatroom 
        
            username:   string
            password:   string
            fullname:   string (The sender's full name)
            room_name:  string (The chat room's name)
            message:    string
        """

    def getMessages(self, username, password, partner, chatrooms, since, until):
        """ Returns messages from conversation partners or chatrooms,  
            optionally within a certain date range.

            username:   string
            password:   string

            partner:    None or '*' or a username. 
                - None: ignore partners
                - *   : match all partners   

            chatrooms:  list of strings

            since: iso8601 date string or None 
            until: iso8601 date string or None
        """

    def getNewMessages(self, username, password, since):
        """ Get all messages since a certain date.
            
            username:   string
            password:   string
            since:      iso8601 date string or None

            If since=None, get all messages.
        """

    def getUnclearedMessages(self, username, password, partner, chatrooms, until, clear):
        """ Get all messages since the last clearance date. 
            Optionally mark them as cleared.

            username:   string
            password:   string

            partner: None or '*' or a string
                - None: ignore partners
                - *   : match all partners   
            chatrooms: '*' or list   
                - *   : match all chatrooms
            until: iso8601 date string or None
            clear: boolean
        """


class IUser(Interface):
    """ A user using the babble.server """

    def setStatus(self, status):
        """ Sets the user's status """

    def getStatus(self):
        """ Returns the user's status """


class IMessageBox(Interface):
    """ A container for messages """

    def addMessage(self, message, author, fullname):
        """ Add a message to the MessageBox """


class IConversation(Interface):
    """ A conversation between two or more users """

    def addMessage(self, text, author, fullname):
        """ Add a message to the Conversation """


class IChatRoom(Interface):
    """ """ 

    def addMessage(self, text, author, fullname):
        """ Add a message to the Chatroom """


class IMessage(Interface):
    """ A message in a message box """

