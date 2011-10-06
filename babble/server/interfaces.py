from zope.interface import Interface 
from zope import schema

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

    def _getUser(self, username, auto_register=True):
        """ Retrieve the IUser obj from the 'Users' folder.
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

    def setStatus(self, username, status):
        """ Set the user's status.

            The user might have a status such as 'available', 'chatty', 
            'busy' etc. but this only applies if the user is actually 
            online, as determined from the 'user access dictionary'.

            The 'status' attribute is optional, it depends on the chat client 
            whether the user's 'status' property is at all relevant 
            and being used.

            returns {'status': int}
        """

    def getStatus(self, username):
        """ Get the user's status.

            The user might have a status such as 'available', 'chatty', 
            'busy' etc. but this only applies if the user is actually 
            online, as determined from the 'user access dictionary'.

            The 'status' attribute is optional, it depends on the chat client 
            whether the user's 'status' property is at all relevant 
            and being used.

            returns {'status': int, 'userstatus': string}
        """

    def sendMessage(self, username, password, recipient, message):
        """ Sends a message to recipient

            A message is added to the messagebox of both the sender and
            recipient.

            returns {'status': string}
        """

    def getUnclearedMessages(
                        self, 
                        username, 
                        password,
                        sender, 
                        since,
                        clear=False,
                        ):
        """ Returns the uncleared messages since a certain date.

            The 'since' date format must be iso8601, which is also the format
            of the returned timestamp.
            
            If sender is none, return all uncleared messages, otherwise return
            only the uncleared messages sent by that specific sender.

            If clear=True, then mark the messages as being cleared.
        """


class IUser(Interface):
    """ A user using the babble.server """

    def _getMessageBox(self, owner):
        """ The MessageBox is a container inside the 'User' object that stores
            the messages sent and received by that user.
        """

    def setStatus(self, status):
        """ Sets the user's status """

    def getStatus(self):
        """ Returns the user's status """

    def addMessage(self, contact, message, author, timestamp):
        """ Add a message to this user's contact's messagebox
            
            The message author could be either the user or the
            contact (conversation partnet), and is therefore passed 
            as a separate var.
        """

    def getMessages(self, username, password, since):
        """ Return all messages since a certain date, as well as the timestamp 
            of the newest message.

            The 'since' date format must be iso8601, which is also the format
            of the returned timestamp.
            
            To generate a date in this format, use the ISO8601() method for
            Zope2 DateTime objects and isoformat() for python's builtin
            datetime types.

            It's very important that timezone information is also included!
            I.e datetime.now(utc) instead of datetime.now()
        """

    def getUnclearedMessages(self, sender, since, clear=False):
        """ Return uncleared messages in list of dicts with senders as keys. 

            The date format of 'since' must be iso8601. 

            If a sender is specified, then return only the messages sent by
            him/her.

            If clear=True, then mark them as cleared. Messages are usually marked
            as cleared when the chat session is over.
        """


class IMessageBox(Interface):
    """ A container for messages """

    def addMessage(self, message, author, timestamp):
        """ Add a message to the MessageBox """


class IMessage(Interface):
    """ A message in a message box """

    author = schema.Text(
        title=u"Message Author",
        required=True,)

    text = schema.Text(
        title=u"Message Body",
        required=True,)

    time = schema.Datetime(
        title=u"Timestamp for the message",
        required=True,)

    def uncleared(self):
        """ Has this message been cleard? """

    def markAsCleared(self):
        """ Mark this message as cleared """
