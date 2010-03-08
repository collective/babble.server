import logging
import datetime

from zope.interface import implements

from AccessControl import ClassSecurityInfo
from Globals import InitializeClass
from OFS.Folder import Folder
from ZPublisher import NotFound
from persistent.dict import PersistentDict

from Products.BTreeFolder2.BTreeFolder2 import manage_addBTreeFolder

from interfaces import IChatService
from user import User

log = logging.getLogger('babble.server/service.py')

class ChatService(Folder):
    """ """
    implements(IChatService)
    security = ClassSecurityInfo()
    security.declareObjectProtected('Use Chat Service')

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
        if not hasattr(self, 'temp_folder'): # Acquisition
            log.warn("The chatservice 'Online Users' folder did not exist, "
                "and has been automatically recreated.")
            raise NotFound("/temp_folder does not exist.")

            
        temp_folder = self.temp_folder # Acquisition
        if not temp_folder.hasObject('user_access_dict'):
            log.info("The user_access_dict did not exist, "
                    "and has been automatically recreated.")
            temp_folder._setOb('user_access_dict', PersistentDict())

        return temp_folder._getOb('user_access_dict')


    def _getUsersFolder(self):
        """ The 'Users' folder is a BTreeFolder that contains IUser objects.
            See babble.server.interfaces.py:IUser
        """
        if not self.hasObject('users'):
            log.warn("The chatservice 'Users' folder did not exist, "
                    "and has been automatically recreated.")
            manage_addBTreeFolder(self, 'users', 'Users')

        return self._getOb('users')


    def _getUser(self, username):
        """ Retrieve the IUser obj from the 'Users' folder.
        """
        users = self._getUsersFolder()
        if not users.hasObject(username):
            raise NotFound("%s is not registered." % username)
        return users._getOb(username)


    def _confirmAsOnline(self, username):
        """ Confirm that the user is currently online by updating the 'user
            access dict'
        """
        uad = self._getUserAccessDict()
        uad[username] = datetime.datetime.now()


    def register(self, username, password):
        """ Register a user with the babble.server's acl_users and create a
            'User' object in the 'Users' folder
        """
        self.acl_users.userFolderAddUser(
                        username, password, roles=(), domains=())

        users = self._getUsersFolder()
        users._setObject(username, User(username))


    def isRegistered(self, username):
        """ Check whether the user is registered via acl_users """
        return self.acl_users.getUser(username) and True or False


    def setUserPassword(self, username, password):
        """ Set the user's password """
        self.acl_users.userFolderEditUser(
                    username, password, roles=(), domains=())


    def authenticate(self, username, password):
        """ Authenticate the user with username and password """
        return self.acl_users.authenticate(username, password, self.REQUEST)
        

    def isOnline(self, username):
        """ Determine whether the user is (probably) currently online

            Get the last time that the user updated the 'user access dict' and
            see whether this time is less than 1 minute in the past.

            If yes, then we assume the user is online, otherwise not.
        """
        uad = self._getUserAccessDict()
        last_confirmed_date = uad.get(username, datetime.datetime.min)
        delta = datetime.timedelta(minutes=1)
        cutoff_date = datetime.datetime.now() - delta
        return last_confirmed_date > cutoff_date


    def getOnlineUsers(self):
        """ Determine the (probable) online users from the 'user access dict' 
            and return them as a list
        """
        uad = self._getUserAccessDict()
        return [user for user in uad.keys() if self.isOnline(user)]


    def setStatus(self, username, status):
        """ Set the user's status.

            The user might have a status such as 'available', 'chatty', 
            'busy' etc. but this only applies if the user is actually 
            online, as determined from the 'user access dictionary'.

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
            online, as determined from the 'user access dictionary'.

            The 'status' attribute is optional, it depends on the chat client 
            whether the user's 'status' property is at all relevant 
            and being used.
        """
        if not self.isOnline(username):
            return 'offline'
            
        user = self._getUser(username)
        return user.getStatus()


    def sendMessage(self, sender, recipient, message, register=False):
        """ Sends a message to recipient

            A message is added to the messagebox of both the sender and
            recipient.
        """
        # Add for the sender, but make sure it's set to read.
        user = self._getUser(sender)
        user.addMessage(recipient, message, sender, read=True)

        user = self._getUser(recipient)
        user.addMessage(sender, message, sender)


    def getUnreadMessages(
                        self, 
                        username, 
                        sender=None, 
                        read=True,
                        confirm_online=True,
                        ):
        """ Returns the unread messages for a user. 
            
            If sender is none, return all unread messages, otherwise return
            only the unread messages sent by that specific sender.
        """
        if confirm_online:
            self._confirmAsOnline(username)

        user = self._getUser(username)
        messages = user.getUnreadMessages(sender, read)
        return messages


    def getUnclearedMessages(
                        self, 
                        username, 
                        sender=None, 
                        read=True,
                        clear=False,
                        confirm_online=True,
                        ):
        """ Returns the uncleared messages for user. 
            
            If sender is none, return all uncleared messages, otherwise return
            only the uncleared messages sent by that specific sender.
        """
        if confirm_online:
            self._confirmAsOnline(username)

        user = self._getUser(username)
        messages = user.getUnclearedMessages(sender, read, clear)
        return messages


InitializeClass(ChatService)

