import logging
from datetime import datetime

from zope.interface import implements

from AccessControl import ClassSecurityInfo
from Globals import InitializeClass
from OFS.Folder import Folder
from ZPublisher import NotFound
from zExceptions import BadRequest
from persistent.dict import PersistentDict

from Products.BTreeFolder2.BTreeFolder2 import manage_addBTreeFolder
from Products.TemporaryFolder.TemporaryFolder import constructTemporaryFolder 

from interfaces import IChatService
from user import User

log = logging.getLogger('babble.server/service.py')

class ChatService(Folder):
    """ Chat Service """
    implements(IChatService)
    security = ClassSecurityInfo()
    security.declareObjectProtected('Use Chat Service')

    def _getUserAccessDict(self):
        """ The user access dictionary is stored inside a Temporary Folder.
            The contents of a Temporary Folder is kept in RAM and loses all
            it's contents whenever Zope is restarted.

            The user access dictionary contains usernames as keys and the
            last date and time that these users have been confirmed to be 
            online as the values.

            These date values can be used to determine (guess) whether the 
            user is still currently online.
        """
        if not self.hasObject('temp_folder'):
            log.warn("The chatservice 'Online Users' folder did not exist, "
                "and has been automatically recreated.")

            constructTemporaryFolder(self, 'temp_folder')
            
        temp_folder = self._getOb('temp_folder')
        if not temp_folder.hasObject('user_access_dict'):
            log.info("The user_access_dict did not exist, "
                "and has been automatically recreated.")

            temp_folder._setOb('user_access_dict', PersistentDict())

        return temp_folder._getOb('user_access_dict')

    def _getUsersFolder(self):
        if not self.hasObject('users'):
            log.warn("The chatservice 'Users' folder did not exist, "
                "and has been automatically recreated.")

            manage_addBTreeFolder(self, 'users', 'Users')
            
        return self._getOb('users')

    def _getUser(self, username, auto_register=True):
        users = self._getUsersFolder()
        if not users.hasObject(username):
            if auto_register:
                self.register(username, username[::-2]*2)
            else:
                raise NotFound("%s is not registered." % username)

        return users._getOb(username)

    def register(self, username, password):
        """ register a user with the babble.server """
        self.acl_users.userFolderAddUser(
                        username, password, roles=(), domains=())

        users = self._getUsersFolder()
        users._setObject(username, User(username))

    def isRegistered(self, username):
        """ Check whether the user is registered """
        if self.users.hasObject(username):
            return True
        return False

    def setUserPassword(self, username, password):
        """ set user's password """
        self.acl_users.userFolderEditUser(
                    username, password, roles=(), domains=())

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

    def confirmAsOnline(self, username):
        """ Confirm that the user is currently online by updating the 'user
            access dict'
        """
        uad = self._getUserAccessDict()
        uad[username] = datetime.now()

    def isOnline(self, username):
        """ Determine whether the user is (probably) currently online

            Get the last time that the user updated the 'user access dict' and
            see whether this time is less than 1 minute in the past.

            If yes, then we assume the user is online, otherwise not.
        """
        uad = self._getUserAccessDict()
        last_confirmed_date = uad.get(username, datetime.min)
        now = datetime.now()
        minute = now.minute  or 1
        cutoff_date = now.replace(minute=minute-1)
        return last_confirmed_date > cutoff_date

    def getOnlineUsers(self):
        """ Determine the (probable) online users from the 'user access dict' 
            and return them as a list
        """
        online_users = []
        uad = self._getUserAccessDict()
        for username in uad.keys():
            last_confirmed_date = uad.get(username, datetime.min)
            now = datetime.now()
            minute = now.minute  or 1
            cutoff_date = now.replace(minute=minute-1)
            if last_confirmed_date > cutoff_date:
                online_users.append(username)

        return online_users

    def setStatus(self, username, status):
        """ Set the user's status.

            The user might have a status such as 'available', 'chatty', 
            'busy' etc. but this only applies if the user is actually 
            online.

            The 'status' attribute is optional, it depends on the chat client 
            whether the user's 'status' property is at all relevant 
            and being used.
        """
        user = self._getUser(username)
        user.setStatus(status)

    def getStatus(self, username):
        """ Get the user's status.

            The user might have a status such as 'available', 'chatty', 
            'busy' etc. but this only applies if the user is actually 
            online.

            The 'status' attribute is optional, it depends on the chat client 
            whether the user's 'status' property is at all relevant 
            and being used.
        """
        if not self.isOnline(username):
            return 'offline'
            
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
                        register=True,
                        read=True,
                        confirm_online=True,
                        ):
        """ Returns the unread messages for user. 
            
            If sender is none, return all unread messages, otherwise return
            only the unread messages for that specific sender.
        """
        if confirm_online:
            self.confirmAsOnline(username)

        user = self._getUser(username, register)
        messages = user.getUnreadMessages(sender, read)
        return messages

    def getUnclearedMessages(
                        self, 
                        username, 
                        sender=None, 
                        register=True,
                        read=True,
                        clear=False,
                        confirm_online=True,
                        ):
        """ Returns the uncleared messages for user. 
            
            If sender is none, return all uncleared messages, otherwise return
            only the uncleared messages for that specific sender.
        """
        if confirm_online:
            self.confirmAsOnline(username)

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

