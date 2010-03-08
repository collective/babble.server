import datetime
from zope import component

from Testing import ZopeTestCase as ztc
from ZPublisher import NotFound
from persistent.dict import PersistentDict

from Products.TemporaryFolder.TemporaryFolder import SimpleTemporaryContainer
from Products.Five import zcml

import Products.Five
ztc.installProduct('Five')
zcml.load_config('configure.zcml', package=Products.Five)

import babble.server
ztc.installProduct('babble.server')
zcml.load_config('configure.zcml', package=babble.server)

class TestChatService(ztc.ZopeTestCase):

    def afterSetUp(self):
        """ Adds a babble.server to the default fixture """
        # Create the admin user.
        self.setRoles(('Manager',))

        adding = self.app.restrictedTraverse('+')
        view = component.getMultiAdapter(
                                    (adding, self.app.REQUEST),
                                    name=u'addChatService.html',
                                    )

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
        s.register('username', 'password')
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

        # Test that the 'user access dict' is recreated if it is deleted (which
        # is plausible since it's in a temp folder)
        s.temp_folder._getOb('user_access_dict')
        uad = s._getUserAccessDict()
        self.assertEqual(uad, PersistentDict())

        # Test the NotFound is raised when the 'temp_folder' is not there
        self.app._delOb('temp_folder')
        self.assertRaises(NotFound, s._getUserAccessDict)


    def test_registration(self):
        """ Test the 'register', 'isRegistered', 'authenticate' and
            'setUserPassword'  methods.
        """
        s = self.chatservice
        s.register('username', 'password')
        self.assertEqual('username', s._getUser('username').id)

        r = s.isRegistered('username')
        self.assertEqual(r, True)

        auth = s.authenticate('username', 'password')
        self.assertEqual(auth != None, True)
        self.assertEqual(auth.name, 'username')

        r = s.isRegistered('nobody')
        self.assertEqual(r, False)

        auth = s.authenticate('nobody', 'password')
        self.assertEqual(auth, None)

        s.setUserPassword('username', 'new_password')
        auth = s.authenticate('username', 'password')
        self.assertEqual(auth, None)

        auth = s.authenticate('username', 'new_password')
        self.assertEqual(auth != None, True)
        self.assertEqual(auth.name, 'username')


    def test_online(self):
        """ Test the '_confirmAsOnline', 'isOnline' and 'getOnlineUsers' methods """
        s = self.chatservice
        u = 'username'
        s.register(u, u)
        self.assertEqual(s.isOnline(u), False)

        # Test that a user entry was made into the 'user access dict'
        s._confirmAsOnline(u)
        uad = s._getUserAccessDict()
        self.assertEqual(uad.get(u, None) != None, True)

        self.assertEqual(s.isOnline(u), True)

        now = datetime.datetime.now()
        
        # Test that a user that was confirmed as online 59 seconds ago (i.e
        # less than a minute) is still considered as online.
        delta = datetime.timedelta(seconds=59)
        uad[u] = datetime.datetime.now() - delta
        self.assertEqual(s.isOnline(u), True)

        ou = s.getOnlineUsers()
        self.assertEquals(ou, [u])

        # Test that a user that was confirmed as online one minute ago (i.e
        # at least a minute) is now considered as offline.
        delta = datetime.timedelta(minutes=1)
        uad[u] = datetime.datetime.now() - delta
        self.assertEqual(s.isOnline(u), False)

        ou = s.getOnlineUsers()
        self.assertEquals(ou, [])

        # Test 'getOnlineUsers' with multiple online users.
        s._confirmAsOnline(u)

        u = 'another'
        s.register(u, u)
        s._confirmAsOnline(u)

        ou = s.getOnlineUsers()
        self.assertEquals(ou, ['username', 'another'])


    def test_status(self):
        """ Test the 'setStatus' and 'getStatus' methods
        """
        s = self.chatservice
        u = 'username'
        s.register(u, u)

        self.assertEqual(s.getStatus(u), 'offline')

        s._confirmAsOnline(u)
        self.assertEqual(s.getStatus(u), 'online')

        s.setStatus(u, 'busy')
        self.assertEqual(s.getStatus(u), 'busy')

        s.setStatus(u, 'away')
        self.assertEqual(s.getStatus(u), 'away')

        # Simulate one minute of time passing and then test the that user's
        # status is 'offline'
        delta = datetime.timedelta(minutes=1)
        uad = s._getUserAccessDict()
        uad[u] = datetime.datetime.now() - delta
        self.assertEqual(s.getStatus(u), 'offline')


    def test_messaging(self):
        """ Test the 'sendMessage' and 'getUnreadMessages' methods """
        s = self.chatservice
        s.register('sender', 'sender')
        s.register('recipient', 'passwd')

        um = s.getUnreadMessages(
                                'recipient',
                                sender='sender',
                                read=True,
                                confirm_online=True,
                                )
        self.assertEqual(um, [])
        s.sendMessage('sender', 'recipient', 'message')

        um = s.getUnreadMessages(
                                'recipient',
                                sender='sender',
                                read=False,
                                confirm_online=True,
                                )
        # The unread messages datastructure looks as follows:
        # [
        #   {
        #    'messages': (('username', '2010/03/08', '15:25', 'message'),), 
        #    'user': 'username'
        #    }
        # ]
        #
        # Test that messages from only one user was returned
        self.assertEqual(len(um), 1)
        # Test that only one message was received from this user
        self.assertEqual(len(um[0]['messages']), 1)
        # Test that the message tuple has 4 elements
        self.assertEqual(len(um[0]['messages'][0]), 4)
        # Test that senders username
        self.assertEqual(um[0]['messages'][0][0], 'sender')
        # Test that message date
        self.assertEqual(um[0]['messages'][0][1], 
                    datetime.datetime.now().strftime("%Y/%m/%d"))
        # Test that message time
        self.assertEqual(um[0]['messages'][0][2], 
                    datetime.datetime.now().strftime("%H:%M"))
        # Test that message text
        self.assertEqual(um[0]['messages'][0][3], 'message')


        # Test getUnreadMessages with multiple senders. We didn't mark the
        # previous sender's messages as 'read', so they should be returned
        # again.
        s.register('sender2', 'sender2')
        s.sendMessage('sender2', 'recipient', 'another message')
        um = s.getUnreadMessages(
                                'recipient',
                                read=True,
                                confirm_online=True,
                                )
        # Test that messages from two users were returned
        self.assertEqual(len(um), 2)
        # Test that only one message was received from each
        self.assertEqual(len(um[0]['messages']), 1)
        self.assertEqual(len(um[1]['messages']), 1)

        # Test the properties of the message sent by sender1
        self.assertEqual(len(um[1]['messages'][0]), 4)
        self.assertEqual(um[1]['messages'][0][0], 'sender2')
        self.assertEqual(um[1]['messages'][0][1], 
                    datetime.datetime.now().strftime("%Y/%m/%d"))
        self.assertEqual(um[1]['messages'][0][2], 
                    datetime.datetime.now().strftime("%H:%M"))
        self.assertEqual(um[1]['messages'][0][3], 'another message')

        # All the unread messages for 'recipient' has now been marked as read,
        # lets test that no new messages are returned
        um = s.getUnreadMessages('recipient')
        self.assertEqual(um, [])


    def test_message_clearing(self):
        """ Test the 'sendMessage' and 'getUnclearedMessages' methods """
        s = self.chatservice
        s.register('sender', 'sender')
        s.register('recipient', 'passwd')

        um = s.getUnclearedMessages('recipient', sender='sender')
        self.assertEqual(um, [])
        s.sendMessage('sender', 'recipient', 'message')

        um = s.getUnclearedMessages(
                                'recipient',
                                sender='sender',
                                clear=False,
                                confirm_online=True,)
        # The uncleared messages datastructure looks as follows:
        # [
        #   {
        #    'messages': (('username', '2010/03/08', '15:25', 'message'),), 
        #    'user': 'username'
        #    }
        # ]
        #
        # Test that messages from only one user was returned
        self.assertEqual(len(um), 1)
        # Test that only one message was received from this user
        self.assertEqual(len(um[0]['messages']), 1)
        # Test that the message tuple has 4 elements
        self.assertEqual(len(um[0]['messages'][0]), 4)
        # Test that senders username
        self.assertEqual(um[0]['messages'][0][0], 'sender')
        # Test that message date
        self.assertEqual(um[0]['messages'][0][1], 
                    datetime.datetime.now().strftime("%Y/%m/%d"))
        # Test that message time
        self.assertEqual(um[0]['messages'][0][2], 
                    datetime.datetime.now().strftime("%H:%M"))
        # Test that message text
        self.assertEqual(um[0]['messages'][0][3], 'message')


        # Test getUnclearedMessages with multiple senders. We didn't mark the
        # previous sender's messages as 'clear', so they should be returned
        # again.
        s.register('sender2', 'sender2')
        s.sendMessage('sender2', 'recipient', 'another message')
        um = s.getUnclearedMessages(
                                'recipient',
                                clear=True,
                                confirm_online=True,
                                )
        # Test that messages from two users were returned
        self.assertEqual(len(um), 2)
        # Test that only one message was received from each
        self.assertEqual(len(um[0]['messages']), 1)
        self.assertEqual(len(um[1]['messages']), 1)

        # Test the properties of the message sent by sender1
        self.assertEqual(len(um[1]['messages'][0]), 4)
        self.assertEqual(um[1]['messages'][0][0], 'sender2')
        self.assertEqual(um[1]['messages'][0][1], 
                    datetime.datetime.now().strftime("%Y/%m/%d"))
        self.assertEqual(um[1]['messages'][0][2], 
                    datetime.datetime.now().strftime("%H:%M"))
        self.assertEqual(um[1]['messages'][0][3], 'another message')

        # All the uncleared messages for 'recipient' has now been marked as clear,
        # lets test that no new messages are returned
        um = s.getUnclearedMessages('recipient')
        self.assertEqual(um, [])


def test_suite():
    from unittest import TestSuite, makeSuite
    suite = TestSuite()
    suite.addTest(makeSuite(TestChatService))
    return suite
