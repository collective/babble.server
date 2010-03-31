import datetime
import simplejson as json

from Testing import ZopeTestCase as ztc
from ZPublisher import NotFound
from persistent.dict import PersistentDict

from Products.TemporaryFolder.TemporaryFolder import SimpleTemporaryContainer
from Products.Five import zcml
from babble.server.config import SUCCESS
from babble.server.config import AUTH_FAIL

import Products.Five
ztc.installProduct('Five')
zcml.load_config('configure.zcml', package=Products.Five)

import babble.server
ztc.installProduct('babble.server')
zcml.load_config('configure.zcml', package=babble.server)

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
        uad = s._getUserAccessDict()
        self.assertEqual(uad, PersistentDict())

        # Returned dict should now be from cache...
        uad = s._getUserAccessDict()
        self.assertEqual(uad, getattr(s, '_v_user_access_dict'))

        # Test that the 'user access dict' is recreated if it is deleted (which
        # is plausible since it's in a temp folder)
        s.temp_folder._getOb('user_access_dict')
        uad = s._getUserAccessDict()
        self.assertEqual(uad, PersistentDict())

        # Test the NotFound is raised when the 'temp_folder' is not there
        self.app._delOb('temp_folder')
        # Invalidate the cache
        delattr(s, '_v_user_access_dict')
        self.assertRaises(NotFound, s._getUserAccessDict)


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
        """ Test the 'sendMessage' and 'getUnreadMessages' methods """
        s = self.chatservice
        s.register('sender', 'secret')
        s.register('recipient', 'secret')

        um = s.getUnreadMessages('recipient', 'secret', read=True)
        um = json.loads(um)
        self.assertEqual(um['status'], SUCCESS)
        self.assertEqual(um['messages'], {})

        # test authentication
        response = s.sendMessage('sender', 'wrongpass', 'recipient', 'message')
        response = json.loads(response)
        self.assertEqual(response['status'], AUTH_FAIL)

        response = s.sendMessage('sender', 'secret', 'recipient', 'message')
        response = json.loads(response)
        self.assertEqual(response['status'], SUCCESS)

        # test authentication
        um = s.getUnreadMessages('recipient', 'wrongpass', read=False)
        um = json.loads(um)
        self.assertEqual(um['status'], AUTH_FAIL)
        self.assertEqual(um['messages'], {})

        um = s.getUnreadMessages('recipient', 'secret', read=False)
        um = json.loads(um)
        self.assertEqual(um['status'], SUCCESS)

        db = s.getUnreadMessages('recipient', 'secret', read=False)
        db = json.loads(db)
        self.assertEqual(um, db)
        # The unread messages datastructure looks as follows:
        # [
        #   {
        #    'messages': (('username', '2010/03/08', '15:25', 'message'),), 
        #    'user': 'username'
        #    }
        # ]
        msgdict = um['messages'] 
        # Test that messages from only one user was returned
        self.assertEqual(msgdict.keys(), ['sender'])
        # Test that only one message was received from this user
        self.assertEqual(len(msgdict['sender']), 1)
        # Test that the message tuple has 4 elements
        self.assertEqual(len(msgdict['sender'][0]), 4)
        # Test the senders username
        self.assertEqual(msgdict['sender'][0][0], 'sender')
        # Test that message date
        self.assertEqual(msgdict['sender'][0][1], 
                    datetime.datetime.now().strftime("%Y/%m/%d"))
        # Test that message time
        self.assertEqual(msgdict['sender'][0][2], 
                    datetime.datetime.now().strftime("%H:%M"))
        # Test that message text
        self.assertEqual(msgdict['sender'][0][3], 'message')


        # Test getUnreadMessages with multiple senders. We didn't mark the
        # previous sender's messages as 'read', so they should be returned
        # again.
        s.register('sender2', 'secret')
        response = s.sendMessage('sender2', 'secret', 'recipient', 'another msg')
        response = json.loads(response)
        self.assertEqual(response['status'], SUCCESS)

        um = s.getUnreadMessages('recipient', 'secret', read=True)
        um = json.loads(um)

        status = um['status']
        self.assertEqual(status, SUCCESS)

        msgdict = um['messages'] 
        # Test that messages from two users were returned
        self.assertEqual(len(msgdict.keys()), 2)
        # Test that only one message was received from each
        self.assertEqual(len(msgdict.values()[0]), 1)
        self.assertEqual(len(msgdict.values()[1]), 1)

        # Test the properties of the message sent by senders
        self.assertEqual(len(msgdict['sender'][0]), 4)
        self.assertEqual(len(msgdict['sender2'][0]), 4)

        self.assertEqual(msgdict['sender2'][0][0], 'sender2')
        self.assertEqual(msgdict['sender2'][0][1], 
                    datetime.datetime.now().strftime("%Y/%m/%d"))
        self.assertEqual(msgdict['sender2'][0][2], 
                    datetime.datetime.now().strftime("%H:%M"))
        self.assertEqual(msgdict['sender2'][0][3], 'another msg')

        # All the unread messages for 'recipient' has now been marked as read,
        # lets test that no new messages are returned
        um = s.getUnreadMessages('recipient', 'secret')
        um = json.loads(um)
        self.assertEqual(um['status'], SUCCESS)
        self.assertEqual(um['messages'], {})


    def test_message_clearing(self):
        """ Test the 'sendMessage' and 'getUnclearedMessages' methods """
        s = self.chatservice
        s.register('sender', 'secret')
        s.register('recipient', 'secret')

        um = s.getUnclearedMessages('recipient', 'secret', sender='sender')
        um = json.loads(um)
        self.assertEqual(um['messages'], {})

        response = s.sendMessage('sender', 'secret', 'recipient', 'message')
        response = json.loads(response)
        self.assertEqual(response['status'], SUCCESS)

        # Test authentication
        um = s.getUnclearedMessages(
                            'recipient', 
                            'wrongpass', 
                            sender='sender', 
                            clear=False)
        um = json.loads(um)
        self.assertEqual(um['status'], AUTH_FAIL)
        self.assertEqual(um['messages'], {})

        um = s.getUnclearedMessages(
                            'recipient', 
                            'secret', 
                            sender='sender', 
                            clear=False)
        um = json.loads(um)
        self.assertEqual(um['status'], SUCCESS)
        # The uncleared messages datastructure looks as follows:
        # [
        #   {
        #    'messages': (('username', '2010/03/08', '15:25', 'message'),), 
        #    'user': 'username'
        #    }
        # ]
        #
        msgs = um['messages'] 
        # Test that messages from only one user was returned
        self.assertEqual(len(msgs), 1)
        # Test that only one message was received from this user
        self.assertEqual(len(msgs.values()[0]), 1)
        # Test that the message tuple has 4 elements
        self.assertEqual(len(msgs.values()[0][0]), 4)
        # Test that senders username
        self.assertEqual(msgs.values()[0][0][0], 'sender')
        # Test that message date
        self.assertEqual(msgs.values()[0][0][1], 
                    datetime.datetime.now().strftime("%Y/%m/%d"))
        # Test that message time
        self.assertEqual(msgs.values()[0][0][2], 
                    datetime.datetime.now().strftime("%H:%M"))
        # Test that message text
        self.assertEqual(msgs.values()[0][0][3], 'message')


        # Test getUnclearedMessages with multiple senders. We didn't mark the
        # previous sender's messages as 'clear', so they should be returned
        # again.
        s.register('sender2', 'secret')
        response = s.sendMessage('sender2', 'secret', 'recipient', 'another msg')
        response = json.loads(response)
        self.assertEqual(response['status'], SUCCESS)

        um = s.getUnclearedMessages('recipient', 'secret', clear=True)
        um = json.loads(um)
        self.assertEqual(um['status'], SUCCESS)
        # Test that messages from two users were returned
        msgs = um['messages'] 
        self.assertEqual(len(msgs), 2)
        # Test that only one message was received from each
        self.assertEqual(len(msgs.values()[0]), 1)
        self.assertEqual(len(msgs.values()[1]), 1)

        # Test the properties of the message sent by sender1
        self.assertEqual(len(msgs.values()[1][0]), 4)
        self.assertEqual(msgs['sender2'][0][0], 'sender2')
        self.assertEqual(msgs['sender2'][0][1], 
                    datetime.datetime.now().strftime("%Y/%m/%d"))
        self.assertEqual(msgs['sender2'][0][2], 
                    datetime.datetime.now().strftime("%H:%M"))
        self.assertEqual(msgs['sender2'][0][3], 'another msg')

        # All the uncleared messages for 'recipient' has now been marked as clear,
        # lets test that no new messages are returned
        um = s.getUnclearedMessages('recipient', 'secret')
        um = json.loads(um)
        self.assertEqual(um['status'], SUCCESS)
        self.assertEqual(um['messages'], {})


def test_suite():
    from unittest import TestSuite, makeSuite
    suite = TestSuite()
    suite.addTest(makeSuite(TestChatService))
    return suite
