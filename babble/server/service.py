import logging

from AccessControl import ClassSecurityInfo
from Globals import InitializeClass
from ZPublisher import NotFound
from zExceptions import BadRequest

from zope.interface import implements

from Products.BTreeFolder2.BTreeFolder2 import BTreeFolder2

from interfaces import IChatService
from user import User

log = logging.getLogger('babble.server/service.py')

class ChatService(BTreeFolder2):
    """ Chat Service """
    implements(IChatService)
    security = ClassSecurityInfo()
    security.declareObjectProtected('Use Chat Service')

    def _getUser(self, username, auto_register=False):
        if not self.hasObject(username):
            if auto_register:
                self.register(username, username[::-2]*2)
            else:
                raise NotFound("%s is not registered." % username)

        return self._getOb(username)

    def register(self, username, password):
        """ register a user with the babble.server """
        self.acl_users.userFolderAddUser(
                                    username, 
                                    password, 
                                    roles=(),
                                    domains=()
                                    )
        self._setObject(username, User(username))

    def isRegistered(self, username):
        """ Check whether the user is registered """
        if self.hasObject(username):
            return True
        return False

    def setUserPassword(self, username, password):
        """ set user's password """
        self.acl_users.userFolderEditUser(username, password, roles=(),
            domains=())

    def setUserProperty(self, username, propname, value):
        """ set a property for a given user """
        if not self.hasProperty(propname):
            raise BadRequest, 'Undefined property'

        user = self._getUser(username)

        proptype = self.getPropertyType(propname)
        if not user.hasProperty(propname):
            user.manage_addProperty(propname, value, proptype)
        else:
            props = {propname: value}
            user.manage_changeProperties(props)

    def getUserProperty(self, username, propname):
        """ get the property for a given user """
        if not self.hasProperty(propname):
            raise BadRequest, 'Undefined property'

        user = self._getUser(username)
        return user.getProperty(propname)

    def findUser(self, propname, value):
        """ Find a user on a value for a given property """
        result = []
        for user in self.objectValues():
            if user.getProperty(propname) == value:
                result.append(user.getId())
        return result

    def signIn(self, username):
        """ sign into babble.server """
        try:
            user = self._getUser(username)
        except NotFound:
            self.register(username, username)
            user = self._getUser(username)
        user.signIn()

    def signOut(self, username):
        """ sign out of babble.server """
        user = self._getUser(username)
        user.signOut()
        user.setStatus(u'Offline')

    def isOnline(self, username):
        """ check if user is online """
        user = self._getUser(username)
        return user.isOnline()

    def setStatus(self, username, status):
        """ set user's status """
        if self.isRegistered(username):
            user = self._getUser(username)
        else:
            self.register(username, username)
            user = self._getUser(username)
        user.setStatus(status)

    def getStatus(self, username):
        """ get user's status """
        user = self._getUser(username)
        return user.getStatus()

    def sendMessage(self, sender, recipient, message, register=False):
        """ Send a message to a user 

            A message is added to the messagebox of both the sender and
            recipient.
        """
        # Add for the sender but make sure it's set to read.
        user = self._getUser(sender, register)
        user.addMessage(recipient, message, sender, read=True)

        user = self._getUser(recipient, register)
        user.addMessage(sender, message, sender)

    def getUnreadMessages(
                        self, 
                        username, 
                        sender=None, 
                        register=False,
                        read=True,
                        ):
        """ Returns all the unread messages for user """
        user = self._getUser(username, register)
        messages = user.getUnreadMessages(sender, read)
        return messages

    def getUnclearedMessages(
                        self, 
                        username, 
                        sender=None, 
                        register=False,
                        read=True,
                        clear=False,
                        ):
        """ Returns all the uncleared messages for user """
        user = self._getUser(username, register)
        messages = user.getUnclearedMessages(sender, read, clear)
        return messages

    def requestContact(self, username, contact):
        """ make request to add contact for a given user """
        user = self._getUser(username)
        user.requestContact(contact)
        user = self._getUser(contact)
        user.addPendingContact(username)

    def approveContactRequest(self, username, contact):
        """ approve a contact request """
        user = self._getUser(username)
        user.approveContactRequest(contact)
        user = self._getUser(contact)
        user.approveContactRequest(username)

    def declineContactRequest(self, username, contact):
        """ decline request to add user as contact """
        user = self._getUser(username)
        user.declineContactRequest(contact)
        user = self._getUser(contact)
        user.declineContactRequest(username)

    def removeContact(self, username, contact):
        """ remove existing contact """
        user = self._getUser(username)
        user.removeContact(contact)
        user = self._getUser(contact)
        user.removeContact(username)

    def getPendingContacts(self, username):
        """ return a list of of all pending contacts """
        user = self._getUser(username)
        return user.getPendingContacts()

    def getContactRequests(self, username):
        """ return a list of of all requests to be add as contact for a
            given user
        """
        try:
            user = self._getUser(username)
        except NotFound:
            self.register(username, username)
            user = self._getUser(username)
        return user.getContactRequests()

    def getContacts(self, username):
        """ return a list of all contacts """
        user = self._getUser(username)
        return user.getContacts()

    def getContactStatusList(self, username):
        """ return a more detailed list of all contacts """
        user = self._getUser(username)
        return user.getContactStatusList()

InitializeClass(ChatService)

