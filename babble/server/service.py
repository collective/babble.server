import logging
import simplejson as json
from datetime import datetime
from datetime import timedelta
from pytz import utc

from zope.interface import implements

from AccessControl import ClassSecurityInfo
from Globals import InitializeClass
from OFS.Folder import Folder
from ZPublisher import NotFound
from persistent.dict import PersistentDict

from Products.BTreeFolder2.BTreeFolder2 import manage_addBTreeFolder

from interfaces import IChatService
from conversation import Conversation
from utils import hash_encode
import config

log = logging.getLogger('babble.server/service.py')

class ChatService(Folder):
    """ """
    implements(IChatService)
    security = ClassSecurityInfo()
    security.declareObjectProtected('Use Chat Service')

    def _getUserAccessDict(self):
        """ The 'user access dictionary' is stored inside a Temporary Folder.
            A Temporary Folder is kept in RAM and it loses all its contents 
            whenever the Zope server is restarted.

            The 'user access dictionary' contains usernames as keys and the
            last date and time that these users have been confirmed to be 
            online as the values.

            These date values can be used to determine (guess) whether the 
            user is still currently online.
        """
        if not hasattr(self, 'temp_folder'): # Acquisition
            log.error("The chatservice 'Online Users' folder does not exist!")
            raise NotFound("/temp_folder does not exist.")

        if not self.temp_folder.hasObject('user_access_dict'):
            log.debug("The user_access_dict did not exist, "
                    "and has been automatically recreated.")
            self.temp_folder._setOb('user_access_dict', PersistentDict())

        return self.temp_folder._getOb('user_access_dict')


    def _getCachedUserAccessDict(self):
        """ Implement simple caching to minimise writes
        """
        now = datetime.now()
        if hasattr(self, '_v_user_access_dict') \
                and getattr(self, '_v_cache_timeout', now) > now:
            return getattr(self, '_v_user_access_dict')

        # The cache has expired.
        # Update the cache with the new user_access_dict if it is different
        uad = self._getUserAccessDict()
        if getattr(self, '_v_user_access_dict', None) != uad:
            setattr(self, '_v_user_access_dict', uad.copy())

        # Set a new cache timeout, 30 secs in the future
        delta = timedelta(seconds=30)
        cache_timeout = now + delta
        setattr(self, '_v_cache_timeout', cache_timeout)
        return uad


    def _setUserAccessDict(self, **kw):
        """ Make sure that the temp_folder which stores the dict of online
            users is updated. 
            Also make sure that the cache is up to date with new values.
        """
        # Get the user_access_dict directly (bypassing cache) and update it.
        uad = self._getUserAccessDict()
        uad.update(kw)
        self.temp_folder._setOb('user_access_dict', uad.copy())

        # Set the cache
        now = datetime.now()
        delta = timedelta(seconds=30)
        cache_timeout = now + delta
        setattr(self, '_v_cache_timeout', cache_timeout)
        setattr(self, '_v_user_access_dict', uad.copy())


    def _getUsersFolder(self):
        """ The 'Users' folder is a BTreeFolder that contains IUser objects.
            See babble.server.interfaces.py:IUser
        """
        if not self.hasObject('users'):
            log.warn("The chatservice 'Users' folder did not exist, "
                    "and has been automatically recreated.")
            manage_addBTreeFolder(self, 'users', 'Users')

        return self._getOb('users')


    def _getConversationsFolder(self):
        """ The 'Conversations' folder is a BTreeFolder that contains
            IConversation objects.

            See babble.server.interfaces.py:IConversation
        """
        if not self.hasObject('conversations'):
            log.warn("The chatservice 'Conversations' folder did not exist, "
                    "and has been automatically recreated.")
            manage_addBTreeFolder(self, 'conversations', 'Conversations')

        return self._getOb('conversations')


    def _getConversation(self, user1, user2):
        """ """
        folder = self._getConversationsFolder()
        id = '.'.join(sorted([hash_encode(user1), hash_encode(user2)]))
        if not folder.hasObject(id):
            folder._setObject(id, Conversation(id, user1, user2))
        return folder._getOb(id)


    def _getConversationsFor(self, username):
        """ """
        f = self._getConversationsFolder()
        username = hash_encode(username)
        return [f._getOb(i) for i in f.objectIds() if username in i.split('.')]


    def _authenticate(self, username, password):
        """ Authenticate the user with username and password """
        return self.acl_users.authenticate(username, password, self.REQUEST)


    def _isOnline(self, username):
        """ Determine whether the user is (probably) currently online

            Get the last time that the user updated the 'user access dict' and
            see whether this time is less than 1 minute in the past.

            If yes, then we assume the user is online, otherwise not.
        """
        uad = self._getUserAccessDict()
        last_confirmed_date = uad.get(username, datetime.min)
        delta = timedelta(minutes=1)
        cutoff_date = datetime.now() - delta
        return last_confirmed_date > cutoff_date


    def confirmAsOnline(self, username):
        """ Confirm that the user is currently online by updating the 'user
            access dict'
        """
        if username is None:
            return json.dumps({
                            'status': config.ERROR,
                            'errmsg': 'Username may not be None',
                            })

        self._setUserAccessDict(**{username:datetime.now()})
        return json.dumps({'status': config.SUCCESS})


    def register(self, username, password):
        """ Register a user with the babble.server's acl_users
        """
        if ' ' in username:
            return json.dumps({
                            'status': config.ERROR,
                            'errmsg': 'Spaces not allowed in usernames',
                            })
            
        self.acl_users.userFolderAddUser(
                        username, password, roles=(), domains=())

        return json.dumps({'status': config.SUCCESS})


    def isRegistered(self, username):
        """ Check whether the user is registered via acl_users """
        is_registered = self.acl_users.getUser(username) and True or False
        return json.dumps({'status': config.SUCCESS, 'is_registered': is_registered})


    def setUserPassword(self, username, password):
        """ Set the user's password """
        self.acl_users.userFolderEditUser(
                username, password, roles=(), domains=())
        return json.dumps({'status': config.SUCCESS})


    def getOnlineUsers(self):
        """ Determine the (probable) online users from the 'user access dict' 
            and return them as a list
        """
        uad = self._getCachedUserAccessDict()
        ou = [user for user in uad.keys() if self._isOnline(user)]
        return json.dumps({'status': config.SUCCESS, 'online_users': ou})


    def sendMessage(self, username, password, recipient, message):
        """ Sends a message to recipient

            A message is added to the messagebox of both the sender and
            recipient.
        """
        if self._authenticate(username, password) is None:
            log.error('sendMessage: authentication failed')
            return json.dumps({
                    'status': config.AUTH_FAIL, 
                    'last_msg_date': config.NULL_DATE
                    })

        conversation = self._getConversation(username, recipient)
        last_msg_date = conversation.addMessage(message, username).time
        return json.dumps({
                'status': config.SUCCESS, 
                'last_msg_date': last_msg_date
                })


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

        if mark_cleared not in [None, True, False] or \
                    cleared not in [None, True, False]:
            return json.dumps({
                        'status': config.ERROR, 
                        'errmsg': 'Invalid parameter value', })

        if since is None:
            since = config.NULL_DATE 
        elif not config.VALID_DATE_REGEX.search(since):
            return json.dumps({
                        'status': config.ERROR, 
                        'errmsg': 'Invalid date format', })

        if until is None:
            until = datetime.now(utc).isoformat()
        elif not config.VALID_DATE_REGEX.search(until):
            return json.dumps({
                        'status': config.ERROR, 
                        'errmsg': 'Invalid date format', })

        if self._authenticate(username, password) is None:
            log.error('getMessages: authentication failed')
            return json.dumps({'status': config.AUTH_FAIL})

        if sender:
            cs = [self._getConversation(username, sender)]
        else:
            cs = self._getConversationsFor(username)

        last_msg_date = config.NULL_DATE
        messages = {}
        for conversation in cs:
            msg_tuples = []
            conv_messages = []
            for mbox in conversation.values():
                for i in mbox.objectIds():
                    i = float(i)
                    mdate = datetime.utcfromtimestamp(i).replace(tzinfo=utc).isoformat()
                    if mdate <= since or mdate > until:
                        continue

                    m = mbox._getOb('%f' % i)
                    msg_tuples.append((i, m))

            msg_tuples.sort()
            for i, m in msg_tuples:
                if cleared is not None and m._cleared != cleared:
                    continue

                conv_messages.append((m.author, m.text, m.time))

                if m.time > last_msg_date:
                    last_msg_date = m.time 

                if mark_cleared: m._cleared = True

            if conv_messages:
                messages[conversation.partner[username]] = tuple(conv_messages)

        return json.dumps({
                    'status': config.SUCCESS, 
                    'messages': messages,
                    'last_msg_date':last_msg_date
                    })

InitializeClass(ChatService)

