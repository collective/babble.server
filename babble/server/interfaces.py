from zope.interface import Interface 

class IChatService(Interface):
    """ 
        All the public methods return JSON dicts. Each JSON dict will have a
        'status' field, that can contain one of the following integer values:

        0: Success
        -1: Authorization failed
    """

    def _getUserAccessDict(self):
        """ The user access dictionary is stored inside a Temporary Folder.
            A Temporary Folder is kept in RAM and it loses all its contents 
            whenever the Zope server is restarted.

            The 'user access dictionary' contains usernames as keys and the
            last date and time that these users have been confirmed to be 
            online as the values.

            These date values can be used to determine (guess) whether the 
            user is still currently online.
        """

    def _getUsersFolder(self):
        """ The 'Users' folder is a BTreeFolder that contains IUser objects.
            See babble.server.interfaces.py:IUser
        """

    def _authenticate(self, username, password):
        """ Authenticate the user with username and password """

    def _isOnline(self, username):
        """ Determine whether the user is (probably) currently online

            Get the last time that the user updated the 'user access dict' and
            see whether this time is less than 1 minute in the past.

            If yes, then we assume the user is online, otherwise not.
        """

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

    def sendMessage(self, username, password, recipient, message):
        """ Sends a message to recipient

            A message is added to the messagebox of both the sender and
            recipient.

            returns {'status': string}
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

    def addMessage(self, message, author, fullname):
        """ Add a message to the Conversation """


class IChatRoom(Interface):
        """ """ 

class IMessage(Interface):
    """ A message in a message box """

