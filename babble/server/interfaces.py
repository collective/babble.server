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
        """

    def addChatRoomParticipant(self, username, password, path, participant):
        """ Add another user as a participant in a chat room
        """

    def editChatRoom(self, username, password, id, participants):
        """ To be used to add/remove multiple participants 
        """

    def removeChatRoom(self, username, password, id):
        """ """

    def confirmAsOnline(self, username):
        """ Confirm that the user is currently online by updating the 'user
            access dict'

            returns {'status': int}
        """

    def register(self, username, password):
        """ Register a user with the babble.server's acl_users and create a
            'User' object in the 'Users' folder

            returns {'status': int}
        """

    def isRegistered(self, username):
        """ Check whether the user is registered via babble.server's acl_users 
        
            returns {'status': int, 'is_registered': bool}
        """


    def setUserPassword(self, username, password):
        """ Set the user's password 

            returns {'status': int}
        """

    def getOnlineUsers(self):
        """ Determine the (probable) online users from the 'user access dict' 
            and return them as a list

            returns {'status': int, 'online_users': list}
        """

    def sendMessage(self, username, password, fullname, recipient, message):
        """ Sends a message to recipient

            returns {'status': string, 'last_msg_date': date}
        """

    def getMessages(self, username, password, sender, since, until, cleared, mark_cleared):
        """ Returns messages within a certain date range

            Parameter values:
            -----------------
            sender: None or string
                If None, return from all senders.

            since: iso8601 date string or None
            until: iso8601 date string or None

            cleared: None/True/False
                If True, return only cleared messages.
                If False, return only uncleared once.
                Else, return all of them.

            mark_cleared: True/False
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

