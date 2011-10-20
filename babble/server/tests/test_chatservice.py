import datetime
import simplejson as json
from pytz import utc

from Testing import ZopeTestCase as ztc
from ZPublisher import NotFound
from persistent.dict import PersistentDict

from Products.TemporaryFolder.TemporaryFolder import SimpleTemporaryContainer
from Products.Five import zcml
from babble.server import config

import Products.Five
ztc.installProduct('Five')
zcml.load_config('configure.zcml', package=Products.Five)

import babble.server
ztc.installProduct('babble.server')
zcml.load_config('configure.zcml', package=babble.server)

# Regex to test for ISO8601, i.e: '2011-09-30T15:49:35.417693+00:00'
# RE = re.compile(r'^\d{4}-\d{2}-\d{2}[ T]\d{2}:\d{2}:\d{2}\.\d{6}[+-]\d{2}:\d{2}$')

class TestChatService(ztc.ZopeTestCase):

    def afterSetUp(self):
        """ Adds a babble.server to the default fixture """
        view = self.app.unrestrictedTraverse('+/addChatService.html')
        self.assertEqual(type(view()), unicode) # Render the add form
        view(add_input_name='chat_service', title='Chat Service', submit_add=1)

        # The 'temp_folder' is not created for some reason, so do it here...
        self.app._setOb('temp_folder', SimpleTemporaryContainer('temp_folder'))

        self.chatservice = self.app.chat_service


    def test_register(self):
        """ Test the 'register' methods
        """
        s = self.chatservice
        status = s.register('username', 'password')
        status = json.loads(status)
        self.assertEquals(status['status'], config.SUCCESS)


    def test_user_access_dict(self):
        """ Test the '_getUserAccessDict' method
        """ 
        s = self.chatservice
        # We begin with no UAD.
        self.assertEqual(s.temp_folder.hasObject('user_access_dict'), False)

        uad = s._getCachedUserAccessDict()
        # The method should return an empty persistent dict
        self.assertEqual(uad, PersistentDict())

        # Now there should be a UAD
        assert(s.temp_folder.hasObject('user_access_dict'))

        # The cache should be set and it's expiry date must be in the future
        now = datetime.datetime.now()
        assert(getattr(s, '_v_cache_timeout') > now)
        self.assertEqual(getattr(s, '_v_user_access_dict'), PersistentDict())

        # Put a user into the UAD
        online_users = {'max_musterman':now}
        s._setUserAccessDict(**online_users)

        # Test that he is there
        uad = s._getUserAccessDict()
        self.assertEqual(uad, online_users)

        # Test that he is also in the cache (first make sure that the cache
        # timeout is in the future)
        delta = datetime.timedelta(seconds=30)
        cache_timeout = now + delta
        setattr(s, '_v_cache_timeout', cache_timeout)

        # Now test...
        uad = s._getCachedUserAccessDict()
        self.assertEqual(uad, online_users)

        # Wipe the UAD
        s.temp_folder._setOb('user_access_dict', PersistentDict())

        # The cached value should still be there...
        uad = s._getCachedUserAccessDict()
        self.assertEqual(uad, online_users)

        # Wipe the cache
        setattr(s, '_v_cache_timeout', now-delta)
        uad = s._getCachedUserAccessDict()
        self.assertEqual(uad, PersistentDict())

        # Put a user into the UAD
        online_users = {'maxine_musterman':now}
        s._setUserAccessDict(**online_users)

        # Test that he is there and in the cache...
        uad = s._getUserAccessDict()
        self.assertEqual(uad, online_users)

        now = datetime.datetime.now()
        assert(getattr(s, '_v_cache_timeout') > now)

        uad = s._getCachedUserAccessDict()
        self.assertEqual(uad, online_users)

        # Test that the 'user access dict' is recreated if it is deleted (which
        # is plausible since it's in a temp folder)
        s.temp_folder._delOb('user_access_dict')
        uad = s._getUserAccessDict()
        self.assertEqual(uad, PersistentDict())

        # Test the NotFound is raised when the 'temp_folder' is not there
        self.app._delOb('temp_folder')
        # Invalidate the cache
        self.assertRaises(NotFound, s._getUserAccessDict)
        delattr(s, '_v_user_access_dict')
        self.assertRaises(NotFound, s._getCachedUserAccessDict)


    def test_registration(self):
        """ Test the 'register', 'isRegistered', 'authenticate' and
            'setUserPassword'  methods.
        """
        s = self.chatservice
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
        s = self.chatservice
        u = 'username'
        s.register(u, u)
        self.assertEqual(s._isOnline(u), False)

        r = s.confirmAsOnline(None)
        r = json.loads(r)
        self.assertEquals(r['status'], config.ERROR)

        # Test that a user entry was made into the 'user access dict'
        s.confirmAsOnline(u)
        uad = s._getUserAccessDict()
        self.assertEqual(uad.get(u, None) != None, True)

        self.assertEqual(s._isOnline(u), True)

        now = datetime.datetime.now()
        
        # Test that a user that was confirmed as online 59 seconds ago (i.e
        # less than a minute) is still considered as online.
        delta = datetime.timedelta(seconds=59)
        uad[u] = datetime.datetime.now() - delta
        self.assertEqual(s._isOnline(u), True)

        ou = s.getOnlineUsers()
        ou = json.loads(ou)
        self.assertEquals(ou['status'], config.SUCCESS)
        self.assertEquals(ou['online_users'], [u])

        # Test that a user that was confirmed as online one minute ago (i.e
        # at least a minute) is now considered as offline.
        delta = datetime.timedelta(minutes=1)
        uad[u] = datetime.datetime.now() - delta
        self.assertEqual(s._isOnline(u), False)

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


    def test_messaging(self):
        """ Test sendMessage, getMessages, getNewMessages and related methods """
        s = self.chatservice
        s.register('sender', 'secret')
        s.register('recipient', 'secret')

        # Delete the Conversations folder to check that it gets recreated.
        s.manage_delObjects(['conversations'])
        um = json.loads(s.getMessages('recipient', 'secret', None, [], config.NULL_DATE, None,))
        self.assertEqual(um['status'], config.SUCCESS)
        self.assertTrue(hasattr(s, 'conversations'))

        um = s.getMessages('recipient', 'secret', None, [], config.NULL_DATE, None)
        um = json.loads(um)
        self.assertEqual(um['status'], config.SUCCESS)
        self.assertEqual(um['messages'], {})

        # test authentication
        response = json.loads(s.sendMessage('sender', 'wrongpass', 'recipient', 'This is the message'))
        self.assertEqual(response['status'], config.AUTH_FAIL)

        response = json.loads(s.getMessages('sender', 'wrongpass', None, [], None, None))
        self.assertEqual(response['status'], config.AUTH_FAIL)

        um = json.loads(s.getNewMessages('recipient', 'wrongpass', 'sender', []))
        self.assertEqual(um['status'], config.AUTH_FAIL)

        um = json.loads(s.getUnclearedMessages('recipient', 'wrongpass', 'sender', [], False))
        self.assertEqual(um['status'], config.AUTH_FAIL)

        # Test invalid date.
        um = json.loads(s.getMessages('recipient', 'secret', 'sender', [], '123512512351235', None))
        self.assertEqual(um['status'], config.ERROR)
        self.assertEqual(um['errmsg'], 'Invalid date format')

        um = json.loads(s.getMessages('recipient', 'secret', 'sender', [], None, '123512512351235'))
        self.assertEqual(um['status'], config.ERROR)
        self.assertEqual(um['errmsg'], 'Invalid date format')
        
        # test valid message sending
        response = s.sendMessage('sender', 'secret', 'recipient', 'This is the message')
        response = json.loads(response)
        self.assertEqual(response['status'], config.SUCCESS)
        self.assertTrue(bool(config.VALID_DATE_REGEX.search(response['last_msg_date'])))
        message_timestamp = response['last_msg_date']

        um = json.loads(s.getMessages( 'recipient', 'secret', None, [], config.NULL_DATE, None, ))
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

        # Test that the recipient now has an updated last_msg_date attr
        user = s.acl_users.getUser('recipient')
        self.assertEqual(um['last_msg_date'], user.last_received_date)

        # The sender didn't call getMessages yet, so his last_msg_date must be NULL_DATE
        user = s.acl_users.getUser('sender')
        self.assertEqual(config.NULL_DATE, user.last_received_date)

        msgdict = um['messages'] 
        # Test that messages from only one user was returned
        self.assertEqual(msgdict.keys(), ['sender'])
        # Test that only one message was received from this user
        self.assertEqual(len(msgdict['sender']), 1)
        # Test that the message tuple has 3 elements
        self.assertEqual(len(msgdict['sender'][0]), 3)
        self.assertEqual(msgdict['sender'][0][0], 'sender')
        self.assertEqual(msgdict['sender'][0][1], 'This is the message')
        self.assertEqual(msgdict['sender'][0][2], message_timestamp)
        self.assertTrue(bool(config.VALID_DATE_REGEX.search(msgdict['sender'][0][2])))

        # Test that we get the same results again.
        db = json.loads(s.getMessages( 'recipient', 'secret', None, [], None, None, ))
        self.assertEqual(db, um)

        # Test exact 'since' dates. 
        db = json.loads(s.getMessages( 'recipient', 'secret', None, [], um['last_msg_date'], None, ))
        self.assertEqual(db['messages'], {})

        # Test exact 'until' date. This must return the message
        db = json.loads(s.getMessages( 'recipient', 'secret', None, [], None, um['last_msg_date'], ))
        self.assertEqual(db, um)

        # Test that the sender also gets the same results
        db = json.loads(s.getMessages( 'sender', 'secret', None, [], None, um['last_msg_date'], ))
        self.assertEqual(db.keys(), ['status', 'messages', 'last_msg_date', 'chatroom_messages'])
        self.assertEqual(db['last_msg_date'], message_timestamp)

        msgdict = db['messages'] 
        # Test that messages from only one user was returned
        self.assertEqual(msgdict.keys(), ['recipient'])
        # Test that only one message was received from this user
        self.assertEqual(len(msgdict['recipient']), 1)
        # Test that the message tuple has 3 elements
        self.assertEqual(len(msgdict['recipient'][0]), 3)
        self.assertTrue(bool(config.VALID_DATE_REGEX.search(msgdict['recipient'][0][2])))
        self.assertEqual(msgdict['recipient'][0][2], message_timestamp)
        self.assertEqual(msgdict['recipient'][0][0], 'sender')
        self.assertEqual(msgdict['recipient'][0][1], 'This is the message')

        # Test that the recipient now has an updated last_received_date attr
        user = s.acl_users.getUser('sender')
        self.assertEqual(db['last_msg_date'], user.last_received_date)

        # Test getMessages with multiple senders. 
        s.register('sender2', 'secret')
        response = s.sendMessage('sender2', 'secret', 'recipient', 'Message from sender2')
        response = json.loads(response)
        self.assertEqual(response['status'], config.SUCCESS)
        self.assertEqual(bool(config.VALID_DATE_REGEX.search(response['last_msg_date'])), True)
        message2_timestamp = response['last_msg_date']

        um = json.loads(s.getMessages('recipient', 'secret', None, [], config.NULL_DATE, None))
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
        self.assertEqual(len(msgdict['sender'][0]), 3)
        self.assertEqual(len(msgdict['sender2'][0]), 3)

        self.assertEqual(msgdict['sender2'][0][0], 'sender2')
        self.assertEqual(msgdict['sender2'][0][1], 'Message from sender2')

        recipient_messages = um
        # Now test that the sender also will get the message he sent...
        sender2_messages = json.loads(s.getMessages('sender2', 'secret', 'recipient', [], config.NULL_DATE, None,))
        self.assertEqual(sender2_messages.keys(), recipient_messages.keys())
        self.assertEqual(sender2_messages['status'], recipient_messages['status'])
        self.assertEqual(sender2_messages['last_msg_date'], recipient_messages['last_msg_date'])
        self.assertEqual(sender2_messages['messages']['recipient'], recipient_messages['messages']['sender2'])

        user = s.acl_users.getUser('sender2')
        self.assertEqual(um['last_msg_date'], user.last_received_date)
        last_date_sender2 = user.last_received_date

        # Test for messages sent after message_timestamp. This should not return messages.
        um = json.loads(s.getMessages('recipient', 'secret', None, [], recipient_messages['last_msg_date'], None))
        self.assertEqual(um['status'], config.SUCCESS)
        self.assertEqual(um['messages'], {})
        self.assertEqual(um['last_msg_date'], config.NULL_DATE)

        # Test that the recipient now has an updated last_msg_date attr
        user = s.acl_users.getUser('sender2')
        self.assertEqual(sender2_messages['last_msg_date'], user.last_received_date)

        # Test with finer date ranges via 'since' and 'until'
        before_msg = datetime.datetime.now(utc).isoformat()

        response = s.sendMessage('sender', 'secret', 'recipient', "sender's message between times")
        response = json.loads(response)
        self.assertEqual(response['status'], config.SUCCESS)

        after_msg = datetime.datetime.now(utc).isoformat()

        um = json.loads(s.getMessages('recipient', 'secret', None, [], config.NULL_DATE, None))
        msgs = um['messages'] 
        self.assertEqual(um['status'], config.SUCCESS)
        self.assertEqual(len(um['messages']['sender']), 2)
        self.assertEqual(len(um['messages']['sender2']), 1)

        recipient_messages1 = s.getMessages('recipient', 'secret', None, [], before_msg, after_msg)
        um = json.loads(recipient_messages1)
        self.assertEqual(um['status'], config.SUCCESS)
        self.assertEqual(len(um['messages']['sender']), 1)
        self.assertEqual(um['messages']['sender'][0][1], "sender's message between times")

        sender_messages = json.loads(s.getMessages('sender', 'secret', None, [], before_msg, after_msg))
        self.assertEqual(sender_messages['status'], config.SUCCESS)
        self.assertEqual(len(sender_messages['messages']['recipient']), 1)
        self.assertEqual(sender_messages['messages']['recipient'][0][1], "sender's message between times")

        # Test getMessages between times and with multiple senders. 
        before_sender2_msg = datetime.datetime.now(utc).isoformat()
        response = s.sendMessage('sender2', 'secret', 'recipient', "sender2's message between times")
        response = json.loads(response)
        self.assertEqual(response['status'], config.SUCCESS)
        after_sender2_msg = datetime.datetime.now(utc).isoformat()

        recipient_messages2 = s.getMessages('recipient', 'secret', None, [], before_msg, after_msg)
        self.assertEqual(recipient_messages1, recipient_messages2)

        recipient_messages2 = s.getMessages('recipient', 'secret', None, [], before_msg, before_sender2_msg)
        self.assertEqual(recipient_messages1, recipient_messages2)

        um = json.loads(s.getMessages('recipient', 'secret', None, [], before_msg, after_sender2_msg))
        self.assertEqual(len(um['messages']), 2)
        self.assertEqual(len(um['messages']['sender']), 1)
        self.assertEqual(len(um['messages']['sender2']), 1)
        self.assertEqual(um['messages']['sender'][0][1], "sender's message between times")
        self.assertEqual(um['messages']['sender2'][0][1], "sender2's message between times")

        um = json.loads(s.getMessages('recipient', 'secret', None, [], before_sender2_msg, after_sender2_msg))
        self.assertEqual(len(um['messages']), 1)
        self.assertEqual(len(um['messages']['sender2']), 1)
        self.assertEqual(um['messages']['sender2'][0][1], "sender2's message between times")

        # Test that the recipient now has an updated last_msg_date attr
        user = s.acl_users.getUser('recipient')
        self.assertEqual(um['last_msg_date'], user.last_received_date)

        # Test getNewMessages. sender2 sent a message but didn't fetch it yet.
        # So we should be able to get it now.
        # We also send a message from sender... so we should get 2 msgs now.
        response = s.sendMessage('sender', 'secret', 'sender2', "Message from sender to sender2")

        user = s.acl_users.getUser('sender2')
        last_date_sender2 = user.last_received_date

        um = json.loads(s.getNewMessages('sender2', 'secret', None, []))
        self.assertEqual(len(um['messages']), 2)
        self.assertEqual(len(um['messages']['sender']), 1)
        self.assertEqual(len(um['messages']['recipient']), 1)
        self.assertEqual(um['messages']['sender'][0][1], "Message from sender to sender2")
        self.assertEqual(um['messages']['recipient'][0][1], "sender2's message between times")

        user = s.acl_users.getUser('sender2')
        self.assertEqual(um['last_msg_date'], user.last_received_date)

        # last_msg_date must be the same date as sender's message, which was last
        self.assertEqual(um['last_msg_date'], um['messages']['sender'][0][2])

        # Now getNewMessages must return nothing
        um = json.loads(s.getNewMessages('sender2', 'secret', None, []))
        self.assertEqual(um['messages'], {})
        self.assertEqual(um['last_msg_date'], config.NULL_DATE)



    def test_chatroom_messaging(self):
        """ Test the 'sendMessage' and 'getMessages' methods, together with
            ChatRooms 
        """
        s = self.chatservice
        s.register('user1', 'secret')
        s.register('user2', 'secret')
        s.register('user3', 'secret')
        s.register('user4', 'secret')

        # First test with a non-existing chatroom.
        um = json.loads(s.getMessages('user1', 'secret', None, ['non-existing-chatroom'], config.NULL_DATE, None,))
        self.assertEqual(um['status'], config.ERROR)
        self.assertEqual(um['errmsg'], "Chatroom 'non-existing-chatroom' doesn't exist")

        # We can also pass in a string (and not list of strings)
        um = json.loads(s.getMessages('user2', 'secret', None, 'non-existing-chatroom', config.NULL_DATE, None,))
        self.assertEqual(um['status'], config.ERROR)
        self.assertEqual(um['errmsg'], "Chatroom 'non-existing-chatroom' doesn't exist")

        # Ok, now let's create a ChatRoom
        s.createChatRoom('chatroom1', ['user1', 'user2', 'user3', 'user4'])
        
        # test valid message sending
        response = json.loads(s.sendChatRoomMessage('user1', 'secret', 'chatroom1', 'This is the message'))
        self.assertEqual(response['status'], config.SUCCESS)
        self.assertTrue(bool(config.VALID_DATE_REGEX.search(response['last_msg_date'])))
        message_timestamp = response['last_msg_date']

        # test message sending to non-existent chatroom
        response = json.loads(s.sendChatRoomMessage('user1', 'secret', 'non-existing-chatroom', 'This is the message'))
        self.assertEqual(response['status'], config.ERROR)
        self.assertEqual(response['errmsg'], "Chatroom 'non-existing-chatroom' doesn't exist")

        # test message sender with invalid credentials
        response = json.loads(s.sendChatRoomMessage('user1', 'wrongpass', 'chatroom1', 'This is the message'))
        self.assertEqual(response['status'], config.AUTH_FAIL)

        # Now, let's test message fetching
        um = json.loads(s.getMessages( 'user1', 'secret', None, ['chatroom1'], config.NULL_DATE, None,))
        self.assertEqual(um['status'], config.SUCCESS)
        # The returned datastructure looks as follows:
        #
        # {   'chatroom_messages': 
        #         {'chatroom1': [
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
        self.assertEqual(msgdict.keys(), ['chatroom1'])
        # Test that only one message was received from this user
        self.assertEqual(len(msgdict['chatroom1']), 1)
        # Test that the message tuple has 3 elements
        self.assertEqual(len(msgdict['chatroom1'][0]), 3)
        # Test the message's last_msg_date
        self.assertTrue(bool(config.VALID_DATE_REGEX.search(msgdict['chatroom1'][0][2])))
        self.assertEqual(msgdict['chatroom1'][0][2], message_timestamp)
        self.assertEqual(msgdict['chatroom1'][0][0], 'user1')
        self.assertEqual(msgdict['chatroom1'][0][1], 'This is the message')

        # Now check if we get the same response for the other participants in
        # the chatroom
        db = json.loads(s.getMessages( 'user2', 'secret', None, ['chatroom1'], None, None,))
        self.assertEqual(db, um)
        db = json.loads(s.getMessages( 'user3', 'secret', None, ['chatroom1'], None, None,))
        self.assertEqual(db, um)
        db = json.loads(s.getMessages( 'user4', 'secret', None, ['chatroom1'], None, None,))
        self.assertEqual(db, um)

        # Test exact 'since' dates.
        db = json.loads(s.getMessages( 'user1', 'secret', None, ['chatroom1'], um['last_msg_date'], None,))
        self.assertEqual(db['messages'], {})
        self.assertEqual(db['chatroom_messages'], {})

        # Test exact 'until' date. This must return the message
        db = json.loads(s.getMessages( 'user1', 'secret', None, ['chatroom1'], None, um['last_msg_date'],))
        self.assertEqual(db, um)

        # Test getChatRoomMessages with multiple senders. 
        response = s.sendChatRoomMessage('user2', 'secret', 'chatroom1', 'another msg')
        response = json.loads(response)
        self.assertEqual(response['status'], config.SUCCESS)
        self.assertEqual(bool(config.VALID_DATE_REGEX.search(response['last_msg_date'])), True)
        message2_timestamp = response['last_msg_date']

        um = s.getMessages( 'user1', 'secret', None, 'chatroom1', config.NULL_DATE, None,)
        mdict = json.loads(um)
        self.assertEqual(mdict['status'], config.SUCCESS)
        self.assertEqual(mdict['last_msg_date'], message2_timestamp)

        db = s.getMessages( 'user2', 'secret', None, 'chatroom1', config.NULL_DATE, None,)
        self.assertEqual(db, um)
        db = s.getMessages( 'user3', 'secret', None, 'chatroom1', config.NULL_DATE, None,)
        self.assertEqual(db, um)

        db = json.loads(s.getNewMessages( 'user4', 'secret', None, 'chatroom1'))
        self.assertEqual(db['status'], config.SUCCESS)
        self.assertEqual(db['last_msg_date'], message2_timestamp)
        self.assertEqual(db['chatroom_messages']['chatroom1'][0][0], 'user2')
        self.assertEqual(db['chatroom_messages']['chatroom1'][0][1], 'another msg')
        self.assertEqual(db['chatroom_messages']['chatroom1'][0][2], message2_timestamp)

        db = s.getMessages( 'user4', 'secret', None, 'chatroom1', config.NULL_DATE, None,)
        self.assertEqual(db, um)

        db = s.getUnclearedMessages( 'user4', 'secret', None, 'chatroom1', False)
        self.assertEqual(db, um)

        db = s.getUnclearedMessages( 'user4', 'secret', None, 'chatroom1', True)
        self.assertEqual(db, um)

        db = json.loads(s.getUnclearedMessages( 'user4', 'secret', None, 'chatroom1', True))
        self.assertEqual(mdict['status'], config.SUCCESS)
        self.assertEqual(db['messages'], {})
        self.assertEqual(db['chatroom_messages'], {})



def test_suite():
    from unittest import TestSuite, makeSuite
    suite = TestSuite()
    suite.addTest(makeSuite(TestChatService))
    return suite
