from zope.interface import Interface 
from zope import schema

class IChatService(Interface):
    """ A basic babble.server """

    def register(username):
        """ register a user with the babble.server """

    def setUserProperty(username, name, value):
        """ set a property for a given user """

    def getUserProperty(username, name):
        """ get the property for a given user """

    def findUser(propname, value):
        """ Find a user on a value for a given property """

    def signIn(username):
        """ sign into message service """

    def signOut(username):
        """ sign out of message service """

    def isOnline(username):
        """ is user online """

    def sendMessage(username, recipient, message):
        """ send a message to a user """

    def getMessagesForUser(username, sender):
        """ get all the messages for a user from a given sender """

    def requestContact(username, contact):
        """ a request from user identified by 'username' to make contact
            with a contact identified by 'contact'
        """

    def approveContactRequest(username, contact):
        """ user identified by 'username' approves contact identified by
            'contact'
        """

    def declineContactRequest(username, contact):
        """ decline request to add user as contact """

    def removeContact(username, contact):
        """ remove existing contact from a user's contact list """

    def getPendingContacts(username):
        """ return a list of of all pending contacts """

    def getContactRequests(username):
        """ return a list of of all requests to be add as contact for a
            given user
        """

    def getContacts(username):
        """ return a list of of approved contacts """


class IUser(Interface):
    """ A user using the babble.server """

    def signIn(self):
        """ sign in """

    def signOut(self):
        """ sign out """

    def isOnline(self):
        """ is user online """

    def addMessage(recipient, message):
        """ add message for recipient """

    def getMessagesFromSender(sender):
        """ get messages from sender """

    def requestContact(contact):
        """ make request to add user as contact """

    def approveContactRequest(contact):
        """ add user as contact """

    def declineContactRequest(contact):
        """ decline request to add user as contact """

    def removeContact(contact):
        """ remove existing contact """

    def getPendingContacts():
        """ return a list of of all pending contacts """

    def getContactRequests():
        """ return a list of of all requests to be add as contact for a
            given user
        """

class IMessageBox(Interface):
    """ A container for messages """

    def addMessage(self, message):
        """ add a message """


class IMessage(Interface):
    """ A message in a message box """

    text = schema.Text(
        title=u"Message Body",
        required=True,)

    time = schema.Datetime(
        title=u"Timestamp for the message",
        required=True,)
