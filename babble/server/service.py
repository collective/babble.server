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
from chatroom import ChatRoom
from utils import hashed
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


    def _getChatRoomsFolder(self):
        """ The 'ChatRooms' folder is a BTreeFolder that contains IChatRoom objects.
        """
        if not self.hasObject('chatrooms'):
            log.warn("The chatservice's 'ChatRooms' folder did not exist, "
                    "and has been automatically recreated.")
            manage_addBTreeFolder(self, 'chatrooms', 'ChatRooms')

        return self._getOb('chatrooms')


    def _getConversationsFolder(self):
        """ The 'Conversations' folder is a BTreeFolder that contains
            IConversation objects.

            See babble.server.interfaces.py:IConversation
        """
        if not self.hasObject('conversations'):
            log.warn("The chatservice's 'Conversations' folder did not exist, "
                    "and has been automatically recreated.")
            manage_addBTreeFolder(self, 'conversations', 'Conversations')

        return self._getOb('conversations')


    def _getConversation(self, user1, user2):
        """ """
        folder = self._getConversationsFolder()
        id = '.'.join(sorted([hashed(user1), hashed(user2)]))
        if not folder.hasObject(id):
            folder._setObject(id, Conversation(id, user1, user2))
        return folder._getOb(id)


    def _getConversationsFor(self, username):
        """ """
        f = self._getConversationsFolder()
        username = hashed(username)
        return [f._getOb(i) for i in f.objectIds() if username in i.split('.')]


    def _getChatRooms(self, ids):
        folder = self._getChatRoomsFolder()
        if type(ids) == str:
            ids= [ids]
        crs = []
        for c in ids:
            crs.append(folder._getOb(hashed(c)))
        return crs


    def _getChatRoom(self, id):
        folder = self._getChatRoomsFolder()
        return folder._getOb(hashed(id))


    def _getChatRoomsFor(self, username):
        folder = self._getChatRoomsFolder()
        rooms = []
        for chatroom in folder.values():
            if username in chatroom.participants:
                rooms.append(chatroom)
        return rooms

    
    def addChatRoomParticipant(self, username, password, path, participant):
        """ """
        if self._authenticate(username, password) is None:
            log.error('addChatRoomParticipant: authentication failed')
            return json.dumps({'status': config.AUTH_FAIL})
        try:
            chatroom = self._getChatRoom(path)
        except KeyError:
            return json.dumps({
                    'status': config.NOT_FOUND, 
                    'errmsg': "Chatroom '%s' doesn't exist" % id, 
                    })
        if participant not in chatroom.participants:
            chatroom._addParticipant(participant)
        return json.dumps({'status': config.SUCCESS})


    def createChatRoom(self, username, password, path, participants):
        """ Chat rooms, unlike members, don't necessarily have unique IDs. They
            do however have unique paths. We hash the path to get a unique id.
        """
        if self._authenticate(username, password) is None:
            log.error('createChatRoom: authentication failed')
            return json.dumps({'status': config.AUTH_FAIL})

        folder = self._getChatRoomsFolder()
        id = hashed(path)
        folder._setObject(id, ChatRoom(id, path, participants))
        return json.dumps({'status': config.SUCCESS})


    def editChatRoom(self, username, password, id, participants):
        """ """
        if self._authenticate(username, password) is None:
            log.error('getMessages: authentication failed')
            return json.dumps({'status': config.AUTH_FAIL})
        try:
            chatroom = self._getChatRoom(id)
        except KeyError:
            return json.dumps({
                    'status': config.NOT_FOUND, 
                    'errmsg': "Chatroom '%s' doesn't exist" % id, 
                    })

        chatroom.participants = participants
        chatroom.partner = {}
        for p in participants:
            chatroom.partner[p] = chatroom.client_path
        return json.dumps({'status': config.SUCCESS})


    def removeChatRoom(self, username, password, id):
        """ """
        if self._authenticate(username, password) is None:
            log.error('getMessages: authentication failed')
            return json.dumps({'status': config.AUTH_FAIL})

        parent = self._getChatRoomsFolder()
        parent.manage_delObjects([hashed(id)])
        return json.dumps({'status': config.SUCCESS})


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
        user = self.acl_users.userFolderAddUser(
                                    username, 
                                    password, 
                                    roles=(), 
                                    domains=(), 
                                    last_msg_date=config.NULL_DATE )
        user.last_received_date = config.NULL_DATE
        user.last_cleared_date = config.NULL_DATE
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


    def sendMessage(self, username, password, fullname, recipient, message):
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
        last_msg_date = conversation.addMessage(message, username, fullname).time
        return json.dumps({
                'status': config.SUCCESS, 
                'last_msg_date': last_msg_date
                })


    def sendChatRoomMessage(self, username, password, fullname, room_name, message):
        """ Sends a message to a chatroom """
        if self._authenticate(username, password) is None:
            log.error('sendMessage: authentication failed')
            return json.dumps({
                    'status': config.AUTH_FAIL, 
                    'last_msg_date': config.NULL_DATE
                    })
        try:
            chatroom = self._getChatRoom(room_name)
        except KeyError:
            return json.dumps({
                    'status': config.ERROR, 
                    'errmsg': "Chatroom '%s' doesn't exist" % room_name, 
                    })

        last_msg_date = chatroom.addMessage(message, username, fullname).time
        return json.dumps({
                'status': config.SUCCESS, 
                'last_msg_date': last_msg_date
                })


    def _getMessagesFromContainers(self, containers, username, since, until):
        """ containers: A list of conversations, or a list of chatrooms
            since:  iso8601 date string
            until:  iso8601 date string
        """
        last_msg_date = config.NULL_DATE
        msgs_dict = {}
        for container in containers:
            msg_tuples = []
            mbox_messages = []
            for mbox in container.values():
                for i in mbox.objectIds():
                    i = float(i)
                    mdate = datetime.utcfromtimestamp(i).replace(tzinfo=utc).isoformat()
                    if mdate <= since or mdate > until:
                        continue

                    m = mbox._getOb('%f' % i)
                    msg_tuples.append((i, m))
            
            msg_tuples.sort()
            for i, m in msg_tuples:
                try:
                    mbox_messages.append((m.author, m.text, m.time, m.fullname))
                except AttributeError as e:
                    # BBB
                    if str(e) == 'fullname':
                        mbox_messages.append((m.author, m.text, m.time, m.author))
                    else:
                        raise AttributeError, e

                if m.time > last_msg_date:
                    last_msg_date = m.time 

            if mbox_messages:
                msgs_dict[container.partner[username]] = tuple(mbox_messages)

        return msgs_dict, last_msg_date


    def _getMessages(self, username, partner, chatrooms, since, until): 
        """ Returns messages within a certain date range

            This is an internal method that assumes authentication has 
            been done.

            partner == '*' means all partners
            chatrooms == '*' means all chatrooms
        """ 
        if since is None:
            since = config.NULL_DATE
        elif not config.VALID_DATE_REGEX.search(since):
            return {'status': config.ERROR, 
                    'errmsg': 'Invalid date format',}

        if until is None:
            until = datetime.now(utc).isoformat()
        elif not config.VALID_DATE_REGEX.search(until):
            return {'status': config.ERROR, 
                    'errmsg': 'Invalid date format',}

        if partner == '*':
            conversations = self._getConversationsFor(username)
        elif partner:
            conversations = [self._getConversation(username, partner)]
        else:
            conversations = []

        if chatrooms == '*':
            chatrooms = self._getChatRoomsFor(username)
        else:
            try:
                chatrooms = self._getChatRooms(chatrooms)
            except KeyError, e:
                return {'status': config.ERROR, 
                        'errmsg': "Chatroom %s doesn't exist" % e,}

        messages, last_msg_date = \
            self._getMessagesFromContainers(conversations, username, since, until)

        chatroom_msgs, last_chat_date = \
            self._getMessagesFromContainers(chatrooms, username, since, until)

        if last_chat_date > last_msg_date:
            last_msg_date = last_chat_date
                
        return {'status': config.SUCCESS, 
                'messages': messages,
                'chatroom_messages': chatroom_msgs,
                'last_msg_date':last_msg_date }


    def getMessages(self, username, password, partner, chatrooms, since, until):
        """ Returns messages within a certain date range

            Parameter values:
            -----------------
            partner: None or '*' or a username. 
                If None, don't return from any partners. 
                If *, return from all partners.
                Else, return only from the user with name given

            chatrooms: list of strings

            since: iso8601 date string or None
            until: iso8601 date string or None
        """
        if self._authenticate(username, password) is None:
            log.error('getMessages: authentication failed')
            return json.dumps({'status': config.AUTH_FAIL})

        return json.dumps(self._getMessages(
                                        username, 
                                        partner, 
                                        chatrooms, 
                                        since, until))


    def getNewMessages(self, username, password):
        """ Get all messages since the user's last fetch.

            partner: None or '*' or a username. 
                If None, don't return from any partners. 
                If *, return from all partners.
                Else, return only from the user with name given
        """
        if self._authenticate(username, password) is None:
            log.error('getNewMessages: authentication failed')
            return json.dumps({'status': config.AUTH_FAIL})

        user = self.acl_users.getUser(username)
        if not hasattr(user, 'last_received_date'):
            user.last_received_date = config.NULL_DATE
        since = user.last_received_date

        result = self._getMessages(username, '*', '*', since, None)

        # XXX: Test this!
        if result['status'] == config.SUCCESS and \
                (result['messages'] or result['chatroom_messages']):
            log.info('getNewMessages: %s' % user.last_received_date)
            user.last_received_date = result['last_msg_date']

        return json.dumps(result)


    def getUnclearedMessages(self, username, password, partner, chatrooms, clear):
        """ Get all messages since the last clearance date.

            partner: None or '*' or a username. 
                If None, don't return from any partners. 
                If *, return from all partners.
                Else, return only from the user with name given
        """
        if self._authenticate(username, password) is None:
            log.error('getUnclearedMessages: authentication failed')
            return json.dumps({'status': config.AUTH_FAIL})

        user = self.acl_users.getUser(username)
        if not hasattr(user, 'last_cleared_date'):
            user.last_cleared_date = config.NULL_DATE
        since = user.last_cleared_date

        result = self._getMessages(username, partner, chatrooms, since, None)
        if result['status'] == config.SUCCESS and \
                (result['messages'] or result['chatroom_messages']):

            # XXX: Test this!
            if result['last_msg_date'] > user.last_received_date:
                # The last_msg_date is not necessarily bigger, since
                # getUnclearedMessages only fetches for a specific partner
                # and/or chatrooms.
                user.last_received_date = result['last_msg_date']

            if clear:
                user.last_cleared_date = result['last_msg_date']
        return json.dumps(result)


InitializeClass(ChatService)

