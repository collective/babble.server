import datetime
import simplejson as json
from pytz import utc

from Testing import ZopeTestCase as ztc
from zExceptions import Unauthorized

from zope.interface.verify import verifyObject

from Products.Five import zcml
import Products.Five
ztc.installProduct('Five')
zcml.load_config('configure.zcml', package=Products.Five)

import babble.server
ztc.installProduct('babble.server')
zcml.load_config('configure.zcml', package=babble.server)

from babble.server import config
from babble.server import interfaces
from babble.server.conversation import Conversation
from babble.server.chatroom import ChatRoom

# Regex to test for ISO8601, i.e: '2011-09-30T15:49:35.417693+00:00'
# RE = re.compile(r'^\d{4}-\d{2}-\d{2}[ T]\d{2}:\d{2}:\d{2}\.\d{6}[+-]\d{2}:\d{2}$')

class TestChatService(ztc.ZopeTestCase):

    def _create_chatservice(self):
        """ Adds a babble.server to the default fixture """
        if getattr(self.app, 'chat_service', None):
            self.app.manage_delObjects(['chat_service'])
        view = self.app.unrestrictedTraverse('+/addChatService.html')
        self.assertEqual(type(view()), unicode) # Render the add form
        view(add_input_name='chat_service', title='Chat Service', submit_add=1)
        return self.app.chat_service


    def test_interfaces(self):
        service = self._create_chatservice() 
        self.assertTrue(verifyObject(interfaces.IChatService, service))

        chatrooms = service._getOb('chatrooms')
        chatrooms._setObject('chatroom', ChatRoom('chatroom', 'chatroom', []))
        chatroom = chatrooms._getOb('chatroom')
        self.assertTrue(verifyObject(interfaces.IChatRoom, chatroom))

        conversations = service._getOb('conversations')
        conversations._setObject('conv', Conversation('conv', 'user1', 'user2'))
        conversation = conversations._getOb('conv')
        self.assertTrue(verifyObject(interfaces.IConversation, conversation))


    def test_register(self):
        """ Test the 'register' methods
        """
        s = self._create_chatservice() 
        status = s.register('username', 'password')
        status = json.loads(status)
        self.assertEquals(status['status'], config.SUCCESS)


    def test_user_access_dict(self):
        """ Test the '_getUserAccessDict' method
        """ 
        s = self._create_chatservice() 
        uad = s._getUserAccessDict()

        # The cache should be set and it's expiry date must be in the future
        self.assertEqual(getattr(s, '_v_user_access_dict'), {})

        now = datetime.datetime.now()

        # Put a user into the UAD
        s._setUserAccessDict('max_musterman')

        # Test that he is there
        uad = s._getUserAccessDict()
        self.assertEqual(uad.keys(), ['max_musterman'])

        # Test that he is also in the cache (first make sure that the cache
        # timeout is in the future)
        delta = datetime.timedelta(seconds=30)
        cache_timeout = now + delta
        setattr(s, '_v_cache_timeout', cache_timeout)

        # Wipe the UAD
        s._v_user_access_dict = {}

        # Put a user into the UAD
        s._setUserAccessDict('maxine_musterman')

        # Test that he is there and in the cache...
        uad = s._getUserAccessDict()
        self.assertEqual(uad.keys(), ['maxine_musterman'])

        now = datetime.datetime.now()
        assert(getattr(s, '_v_cache_timeout') > now)


    def test_registration(self):
        """ Test the 'register', 'isRegistered', 'authenticate' and
            'setUserPassword'  methods.
        """
        s = self._create_chatservice() 
        s.register('username', 'password')

        r = s.isRegistered('username')
        r = json.loads(r)
        self.assertEquals(r['status'], config.SUCCESS)
        self.assertEquals(r['is_registered'], True)

        auth = s._authenticate('username', 'password')
        self.assertEqual(auth != None, True)
        self.assertEqual(auth.name, 'username')

        r = s.isRegistered('nobody')
        r = json.loads(r)
        self.assertEquals(r['status'], config.SUCCESS)
        self.assertEquals(r['is_registered'], False)

        auth = s._authenticate('nobody', 'password')
        self.assertEqual(auth, None)

        s.setUserPassword('username', 'new_password')
        auth = s._authenticate('username', 'password')
        self.assertEqual(auth, None)

        auth = s._authenticate('username', 'new_password')
        self.assertEqual(auth != None, True)
        self.assertEqual(auth.name, 'username')


    def test_online(self):
        """ Test the 'confirmAsOnline', '_isOnline' and 'getOnlineUsers' methods """
        s = self._create_chatservice() 
        u = 'username'
        s.register(u, u)
        uad = s._getUserAccessDict()
        self.assertEqual(s._isOnline(u, uad), False)

        r = s.confirmAsOnline(None)
        r = json.loads(r)
        self.assertEquals(r['status'], config.ERROR)

        # Test that a user entry was made into the 'user access dict'
        s.confirmAsOnline(u)
        self.assertEqual(uad.get(u, None) != None, True)

        self.assertEqual(s._isOnline(u, uad), True)

        now = datetime.datetime.now()
        
        # Test that a user that was confirmed as online 59 seconds ago (i.e
        # less than a minute) is still considered as online.
        delta = datetime.timedelta(seconds=59)
        uad[u] = datetime.datetime.now() - delta
        self.assertEqual(s._isOnline(u, uad), True)

        ou = s.getOnlineUsers()
        ou = json.loads(ou)
        self.assertEquals(ou['status'], config.SUCCESS)
        self.assertEquals(ou['online_users'], [u])

        # Test that a user that was confirmed as online one minute ago (i.e
        # at least a minute) is now considered as offline.
        delta = datetime.timedelta(minutes=1)
        uad[u] = datetime.datetime.now() - delta
        self.assertEqual(s._isOnline(u, uad), False)

        ou = s.getOnlineUsers()
        ou = json.loads(ou)
        self.assertEquals(ou['status'], config.SUCCESS)
        self.assertEquals(ou['online_users'], [])

        # Test 'getOnlineUsers' with multiple online users.
        s.confirmAsOnline(u)

        u = 'another'
        s.register(u, u)
        s.confirmAsOnline(u)

        ou = s.getOnlineUsers()
        ou = json.loads(ou)
        self.assertEquals(ou['status'], config.SUCCESS)
        self.assertEquals(ou['online_users'], ['username', 'another'])


    def test_chatroom(self):
        s = self._create_chatservice()
        s.register('user1', 'secret')
        s.register('user2', 'secret')

        chatroom1_path = '/Plone/chatrooms/chatroom1'
        resp = json.loads(s.createChatRoom('user1', 'secret', chatroom1_path, ['user1']))
        self.assertEqual(resp['status'], config.SUCCESS)

        # test sanity check in _getMessageBox when checking for a messagebox of
        # a user that is not a participant.
        chatroom = s._getChatRoom(chatroom1_path)
        self.assertRaises(Unauthorized, chatroom._getMessageBox, 'user2')


    def test_messaging(self):
        """ Test sendMessage, getMessages, getNewMessages and related methods """
        s = self._create_chatservice()
        s.register('sender', 'secret')
        s.register('recipient', 'secret')

        # Delete the Conversations folder to check that it gets recreated.
        s.manage_delObjects(['conversations'])
        um = json.loads(s.getMessages('recipient', 'secret', '*', [], config.NULL_DATE, None,))
        self.assertEqual(um['status'], config.SUCCESS)
        self.assertTrue(hasattr(s, 'conversations'))

        um = s.getMessages('recipient', 'secret', '*', [], config.NULL_DATE, None)
        um = json.loads(um)
        self.assertEqual(um['status'], config.SUCCESS)
        self.assertEqual(um['messages'], {})

        # test authentication
        response = json.loads(s.sendMessage('sender', 'wrongpass', 'Sender McSend', 'recipient', 'This is the message'))
        self.assertEqual(response['status'], config.AUTH_FAIL)

        response = json.loads(s.getMessages('sender', 'wrongpass', '*', [], None, None))
        self.assertEqual(response['status'], config.AUTH_FAIL)

        um = json.loads(s.getNewMessages('recipient', 'wrongpass', config.NULL_DATE))
        self.assertEqual(um['status'], config.AUTH_FAIL)

        um = json.loads(s.getUnclearedMessages('recipient', 'wrongpass', 'sender', [], config.NULL_DATE, False))
        self.assertEqual(um['status'], config.AUTH_FAIL)

        # Test invalid date.
        um = json.loads(s.getMessages('recipient', 'secret', 'sender', [], '123512512351235', None))
        self.assertEqual(um['status'], config.ERROR)
        self.assertEqual(um['errmsg'], 'Invalid date format')

        um = json.loads(s.getMessages('recipient', 'secret', 'sender', [], None, '123512512351235'))
        self.assertEqual(um['status'], config.ERROR)
        self.assertEqual(um['errmsg'], 'Invalid date format')
        
        # test valid message sending
        response = s.sendMessage('sender', 'secret', 'Sender McSend', 'recipient', 'This is the message')
        response = json.loads(response)
        self.assertEqual(response['status'], config.SUCCESS)
        self.assertTrue(bool(config.VALID_DATE_REGEX.search(response['last_msg_date'])))
        message_timestamp = response['last_msg_date']

        um = json.loads(s.getNewMessages( 'recipient', 'secret', config.NULL_DATE))
        self.assertEqual(um['status'], config.SUCCESS)
        # The returned datastructure looks as follows:
        #
        # {
        #     'status': 0
        #     'last_msg_date': '2011-10-19T10:08:02.164873+00:00',
        #     'chatroom_messages': {},
        #     'messages': {
        #             'sender': [ ['sender', 'This is the message', '2011-10-19T10:08:02.164873+00:00'] ]
        #             },
        # }
        self.assertEqual(um.keys(), ['status', 'messages', 'last_msg_date', 'chatroom_messages'])
        self.assertEqual(um['last_msg_date'], message_timestamp)

        msgdict = um['messages'] 
        # Test that messages from only one user was returned
        self.assertEqual(msgdict.keys(), ['sender'])
        # Test that only one message was received from this user
        self.assertEqual(len(msgdict['sender']), 1)
        # Test that the message tuple has 3 elements
        self.assertEqual(len(msgdict['sender'][0]), 4)
        self.assertEqual(msgdict['sender'][0][0], 'sender')
        self.assertEqual(msgdict['sender'][0][1], 'This is the message')
        self.assertEqual(msgdict['sender'][0][2], message_timestamp)
        self.assertTrue(bool(config.VALID_DATE_REGEX.search(msgdict['sender'][0][2])))

        # Test that we get the same results again.
        db = json.loads(s.getMessages( 'recipient', 'secret', '*', [], None, None, ))
        self.assertEqual(db, um)

        # Test exact 'since' dates. 
        db = json.loads(s.getMessages( 'recipient', 'secret', '*', [], um['last_msg_date'], None, ))
        self.assertEqual(db['messages'], {})

        # Test exact 'until' date. This must return the message
        db = json.loads(s.getMessages( 'recipient', 'secret', '*', [], None, um['last_msg_date'], ))
        self.assertEqual(db, um)

        # Test that the sender also gets the same results
        db = json.loads(s.getMessages( 'sender', 'secret', '*', [], None, um['last_msg_date'], ))
        self.assertEqual(db.keys(), ['status', 'messages', 'last_msg_date', 'chatroom_messages'])
        self.assertEqual(db['last_msg_date'], message_timestamp)

        msgdict = db['messages'] 
        # Test that messages from only one user was returned
        self.assertEqual(msgdict.keys(), ['recipient'])
        # Test that only one message was received from this user
        self.assertEqual(len(msgdict['recipient']), 1)
        # Test that the message tuple has 3 elements
        self.assertEqual(len(msgdict['recipient'][0]), 4)
        self.assertTrue(bool(config.VALID_DATE_REGEX.search(msgdict['recipient'][0][2])))
        self.assertEqual(msgdict['recipient'][0][2], message_timestamp)
        self.assertEqual(msgdict['recipient'][0][0], 'sender')
        self.assertEqual(msgdict['recipient'][0][1], 'This is the message')

        # Test getMessages with multiple senders. 
        s.register('sender2', 'secret')
        before_first_msg_from_sender2 = datetime.datetime.now(utc).isoformat()
        response = s.sendMessage('sender2', 'secret', 'Sender2 McSend', 'recipient', 'Message from sender2')
        response = json.loads(response)
        self.assertEqual(response['status'], config.SUCCESS)
        self.assertEqual(bool(config.VALID_DATE_REGEX.search(response['last_msg_date'])), True)
        message2_timestamp = response['last_msg_date']

        um = json.loads(s.getMessages('recipient', 'secret', '*', [], config.NULL_DATE, None))
        # {
        #     'chatroom_messages': {},
        #     'last_msg_date': '2011-10-19T12:17:13.898764+00:00',
        #     'messages': {
        #                 'sender':  [['sender', 'This is the message', '2011-10-19T12:17:13.897684+00:00']],
        #                 'sender2': [['sender2', 'Message from sender2', '2011-10-19T12:17:13.898764+00:00']]
        #                 }, 
        #     'status': 0
        # }
        self.assertEqual(um['status'], config.SUCCESS)
        self.assertEqual(um['last_msg_date'], message2_timestamp)
        msgdict = um['messages'] 
        # Test that messages from two users were returned
        self.assertEqual(len(msgdict.keys()), 2)
        # Test that only one message was received from each
        self.assertEqual(len(msgdict.values()[0]), 1)
        self.assertEqual(len(msgdict.values()[1]), 1)

        # Test the messages' last_msg_dates
        self.assertTrue(bool(config.VALID_DATE_REGEX.search(msgdict['sender'][0][2])))
        self.assertEqual(msgdict['sender'][0][2], message_timestamp)
        self.assertEqual(msgdict['sender2'][0][2], message2_timestamp)

        # Test the properties of the message sent by senders
        self.assertEqual(len(msgdict['sender'][0]), 4)
        self.assertEqual(len(msgdict['sender2'][0]), 4)

        self.assertEqual(msgdict['sender2'][0][0], 'sender2')
        self.assertEqual(msgdict['sender2'][0][1], 'Message from sender2')

        recipient_messages = um
        # Now test that the sender also will get the message he sent...
        sender2_messages = json.loads(s.getMessages('sender2', 'secret', 'recipient', [], config.NULL_DATE, None,))
        self.assertEqual(sender2_messages.keys(), recipient_messages.keys())
        self.assertEqual(sender2_messages['status'], recipient_messages['status'])
        self.assertEqual(sender2_messages['last_msg_date'], recipient_messages['last_msg_date'])
        self.assertEqual(sender2_messages['messages']['recipient'], recipient_messages['messages']['sender2'])

        # Test for messages sent after message_timestamp. This should not return messages.
        um = json.loads(s.getMessages('recipient', 'secret', '*', [], recipient_messages['last_msg_date'], None))
        self.assertEqual(um['status'], config.SUCCESS)
        self.assertEqual(um['messages'], {})
        self.assertEqual(um['last_msg_date'], message2_timestamp)

        # Test with finer date ranges via 'since' and 'until'
        before_msg = datetime.datetime.now(utc).isoformat()

        response = s.sendMessage('sender', 'secret', 'Sender McSend', 'recipient', "sender's message between times")
        response = json.loads(response)
        self.assertEqual(response['status'], config.SUCCESS)

        after_msg = datetime.datetime.now(utc).isoformat()

        um = json.loads(s.getMessages('recipient', 'secret', '*', [], config.NULL_DATE, None))
        msgs = um['messages'] 
        self.assertEqual(um['status'], config.SUCCESS)
        self.assertEqual(len(um['messages']['sender']), 2)
        self.assertEqual(len(um['messages']['sender2']), 1)

        recipient_messages1 = s.getMessages('recipient', 'secret', '*', [], before_msg, after_msg)
        um = json.loads(recipient_messages1)
        self.assertEqual(um['status'], config.SUCCESS)
        self.assertEqual(len(um['messages']['sender']), 1)
        self.assertEqual(um['messages']['sender'][0][1], "sender's message between times")

        sender_messages = json.loads(s.getMessages('sender', 'secret', '*', [], before_msg, after_msg))
        self.assertEqual(sender_messages['status'], config.SUCCESS)
        self.assertEqual(len(sender_messages['messages']['recipient']), 1)
        self.assertEqual(sender_messages['messages']['recipient'][0][1], "sender's message between times")

        # Test getMessages between times and with multiple senders. 
        before_sender2_msg = datetime.datetime.now(utc).isoformat()
        response = s.sendMessage('sender2', 'secret',  'Sender2 McSend', 'recipient', "sender2's message between times")
        response = json.loads(response)
        self.assertEqual(response['status'], config.SUCCESS)
        after_sender2_msg = datetime.datetime.now(utc).isoformat()

        recipient_messages2 = s.getMessages('recipient', 'secret', '*', [], before_msg, after_msg)
        self.assertEqual(recipient_messages1, recipient_messages2)

        recipient_messages2 = s.getMessages('recipient', 'secret', '*', [], before_msg, before_sender2_msg)
        self.assertEqual(recipient_messages1, recipient_messages2)

        um = json.loads(s.getMessages('recipient', 'secret', '*', [], before_msg, after_sender2_msg))
        self.assertEqual(len(um['messages']), 2)
        self.assertEqual(len(um['messages']['sender']), 1)
        self.assertEqual(len(um['messages']['sender2']), 1)
        self.assertEqual(um['messages']['sender'][0][1], "sender's message between times")
        self.assertEqual(um['messages']['sender2'][0][1], "sender2's message between times")

        um = json.loads(s.getNewMessages('recipient', 'secret', before_first_msg_from_sender2))
        self.assertEqual(len(um['messages']), 2)
        self.assertEqual(len(um['messages']['sender']), 1)
        self.assertEqual(um['messages']['sender'][0][1], "sender's message between times")

        self.assertEqual(len(um['messages']['sender2']), 2)
        self.assertEqual(um['messages']['sender2'][0][1], "Message from sender2")
        self.assertEqual(um['messages']['sender2'][1][1], "sender2's message between times")

        # Test getNewMessages. sender2 sent a message but didn't fetch it yet.
        # So we should be able to get it now.
        # We also send a message from sender... so we should get 2 msgs now.
        response = s.sendMessage('sender', 'secret', 'Sender McSend', 'sender2', "Message from sender to sender2")

        um = json.loads(s.getNewMessages('sender2', 'secret', before_first_msg_from_sender2))
        self.assertEqual(len(um['messages']), 2)
        self.assertEqual(len(um['messages']['sender']), 1)
        self.assertEqual(len(um['messages']['recipient']), 2)
        self.assertEqual(um['messages']['sender'][0][1], "Message from sender to sender2")
        self.assertEqual(um['messages']['recipient'][0][1], "Message from sender2")
        self.assertEqual(um['messages']['recipient'][1][1], "sender2's message between times")

        # last_msg_date must be the same date as sender's message, which was last
        self.assertEqual(um['last_msg_date'], um['messages']['sender'][0][2])
        last_msg_date = um['last_msg_date']

        # Now getNewMessages must return nothing
        um = json.loads(s.getNewMessages('sender2', 'secret', datetime.datetime.now(utc).isoformat()))
        self.assertEqual(um['messages'], {})
        self.assertEqual(um['last_msg_date'], last_msg_date)

        user = s.acl_users.getUser('sender2')
        last_cleared = user.last_cleared_date



    def test_chatroom_messaging(self):
        """ Test the 'sendMessage' and 'getMessages' methods, together with
            ChatRooms 
        """
        s = self._create_chatservice()
        s.register('user1', 'secret')
        s.register('user2', 'secret')
        s.register('user3', 'secret')
        s.register('user4', 'secret')

        chatroom1_path = '/Plone/chatrooms/chatroom1'

        # First test with a non-existing chatroom.
        um = json.loads(s.getMessages('user1', 'secret', None, ['non-existing-chatroom'], config.NULL_DATE, None,))
        self.assertEqual(um['status'], config.ERROR)
        self.assertEqual(um['errmsg'], "Chatroom 'ce40e7b6bdd89c5c80cc27ee4371f32387d3a92068d1e75ddf8496ad' doesn't exist")

        # We can also pass in a string (and not list of strings)
        um = json.loads(s.getMessages('user2', 'secret', None, 'non-existing-chatroom', config.NULL_DATE, None,))
        self.assertEqual(um['status'], config.ERROR)
        self.assertEqual(um['errmsg'], "Chatroom 'ce40e7b6bdd89c5c80cc27ee4371f32387d3a92068d1e75ddf8496ad' doesn't exist")

        # Ok, now let's create a ChatRoom
        resp = json.loads(s.createChatRoom('unkown_user', 'secret', chatroom1_path, ['user1']))
        self.assertEqual(resp['status'], config.AUTH_FAIL)

        resp = json.loads(s.createChatRoom('user1', 'secret', chatroom1_path, ['user1']))
        self.assertEqual(resp['status'], config.SUCCESS)

        self.assertEqual(s._getChatRoom(chatroom1_path).participants, ['user1'])

        # Lets add some participants. Authentication is required, but this can
        # be any registered user.
        resp = json.loads(s.addChatRoomParticipant('user1', 'secret', chatroom1_path, 'unregistered_user'))
        self.assertEqual(resp['status'], config.AUTH_FAIL)
        self.assertEqual(s._getChatRoom(chatroom1_path).participants, ['user1'])

        resp = json.loads(s.addChatRoomParticipant('unknown_user', 'secret', chatroom1_path, 'user2'))
        self.assertEqual(resp['status'], config.AUTH_FAIL)
        self.assertEqual(s._getChatRoom(chatroom1_path).participants, ['user1'])

        resp = json.loads(s.addChatRoomParticipant('user1', 'secret', 'bogus/path', 'user2'))
        self.assertEqual(resp['status'], config.NOT_FOUND)
        self.assertEqual(s._getChatRoom(chatroom1_path).participants, ['user1'])

        resp = json.loads(s.addChatRoomParticipant('user1', 'secret', chatroom1_path, 'user2'))
        self.assertEqual(resp['status'], config.SUCCESS)
        self.assertEqual(s._getChatRoom(chatroom1_path).participants, ['user1', 'user2'])

        # Now we add a new list of participants by calling editChatRoom
        participants = ['user1','user2', 'user3', 'user4']

        resp = json.loads(s.editChatRoom('unknown_user', 'secret', chatroom1_path, participants))
        self.assertEqual(resp['status'], config.AUTH_FAIL)

        resp = json.loads(s.editChatRoom('user1', 'secret', 'bogus/path', participants))
        self.assertEqual(resp['status'], config.NOT_FOUND)

        resp = json.loads(s.editChatRoom('user1', 'secret', chatroom1_path, participants))
        self.assertEqual(resp['status'], config.SUCCESS)
        self.assertEqual(s._getChatRoom(chatroom1_path).participants, ['user1', 'user2', 'user3', 'user4'])
        
        # test valid message sending
        resp = json.loads(s.sendChatRoomMessage('user1', 'secret', 'User 1', chatroom1_path, 'This is the message'))
        self.assertEqual(resp['status'], config.SUCCESS)
        self.assertTrue(bool(config.VALID_DATE_REGEX.search(resp['last_msg_date'])))
        message_timestamp = resp['last_msg_date']

        # test message sending to non-existent chatroom
        resp = json.loads(s.sendChatRoomMessage('user1', 'secret', 'User 1', 'non-existing-chatroom', 'This is the message'))
        self.assertEqual(resp['status'], config.ERROR)
        self.assertEqual(resp['errmsg'], "Chatroom 'non-existing-chatroom' doesn't exist")

        # test message sender with invalid credentials
        resp = json.loads(s.sendChatRoomMessage('user1', 'wrongpass', 'User 1', chatroom1_path, 'This is the message'))
        self.assertEqual(resp['status'], config.AUTH_FAIL)

        # Now, let's test message fetching
        um = json.loads(s.getMessages( 'user1', 'secret', None, [chatroom1_path], config.NULL_DATE, None,))
        self.assertEqual(um['status'], config.SUCCESS)
        # The returned datastructure looks as follows:
        #
        # {   'chatroom_messages': 
        #         {'Plone/chatrooms/chatroom1': [
        #                 ['user1', 'This is the message', '2011-10-18T20:16:27.592127+00:00']
        #             ]
        #         },
        #     'messages': {},
        #     'last_msg_date': '2011-10-18T20:16:27.592127+00:00',
        #     'status': 0
        # }
        self.assertEqual(um.keys(), ['status', 'messages', 'last_msg_date', 'chatroom_messages'])
        self.assertEqual(um['last_msg_date'], message_timestamp)
        msgdict = um['chatroom_messages'] 
        # Test that messages from only one chatroom was returned
        self.assertEqual(msgdict.keys(), [chatroom1_path])
        # Test that only one message was received from this user
        self.assertEqual(len(msgdict[chatroom1_path]), 1)
        # Test that the message tuple has 3 elements
        self.assertEqual(len(msgdict[chatroom1_path][0]), 4)
        # Test the message's last_msg_date
        self.assertTrue(bool(config.VALID_DATE_REGEX.search(msgdict[chatroom1_path][0][2])))
        self.assertEqual(msgdict[chatroom1_path][0][2], message_timestamp)
        self.assertEqual(msgdict[chatroom1_path][0][0], 'user1')
        self.assertEqual(msgdict[chatroom1_path][0][1], 'This is the message')

        # Now check if we get the same response for the other participants in
        # the chatroom
        db = json.loads(s.getMessages( 'user2', 'secret', None, [chatroom1_path], None, None,))
        self.assertEqual(db, um)
        db = json.loads(s.getMessages( 'user3', 'secret', None, [chatroom1_path], None, None,))
        self.assertEqual(db, um)
        db = json.loads(s.getMessages( 'user4', 'secret', None, [chatroom1_path], None, None,))
        self.assertEqual(db, um)

        # Test exact 'since' dates.
        db = json.loads(s.getMessages( 'user1', 'secret', None, [chatroom1_path], um['last_msg_date'], None,))
        self.assertEqual(db['messages'], {})
        self.assertEqual(db['chatroom_messages'], {})

        # Test exact 'until' date. This must return the message
        db = json.loads(s.getMessages( 'user1', 'secret', None, [chatroom1_path], None, um['last_msg_date'],))
        self.assertEqual(db, um)

        # Test getChatRoomMessages with multiple senders. 
        response = s.sendChatRoomMessage('user2', 'secret', 'User 2', chatroom1_path, 'another msg')
        response = json.loads(response)
        self.assertEqual(response['status'], config.SUCCESS)
        self.assertEqual(bool(config.VALID_DATE_REGEX.search(response['last_msg_date'])), True)
        message2_timestamp = response['last_msg_date']

        um = s.getMessages( 'user1', 'secret', None, chatroom1_path, config.NULL_DATE, None,)
        mdict = json.loads(um)
        self.assertEqual(mdict['status'], config.SUCCESS)
        self.assertEqual(mdict['last_msg_date'], message2_timestamp)

        db = s.getMessages( 'user2', 'secret', None, chatroom1_path, config.NULL_DATE, None,)
        self.assertEqual(db, um)
        db = s.getMessages( 'user3', 'secret', None, chatroom1_path, config.NULL_DATE, None,)
        self.assertEqual(db, um)

        db = json.loads(s.getNewMessages( 'user4', 'secret', config.NULL_DATE))
        self.assertEqual(db['status'], config.SUCCESS)
        self.assertEqual(db['last_msg_date'], message2_timestamp)

        self.assertEqual(db['chatroom_messages'][chatroom1_path][0][0], 'user1')
        self.assertEqual(db['chatroom_messages'][chatroom1_path][0][1], 'This is the message')
        self.assertEqual(db['chatroom_messages'][chatroom1_path][0][2], message_timestamp)

        self.assertEqual(db['chatroom_messages'][chatroom1_path][1][0], 'user2')
        self.assertEqual(db['chatroom_messages'][chatroom1_path][1][1], 'another msg')
        self.assertEqual(db['chatroom_messages'][chatroom1_path][1][2], message2_timestamp)
        self.assertEqual(db['messages'], {})

        db = s.getMessages( 'user4', 'secret', None, chatroom1_path, config.NULL_DATE, None,)
        self.assertEqual(db, um)

        db = s.getUnclearedMessages( 'user4', 'secret', None, chatroom1_path, None, False)
        self.assertEqual(db, um)

        db = s.getUnclearedMessages( 'user4', 'secret', None, chatroom1_path, None, False)
        self.assertEqual(db, um)

        db = s.getUnclearedMessages( 'user4', 'secret', None, chatroom1_path, None, True)
        self.assertEqual(db, um)

        db = json.loads(s.getUnclearedMessages( 'user4', 'secret', None, chatroom1_path, None, True))
        self.assertEqual(mdict['status'], config.SUCCESS)
        self.assertEqual(db['messages'], {})
        self.assertEqual(db['chatroom_messages'], {})

        # Finally, lets remove the chatroom
        resp = json.loads(s.removeChatRoom('unkown user', 'secret', chatroom1_path))
        self.assertEqual(resp['status'], config.AUTH_FAIL)

        resp = json.loads(s.removeChatRoom('user1', 'secret', chatroom1_path))
        self.assertEqual(resp['status'], config.SUCCESS)

        resp = json.loads(s.removeChatRoom('user1', 'secret', chatroom1_path))
        self.assertEqual(resp['status'], config.NOT_FOUND)

        folder = s._getChatRoomsFolder()
        self.assertEqual(len(folder.values()), 0)



def test_suite():
    from unittest import TestSuite, makeSuite
    suite = TestSuite()
    suite.addTest(makeSuite(TestChatService))
    return suite
