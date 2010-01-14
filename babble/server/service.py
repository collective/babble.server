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

    def register(self, username, password):
        """ register a user with the babble.server """
        self.acl_users.userFolderAddUser(
                                    username, 
                                    password, 
                                    roles=(),
                                    domains=())
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

    def sendMessage(self, username, recipient, message, register=False):
        """ send a message to a user """
        user = self._getUser(recipient, register)
        user.addMessage(username, message)

    def getAllMessages(self, user, register=False):
        """ Returns all the messages for user"""
        user = self._getUser(user, register)
        messages = user.getAllMessages()
        return messages

    def getMessagesForUser(self, username, sender, read=True):
        """ get all the messages for a user from a given sender"""
        user = self._getUser(username)
        messages = user.getMessagesFromSender(sender, read)
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

    def _getUser(self, username, register=False):
        if not self.hasObject(username):
            if register:
                self.register(username, username[::-2]*2)
            else:
                raise NotFound("%s is not registered." % username)

        return self._getOb(username)

InitializeClass(ChatService)

