import datetime
import re 
import simplejson as json
from pytz import utc

from Testing import ZopeTestCase as ztc
from ZPublisher import NotFound
from persistent.dict import PersistentDict

from Products.TemporaryFolder.TemporaryFolder import SimpleTemporaryContainer
from Products.Five import zcml
from babble.server.config import SUCCESS
from babble.server.config import AUTH_FAIL
from babble.server import config

import Products.Five
ztc.installProduct('Five')
zcml.load_config('configure.zcml', package=Products.Five)

import babble.server
ztc.installProduct('babble.server')
zcml.load_config('configure.zcml', package=babble.server)

# Regex to test for ISO8601, i.e: '2011-09-30T15:49:35.417693+00:00'
RE = re.compile(r'^\d{4}-\d{2}-\d{2}[ T]\d{2}:\d{2}:\d{2}\.\d{6}[+-]\d{2}:\d{2}$')

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
        self.assertEquals(status['status'], SUCCESS)

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
        s.register('username', 'password')
        self.assertEqual('username', s._getUser('username').id)

        r = s.isRegistered('username')
        r = json.loads(r)
        self.assertEquals(r['status'], SUCCESS)
        self.assertEquals(r['is_registered'], True)

        auth = s._authenticate('username', 'password')
        self.assertEqual(auth != None, True)
        self.assertEqual(auth.name, 'username')

        r = s.isRegistered('nobody')
        r = json.loads(r)
        self.assertEquals(r['status'], SUCCESS)
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
        self.assertEquals(ou['status'], SUCCESS)
        self.assertEquals(ou['online_users'], [u])

        # Test that a user that was confirmed as online one minute ago (i.e
        # at least a minute) is now considered as offline.
        delta = datetime.timedelta(minutes=1)
        uad[u] = datetime.datetime.now() - delta
        self.assertEqual(s._isOnline(u), False)

        ou = s.getOnlineUsers()
        ou = json.loads(ou)
        self.assertEquals(ou['status'], SUCCESS)
        self.assertEquals(ou['online_users'], [])

        # Test 'getOnlineUsers' with multiple online users.
        s.confirmAsOnline(u)

        u = 'another'
        s.register(u, u)
        s.confirmAsOnline(u)

        ou = s.getOnlineUsers()
        ou = json.loads(ou)
        self.assertEquals(ou['status'], SUCCESS)
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
        self.assertEqual(json.loads(response)['status'], AUTH_FAIL)
        self.assertEqual(json.loads(s.getStatus(u))['userstatus'], 'online')

        response = s.setStatus(u, p, 'busy')
        self.assertEqual(json.loads(response)['status'], SUCCESS)
        self.assertEqual(json.loads(s.getStatus(u))['userstatus'], 'busy')

        response = s.setStatus(u, p, 'away')
        self.assertEqual(json.loads(response)['status'], SUCCESS)
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

        um = s.getMessages('recipient', 'secret', config.NULL_DATE)
        um = json.loads(um)
        self.assertEqual(um['status'], SUCCESS)
        self.assertEqual(um['messages'], {})

        # test authentication
        response = s.sendMessage('sender', 'wrongpass', 'recipient', 'This is the message')
        response = json.loads(response)
        self.assertEqual(response['status'], AUTH_FAIL)
        self.assertEqual(response['timestamp'], config.NULL_DATE)

        response = s.sendMessage('sender', 'secret', 'recipient', 'This is the message')
        response = json.loads(response)
        self.assertEqual(response['status'], SUCCESS)
        self.assertEqual(bool(RE.search(response['timestamp'])), True)
        message_timestamp = response['timestamp']

        # test authentication
        um = s.getMessages('recipient', 'wrongpass', config.NULL_DATE)
        um = json.loads(um)
        self.assertEqual(um['status'], AUTH_FAIL)
        self.assertEqual(um['messages'], {})

        um = s.getMessages('recipient', 'secret', config.NULL_DATE)
        um = json.loads(um)
        self.assertEqual(um['status'], SUCCESS)

        db = s.getMessages('recipient', 'secret', config.NULL_DATE)
        db = json.loads(db)
        self.assertEqual(um, db)
        # The returned datastructure looks as follows:
        # {
        #   'messages': {
        #       'sender': [ ['sender', '2011/10/04', '08:41', 'message', '2011-10-04T08:41:31.533527+00:00'] ]
        #     }, 
        #   'status': 0, 
        #   'timestamp': '2011-10-04T08:41:31.533527+00:00'
        # }
        self.assertEqual(um.keys(), ['status', 'timestamp', 'messages'])
        self.assertEqual(um['timestamp'], message_timestamp)

        msgdict = um['messages'] 
        # Test that messages from only one user was returned
        self.assertEqual(msgdict.keys(), ['sender'])
        # Test that only one message was received from this user
        self.assertEqual(len(msgdict['sender']), 1)
        # Test that the message tuple has 5 elements
        self.assertEqual(len(msgdict['sender'][0]), 5)
        # Test the message's timestamp
        self.assertEqual(bool(RE.search(msgdict['sender'][0][4])), True)
        self.assertEqual(msgdict['sender'][0][4], message_timestamp)
        # Test the senders username
        self.assertEqual(msgdict['sender'][0][0], 'sender')
        # Test that message date
        self.assertEqual(msgdict['sender'][0][1], 
                    datetime.datetime.now(utc).strftime("%Y/%m/%d"))
        # Test that message time
        self.assertEqual(msgdict['sender'][0][2], 
                    datetime.datetime.now(utc).strftime("%H:%M"))
        # Test that message text
        self.assertEqual(msgdict['sender'][0][3], 'This is the message')

        # Test getMessages with multiple senders. We didn't mark the
        # previous sender's messages as 'read', so they should be returned
        # again.
        s.register('sender2', 'secret')
        response = s.sendMessage('sender2', 'secret', 'recipient', 'another msg')
        response = json.loads(response)
        self.assertEqual(response['status'], SUCCESS)
        self.assertEqual(bool(RE.search(response['timestamp'])), True)
        message2_timestamp = response['timestamp']

        um = s.getMessages('recipient', 'secret', config.NULL_DATE)
        um = json.loads(um)
        self.assertEqual(um['status'], SUCCESS)
        self.assertEqual(um['timestamp'], message2_timestamp)

        msgdict = um['messages'] 
        # Test that messages from two users were returned
        self.assertEqual(len(msgdict.keys()), 2)
        # Test that only one message was received from each
        self.assertEqual(len(msgdict.values()[0]), 1)
        self.assertEqual(len(msgdict.values()[1]), 1)

        # Test the messages' timestamps
        self.assertEqual(bool(RE.search(msgdict['sender'][0][4])), True)
        self.assertEqual(msgdict['sender'][0][4], message_timestamp)
        self.assertEqual(msgdict['sender2'][0][4], message2_timestamp)

        # Test the properties of the message sent by senders
        self.assertEqual(len(msgdict['sender'][0]), 5)
        self.assertEqual(len(msgdict['sender2'][0]), 5)

        self.assertEqual(msgdict['sender2'][0][0], 'sender2')
        self.assertEqual(msgdict['sender2'][0][1], 
                    datetime.datetime.now(utc).strftime("%Y/%m/%d"))
        self.assertEqual(msgdict['sender2'][0][2], 
                    datetime.datetime.now(utc).strftime("%H:%M"))
        self.assertEqual(msgdict['sender2'][0][3], 'another msg')

        # Test for messages sent after message_timestamp. This should not
        # return messages.
        um = s.getMessages('recipient', 'secret', message2_timestamp)
        um = json.loads(um)
        self.assertEqual(um['status'], SUCCESS)
        self.assertEqual(um['messages'], {})
        self.assertEqual(um['timestamp'], message2_timestamp)


    def test_message_clearing(self):
        """ Test the 'sendMessage' and 'getUnclearedMessages' methods 
        """
        s = self.chatservice
        s.register('sender', 'secret')
        s.register('recipient', 'secret')

        um = s.getUnclearedMessages('recipient', 'secret', sender='sender')
        um = json.loads(um)
        self.assertEqual(um['messages'], {})

        response = s.sendMessage('sender', 'secret', 'recipient', 'message')
        response = json.loads(response)
        self.assertEqual(response['status'], SUCCESS)
        self.assertEqual(bool(RE.search(response['timestamp'])), True)
        message_timestamp = response['timestamp']

        # Test authentication
        um = s.getUnclearedMessages(
                            'recipient', 
                            'wrongpass', 
                            sender='sender', 
                            clear=False)
        um = json.loads(um)
        self.assertEqual(um['status'], AUTH_FAIL)
        self.assertEqual(um['messages'], {})
        self.assertEqual(um['timestamp'], config.NULL_DATE)

        um = s.getUnclearedMessages(
                            'recipient', 
                            'secret', 
                            sender='sender', 
                            clear=False)
        um = json.loads(um)
        self.assertEqual(um['status'], SUCCESS)
        self.assertEqual(um.keys(), ['status', 'timestamp', 'messages'])
        self.assertEqual(um['timestamp'], message_timestamp)

        # The uncleared messages datastructure looks as follows:
        # {
        #     'status': 0,
        #     'timestamp': '2011-09-30T12:43:49+00:00'
        #     'messages': {
        #             'sender': [ ['sender', '2011/09/30', '12:43', 'first message', '2011-09-30T12:43:49+00:00'] ]
        #           },
        # }

        # Check that there is a ISO8601 timestamp.
        self.assertEqual(bool(RE.search(um['timestamp'])), True)

        msgs = um['messages'] 
        # Test that messages from only one user was returned
        self.assertEqual(len(msgs), 1)
        # Test that only one message was received from this user
        self.assertEqual(len(msgs.values()[0]), 1)
        # Test that the message tuple has 5 elements
        self.assertEqual(len(msgs.values()[0][0]), 5)
        # Test the message's timestamp
        self.assertEqual(bool(RE.search(msgs.values()[0][0][4])), True)
        self.assertEqual(msgs.values()[0][0][4], message_timestamp)
        # Test that senders username
        self.assertEqual(msgs.values()[0][0][0], 'sender')
        # Test that message date
        self.assertEqual(msgs.values()[0][0][1], 
                    datetime.datetime.now(utc).strftime("%Y/%m/%d"))
        # Test that message time
        self.assertEqual(msgs.values()[0][0][2], 
                    datetime.datetime.now(utc).strftime("%H:%M"))
        # Test that message text
        self.assertEqual(msgs.values()[0][0][3], 'message')


        # Test getUnclearedMessages with multiple senders. We didn't mark the
        # previous sender's messages as 'clear', so they should be returned
        # again.
        s.register('sender2', 'secret')
        response = s.sendMessage('sender2', 'secret', 'recipient', 'another msg')
        response = json.loads(response)
        self.assertEqual(response['status'], SUCCESS)
        self.assertEqual(bool(RE.search(response['timestamp'])), True)
        message2_timestamp = response['timestamp']

        um = s.getUnclearedMessages('recipient', 'secret', clear=True)
        um = json.loads(um)
        self.assertEqual(um['status'], SUCCESS)
        # Test that messages from two users were returned
        msgs = um['messages'] 
        self.assertEqual(len(msgs), 2)
        # Test that only one message was received from each
        self.assertEqual(len(msgs.values()[0]), 1)
        self.assertEqual(len(msgs.values()[1]), 1)

        # Test the messages' timestamps
        self.assertEqual(msgs['sender'][0][4], message_timestamp)
        self.assertEqual(msgs['sender2'][0][4], message2_timestamp)

        # Test the properties of the message sent by sender1
        self.assertEqual(len(msgs.values()[1][0]), 5)
        self.assertEqual(msgs['sender2'][0][0], 'sender2')
        self.assertEqual(msgs['sender2'][0][1], 
                    datetime.datetime.now(utc).strftime("%Y/%m/%d"))
        self.assertEqual(msgs['sender2'][0][2], 
                    datetime.datetime.now(utc).strftime("%H:%M"))
        self.assertEqual(msgs['sender2'][0][3], 'another msg')
        self.assertEqual(bool(RE.search(msgs['sender2'][0][4])), True)

        # Check that the global timestamp is the same as the last message's
        self.assertEqual(um['timestamp'], msgs['sender2'][0][4])

        # All the uncleared messages for 'recipient' has now been marked as clear,
        # lets test that no new messages are returned
        um = s.getUnclearedMessages('recipient', 'secret')
        um = json.loads(um)
        self.assertEqual(um['status'], SUCCESS)
        self.assertEqual(um['messages'], {})
        self.assertEqual(um['timestamp'], config.NULL_DATE)


    def testMessageFetching(self):
        """ Test the getMessages method 
        """
        s = self.chatservice
        s.register('sender', 'secret')
        s.register('recipient', 'secret')

        um = s.getMessages('recipient', 'secret')
        um = json.loads(um)
        self.assertEqual(um['messages'], {})

        before_first_msg = datetime.datetime.now(utc).isoformat()

        response = s.sendMessage('sender', 'secret', 'recipient', 'first message')
        response = json.loads(response)
        self.assertEqual(response['status'], SUCCESS)

        # Test authentication
        um = s.getMessages('recipient', 'wrongpass')
        um = json.loads(um)
        self.assertEqual(um['status'], AUTH_FAIL)
        self.assertEqual(um['messages'], {})

        um = s.getMessages('recipient', 'secret')
        um = json.loads(um)
        self.assertEqual(um['status'], SUCCESS)
        # The uncleared messages datastructure looks as follows:
        # {
        #     'status': 0,
        #     'timestamp': '2011-09-30T12:43:49+00:00'
        #     'messages': {
        #             'sender': [ ['sender', '2011/09/30', '12:43', 'first message', '2011-09-30T12:43:49+00:00'] ]
        #           },
        # }

        # Check that there is a timestamp.
        self.assertEqual(bool(RE.search(um['timestamp'])), True)
        self.assertEqual(um['timestamp'] > before_first_msg, True)

        msgs = um['messages'] 
        # Test that messages from only one user was returned
        self.assertEqual(len(msgs), 1)
        # Test that only one message was received from this user
        self.assertEqual(len(msgs.values()[0]), 1)
        # Test that the message tuple has 5 elements
        self.assertEqual(len(msgs.values()[0][0]), 5)
        # Test that senders username
        self.assertEqual(msgs.values()[0][0][0], 'sender')
        # Test that message date
        self.assertEqual(msgs.values()[0][0][1], 
                    datetime.datetime.now(utc).strftime("%Y/%m/%d"))
        # Test that message time
        self.assertEqual(msgs.values()[0][0][2], 
                    datetime.datetime.now(utc).strftime("%H:%M"))
        # Test that message text
        self.assertEqual(msgs.values()[0][0][3], 'first message')


        # Test getMessages with multiple senders. 
        before_second_msg = datetime.datetime.now(utc).isoformat()
        s.register('sender2', 'secret')
        response = s.sendMessage('sender2', 'secret', 'recipient', 'second message')
        response = json.loads(response)
        self.assertEqual(response['status'], SUCCESS)

        after_second_msg = datetime.datetime.now(utc).isoformat()

        um = s.getMessages('recipient', 'secret', since=before_first_msg)
        um = json.loads(um)
        self.assertEqual(um['status'], SUCCESS)
        # Test that messages from two users were returned
        msgs = um['messages'] 
        self.assertEqual(len(msgs), 2)
        # Test that only one message was received from each
        self.assertEqual(len(msgs.values()[0]), 1)
        self.assertEqual(len(msgs.values()[1]), 1)

        # Test the properties of the message sent by sender1
        self.assertEqual(len(msgs.values()[1][0]), 5)
        self.assertEqual(msgs['sender2'][0][0], 'sender2')
        self.assertEqual(msgs['sender2'][0][1], 
                    datetime.datetime.now(utc).strftime("%Y/%m/%d"))
        self.assertEqual(msgs['sender2'][0][2], 
                    datetime.datetime.now(utc).strftime("%H:%M"))
        self.assertEqual(msgs['sender2'][0][3], 'second message')
        self.assertEqual(bool(RE.search(msgs['sender2'][0][4])), True)

        # Check that the global timestamp is the same as the last message's
        self.assertEqual(um['timestamp'], msgs['sender2'][0][4])

        # Now we make that date later than the first message, so we should only
        # receive the second one.
        um = s.getMessages('recipient', 'secret', since=before_second_msg)
        um = json.loads(um)

        self.assertEqual(um['status'], SUCCESS)
        msgs = um['messages'] 
        self.assertEqual(len(msgs), 1)
        self.assertEqual(msgs.values()[0][0][0], 'sender2')
        self.assertEqual(msgs.values()[0][0][1], 
                    datetime.datetime.now(utc).strftime("%Y/%m/%d"))
        self.assertEqual(msgs.values()[0][0][2], 
                    datetime.datetime.now(utc).strftime("%H:%M"))
        self.assertEqual(msgs.values()[0][0][3], 'second message')
        self.assertEqual(bool(RE.search(msgs['sender2'][0][4])), True)

        # Check that there is a ISO8601 timestamp.
        self.assertEqual(bool(RE.search(um['timestamp'])), True)
        self.assertEqual(um['timestamp'] > before_second_msg, True)
        self.assertEqual(um['timestamp'] < after_second_msg, True)
        # Check that the global timestamp is the same as the last (and only) message's
        self.assertEqual(um['timestamp'], msgs['sender2'][0][4])



def test_suite():
    from unittest import TestSuite, makeSuite
    suite = TestSuite()
    suite.addTest(makeSuite(TestChatService))
    return suite
