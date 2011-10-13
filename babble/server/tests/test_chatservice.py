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


    def test_get_user(self):
        """ Test the '_getUser', and 'register' methods
        """
        s = self.chatservice
        self.assertRaises(NotFound, s._getUser, 'username')

        status = s.register('username', 'password')
        status = json.loads(status)
        self.assertEquals(status['status'], config.SUCCESS)

        self.assertEqual('username', s._getUser('username').id)


    def test_get_users_folder(self):
        """ Test the '_getUsersFolder' method
        """ 
        s = self.chatservice
        f = s._getUsersFolder()
        self.assertEqual(f, s.users)
        
        s.manage_delObjects(['users'])
        f = s._getUsersFolder()
        self.assertEqual(f, s.users)


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
        r = s.register('user name', 'password')
        r = json.loads(r)
        self.assertEquals(r['status'], config.ERROR)

        s.register('username', 'password')
        self.assertEqual('username', s._getUser('username').id)

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


    def test_status(self):
        """ Test the 'setStatus' and 'getStatus' methods
        """
        s = self.chatservice
        u = 'username'
        p = 'secret'
        s.register(u, p)

        self.assertEqual(json.loads(s.getStatus(u))['userstatus'], 'offline')

        s.confirmAsOnline(u)
        self.assertEqual(json.loads(s.getStatus(u))['userstatus'], 'online')

        # Test authentication
        response = s.setStatus(u, 'wrongpass', 'busy')
        self.assertEqual(json.loads(response)['status'], config.AUTH_FAIL)
        self.assertEqual(json.loads(s.getStatus(u))['userstatus'], 'online')

        response = s.setStatus(u, p, 'busy')
        self.assertEqual(json.loads(response)['status'], config.SUCCESS)
        self.assertEqual(json.loads(s.getStatus(u))['userstatus'], 'busy')

        response = s.setStatus(u, p, 'away')
        self.assertEqual(json.loads(response)['status'], config.SUCCESS)
        self.assertEqual(json.loads(s.getStatus(u))['userstatus'], 'away')

        # Simulate one minute of time passing and then test the that user's
        # status is 'offline'
        delta = datetime.timedelta(minutes=1)
        uad = s._getUserAccessDict()
        uad[u] = datetime.datetime.now() - delta
        self.assertEqual(json.loads(s.getStatus(u))['userstatus'], 'offline')


    def test_messaging(self):
        """ Test the 'sendMessage' and 'getMessages' methods """
        s = self.chatservice
        s.register('sender', 'secret')
        s.register('recipient', 'secret')

        # Delete the Conversations folder to check that it gets recreated.
        s.manage_delObjects(['conversations'])
        um = s.getMessages('recipient', 'secret', None, config.NULL_DATE)
        um = json.loads(um)
        self.assertEqual(um['status'], config.SUCCESS)
        self.assertTrue(hasattr(s, 'conversations'))

        um = s.getMessages('recipient', 'secret', None, config.NULL_DATE)
        um = json.loads(um)
        self.assertEqual(um['status'], config.SUCCESS)
        self.assertEqual(um['messages'], {})

        # test authentication
        response = s.sendMessage('sender', 'wrongpass', 'recipient', 'This is the message')
        response = json.loads(response)
        self.assertEqual(response['status'], config.AUTH_FAIL)

        response = s.sendMessage('sender', 'secret', 'recipient', 'This is the message')
        response = json.loads(response)
        self.assertEqual(response['status'], config.SUCCESS)
        self.assertTrue(bool(config.VALID_DATE_REGEX.search(response['last_msg_date'])))
        message_timestamp = response['last_msg_date']

        um = s.getMessages('recipient', 'secret', None, config.NULL_DATE)
        um = json.loads(um)
        self.assertEqual(um['status'], config.SUCCESS)

        db = s.getMessages('recipient', 'secret', None, config.NULL_DATE)
        db = json.loads(db)
        self.assertEqual(um, db)
        # The returned datastructure looks as follows:
        # {
        #   'messages': {
        #       'sender': [ ['sender', '2011/10/04', '08:41', 'message', '2011-10-04T08:41:31.533527+00:00'] ]
        #     }, 
        #   'status': 0, 
        #   'last_msg_date': '2011-10-04T08:41:31.533527+00:00'
        # }
        self.assertEqual(um.keys(), ['status', 'messages', 'last_msg_date', ])
        self.assertEqual(um['last_msg_date'], message_timestamp)

        msgdict = um['messages'] 
        # Test that messages from only one user was returned
        self.assertEqual(msgdict.keys(), ['sender'])
        # Test that only one message was received from this user
        self.assertEqual(len(msgdict['sender']), 1)
        # Test that the message tuple has 3 elements
        self.assertEqual(len(msgdict['sender'][0]), 3)
        # Test the message's last_msg_date
        self.assertTrue(bool(config.VALID_DATE_REGEX.search(msgdict['sender'][0][2])))
        self.assertEqual(msgdict['sender'][0][2], message_timestamp)
        # Test the senders username
        self.assertEqual(msgdict['sender'][0][0], 'sender')
        # Test that message text
        self.assertEqual(msgdict['sender'][0][1], 'This is the message')

        # Test getMessages with multiple senders. We didn't mark the
        # previous sender's messages as 'read', so they should be returned
        # again.
        s.register('sender2', 'secret')
        response = s.sendMessage('sender2', 'secret', 'recipient', 'another msg')
        response = json.loads(response)
        self.assertEqual(response['status'], config.SUCCESS)
        self.assertEqual(bool(config.VALID_DATE_REGEX.search(response['last_msg_date'])), True)
        message2_timestamp = response['last_msg_date']

        um = s.getMessages('recipient', 'secret', None, config.NULL_DATE, mark_cleared=True)
        um = json.loads(um)
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
        self.assertEqual(msgdict['sender2'][0][1], 'another msg')

        # Test for uncleared messages sent after message_timestamp. This should not
        # return messages.
        um = s.getMessages('recipient', 'secret', None, message2_timestamp, cleared_status=False)
        um = json.loads(um)
        self.assertEqual(um['status'], config.SUCCESS)
        self.assertEqual(um['messages'], {})
        self.assertEqual(um['last_msg_date'], config.NULL_DATE)


        response = s.sendMessage('sender', 'secret', 'recipient', 'message')
        response = json.loads(response)
        self.assertEqual(response['status'], config.SUCCESS)
        self.assertTrue(bool(config.VALID_DATE_REGEX.search(response['last_msg_date'])))
        message_timestamp = response['last_msg_date']

        # Test authentication
        um = s.getMessages('recipient', 
                           'wrongpass', 
                           'sender', 
                           config.NULL_DATE,
                           cleared_status=False,
                           mark_cleared=False)
        um = json.loads(um)
        self.assertEqual(um['status'], config.AUTH_FAIL)

        # Test invalid date.
        um = s.getMessages('recipient', 
                           'secret', 
                           'sender', 
                           '123512512351235',
                           cleared_status=False,
                           mark_cleared=False)
        um = json.loads(um)
        self.assertEqual(um['status'], config.ERROR)
        
        # Test invalid pars.
        um = s.getMessages('recipient', 
                           'secret', 
                           'sender', 
                           config.NULL_DATE,
                           cleared_status='True',
                           mark_cleared=False)
        um = json.loads(um)
        self.assertEqual(um['status'], config.ERROR)
        
        um = s.getMessages('recipient', 
                           'secret', 
                           'sender', 
                           config.NULL_DATE,
                           cleared_status='True',
                           mark_cleared='False')
        um = json.loads(um)
        self.assertEqual(um['status'], config.ERROR)

        # Test with valid inputs
        recipient_messages = s.getMessages(
                            'recipient', 
                            'secret', 
                            'sender', 
                            config.NULL_DATE,
                            cleared_status=False,
                            mark_cleared=False)
        recipient_messages = json.loads(recipient_messages)
        self.assertEqual(recipient_messages['status'], config.SUCCESS)
        self.assertEqual(recipient_messages.keys(), ['status', 'messages', 'last_msg_date'])
        self.assertEqual(recipient_messages['last_msg_date'], message_timestamp)

        # The uncleared messages datastructure looks as follows:
        # {
        #     'status': 0,
        #     'last_msg_date': '2011-09-30T12:43:49+00:00'
        #     'messages': {
        #             'sender': [ ['sender', '2011/09/30', '12:43', 'first message', '2011-09-30T12:43:49+00:00'] ]
        #           },
        # }

        # Check that there is a ISO8601 last_msg_date.
        self.assertTrue(bool(config.VALID_DATE_REGEX.search(recipient_messages['last_msg_date'])))

        msgs = recipient_messages['messages'] 
        # Test that messages from only one user was returned
        self.assertEqual(len(msgs), 1)
        # Test that only one message was received from this user
        self.assertEqual(len(msgs.values()[0]), 1)
        # Test that the message tuple has 3 elements
        self.assertEqual(len(msgs.values()[0][0]), 3)
        # Test the message's last_msg_date
        self.assertTrue(bool(config.VALID_DATE_REGEX.search(msgs.values()[0][0][2])))
        self.assertEqual(msgs.values()[0][0][2], message_timestamp)
        # Test that senders username
        self.assertEqual(msgs.values()[0][0][0], 'sender')
        # Test that message text
        self.assertEqual(msgs.values()[0][0][1], 'message')

        # Now test that the sender also will get the message he sent...
        sender_messages = s.getMessages(
                            'sender', 
                            'secret', 
                            'recipient', 
                            config.NULL_DATE,
                            cleared_status=False,
                            mark_cleared=False)
        sender_messages = json.loads(sender_messages)

        self.assertEqual(sender_messages.keys(), recipient_messages.keys())
        self.assertEqual(sender_messages['status'], recipient_messages['status'])
        self.assertEqual(sender_messages['last_msg_date'], recipient_messages['last_msg_date'])
        self.assertEqual(sender_messages['messages']['recipient'], recipient_messages['messages']['sender'])


        # Test getMessages with multiple senders. We didn't mark the
        # previous sender's messages as 'clear', so they should be returned
        # again.
        response = s.sendMessage('sender2', 'secret', 'recipient', 'another msg')
        response = json.loads(response)
        self.assertEqual(response['status'], config.SUCCESS)
        self.assertEqual(bool(config.VALID_DATE_REGEX.search(response['last_msg_date'])), True)
        message2_timestamp = response['last_msg_date']

        um = s.getMessages('recipient', 
                           'secret', 
                           None, 
                           config.NULL_DATE, 
                           cleared_status=False,
                           mark_cleared=True)
        um = json.loads(um)
        self.assertEqual(um['status'], config.SUCCESS)
        # Test that messages from two users were returned
        msgs = um['messages'] 
        self.assertEqual(len(msgs), 2)
        # Test that only one message was received from each
        self.assertEqual(len(msgs.values()[0]), 1)
        self.assertEqual(len(msgs.values()[1]), 1)

        # Test the messages' last_msg_dates
        self.assertEqual(msgs['sender'][0][2], message_timestamp)
        self.assertEqual(msgs['sender2'][0][2], message2_timestamp)

        # Test the properties of the message sent by sender1
        self.assertEqual(len(msgs.values()[1][0]), 3)
        self.assertEqual(msgs['sender2'][0][0], 'sender2')
        self.assertEqual(msgs['sender2'][0][1], 'another msg')
        self.assertTrue(bool(config.VALID_DATE_REGEX.search(msgs['sender2'][0][2])))

        # Check that the global last_msg_date is the same as the last message's
        self.assertEqual(um['last_msg_date'], msgs['sender2'][0][2])

        # All the uncleared messages for 'recipient' has now been marked as clear,
        # lets test that no new messages are returned
        um = s.getMessages('recipient', 
                           'secret', 
                           None, 
                           config.NULL_DATE,
                           cleared_status=False,
                           mark_cleared=False)
        um = json.loads(um)
        self.assertEqual(um['status'], config.SUCCESS)
        self.assertEqual(um['messages'], {})
        self.assertEqual(um['last_msg_date'], config.NULL_DATE)

        before_first_msg = datetime.datetime.now(utc).isoformat()

        response = s.sendMessage('sender', 'secret', 'recipient', 'xxx message')
        response = json.loads(response)
        self.assertEqual(response['status'], config.SUCCESS)

        um = s.getMessages('recipient', 'secret', None, since=config.NULL_DATE, cleared_status=False)
        um = json.loads(um)
        self.assertEqual(um['status'], config.SUCCESS)
        self.assertEqual(len(msgs), 2)

        um = s.getMessages('recipient', 'secret', None, since=config.NULL_DATE, cleared_status=False)
        um = json.loads(um)
        msgs = um['messages'] 
        # Test that messages from only one user was returned
        self.assertEqual(len(msgs), 1)
        self.assertEqual(um['status'], config.SUCCESS)

        # Check that there is a last_msg_date.
        self.assertTrue(bool(config.VALID_DATE_REGEX.search(um['last_msg_date'])))
        self.assertEqual(um['last_msg_date'] > before_first_msg, True)

        # Test that only one message was received from this user
        self.assertEqual(len(msgs.values()[0]), 1)
        # Test that the message tuple has 3 elements
        self.assertEqual(len(msgs.values()[0][0]), 3)
        # Test that senders username
        self.assertEqual(msgs.values()[0][0][0], 'sender')
        # Test that message text
        self.assertEqual(msgs.values()[0][0][1], 'xxx message')


        # Test getMessages with multiple senders. 
        before_second_msg = datetime.datetime.now(utc).isoformat()
        response = s.sendMessage('sender2', 'secret', 'recipient', 'second message')
        response = json.loads(response)
        self.assertEqual(response['status'], config.SUCCESS)

        after_second_msg = datetime.datetime.now(utc).isoformat()

        um = s.getMessages('recipient', 'secret', None, since=before_first_msg, cleared_status=False)
        um = json.loads(um)
        self.assertEqual(um['status'], config.SUCCESS)
        # Test that messages from two users were returned
        msgs = um['messages'] 
        self.assertEqual(len(msgs), 2)
        # Test that only one message was received from each
        self.assertEqual(len(msgs.values()[0]), 1)
        self.assertEqual(len(msgs.values()[1]), 1)

        # Test the properties of the message sent by sender1
        self.assertEqual(len(msgs.values()[1][0]), 3)
        self.assertEqual(msgs['sender2'][0][0], 'sender2')
        self.assertEqual(msgs['sender2'][0][1], 'second message')
        self.assertTrue(bool(config.VALID_DATE_REGEX.search(msgs['sender2'][0][2])))

        # Check that the global last_msg_date is the same as the last message's
        self.assertEqual(um['last_msg_date'], msgs['sender2'][0][2])

        # Now we make that date later than the first message, so we should only
        # receive the second one.
        um = s.getMessages('recipient', 'secret', None, since=before_second_msg, cleared_status=False)
        um = json.loads(um)

        self.assertEqual(um['status'], config.SUCCESS)
        msgs = um['messages'] 
        self.assertEqual(len(msgs), 1)
        self.assertEqual(msgs.values()[0][0][0], 'sender2')
        self.assertEqual(msgs.values()[0][0][1], 'second message')
        self.assertTrue(bool(config.VALID_DATE_REGEX.search(msgs['sender2'][0][2])))

        # Check that there is a ISO8601 last_msg_date.
        self.assertTrue(bool(config.VALID_DATE_REGEX.search(um['last_msg_date'])))
        self.assertEqual(um['last_msg_date'] > before_second_msg, True)
        self.assertEqual(um['last_msg_date'] < after_second_msg, True)
        # Check that the global last_msg_date is the same as the last (and only) message's
        self.assertEqual(um['last_msg_date'], msgs['sender2'][0][2])


def test_suite():
    from unittest import TestSuite, makeSuite
    suite = TestSuite()
    suite.addTest(makeSuite(TestChatService))
    return suite
