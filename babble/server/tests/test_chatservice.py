import os, sys

if __name__ == '__main__':
    execfile(os.path.join(sys.path[0], 'framework.py'))

from Testing import ZopeTestCase
import babble.server
from Products.Five import zcml
from babble.server.service import ChatService

ZopeTestCase.installProduct('Five')
ZopeTestCase.installProduct('babble.server')

zcml.load_config('configure.zcml', package=babble.server)

class TestChatService(ZopeTestCase.ZopeTestCase):

    def afterSetUp(self):
        '''Adds a babble.server to the default fixture'''
        self.chatservice = ChatService('chatservice')
        self.chatservice.manage_addUserFolder()
        self.chatservice.title = 'Chat Service'

    def test_register(self):
        s = self.chatservice
        u = 'username'
        s.register(u, u)
        self.assertEqual(u, s._getUser(u).id)

    def test_setUserProperty(self):
        s = self.chatservice
        u = 'username'
        s.register(u, u)
        s.manage_addProperty('name', '', 'string')
        self.assertEqual(s.setUserProperty(u, 'name', 'pete'), None)

    def test_getUserProperty(self):
        s = self.chatservice
        u = 'username'
        self.test_setUserProperty()
        self.assertEqual(s.getUserProperty(u, 'name'), 'pete')

    def test_findUser(self):
        s = self.chatservice
        u = 'username'
        self.test_setUserProperty()
        self.assertEqual(s.findUser('name', 'pete'), ['username'])

    def test_signIn(self):
        s = self.chatservice
        u = 'username'
        s.register(u, u)
        self.assertEqual(s.signIn(u), None)

    def test_signOut(self):
        s = self.chatservice
        u = 'username'
        s.register(u, u)
        self.assertEqual(s.signOut(u), None)

    def test_isOnline(self):
        """ check if user is online """
        s = self.chatservice
        u = 'username'
        s.register(u, u)
        s.signIn(u)
        self.assertEqual(s.isOnline(u), True)
        s.signOut(u)
        self.assertEqual(s.isOnline(u), False)

    def test_requestContact(self):
        """ make contact request """
        s = self.chatservice
        s.register('chatterbox', 'passwd')
        s.register('buddy', 'passwd')
        s.requestContact('chatterbox', 'buddy')
        self.assertEqual(s.getContactRequests('chatterbox'), ('buddy',))
        self.assertEqual(s.getPendingContacts('buddy'), ('chatterbox',))

    def test_approveContactRequest(self):
        """ make contact request """
        s = self.chatservice
        s.register('chatterbox', 'passwd')
        s.register('buddy', 'passwd')
        s.requestContact('chatterbox', 'buddy')
        s.approveContactRequest('buddy', 'chatterbox')
        self.assertEqual(s.getContactRequests('chatterbox'), ())
        self.assertEqual(s.getPendingContacts('buddy'), ())
        self.assertEqual(s.getContacts('buddy'), ('chatterbox',))
        self.assertEqual(s.getContacts('chatterbox'), ('buddy',))

    def test_declineContactRequest(self):
        """ make contact request """
        s = self.chatservice
        s.register('chatterbox', 'passwd')
        s.register('buddy', 'passwd')
        s.requestContact('chatterbox', 'buddy')
        s.declineContactRequest('buddy', 'chatterbox')
        self.assertEqual(s.getContactRequests('chatterbox'), ())
        self.assertEqual(s.getPendingContacts('buddy'), ())
        self.assertEqual(s.getContacts('buddy'), ())
        self.assertEqual(s.getContacts('chatterbox'), ())

    def test_sendMessage(self):
        """ send a message to a user """
        s = self.chatservice
        u = 'username'
        s.register(u, u)
        s.register('recipient', 'passwd')
        self.assertEqual(s.sendMessage(u, 'recipient', 'message'), None)

    def test_getMessagesForUser(self):
        """ get all the messages for a user from a given sender"""
        s = self.chatservice
        u = 'username'
        s.register(u, u)
        s.register('recipient', 'passwd')
        self.assertEqual(s.getMessagesForUser(u, 'recipient'), ())
        s.sendMessage(u, 'recipient', 'message')
        self.assertEqual(s.getMessagesForUser(u, 'recipient'), ())

    def test_getContactStatusList(self):
        """ test contact status list """
        s = self.chatservice
        s.register('chatterbox', 'passwd')
        s.register('buddy', 'passwd')
        s.requestContact('chatterbox', 'buddy')
        self.assertEqual(s.getContactStatusList('chatterbox'),
            [('buddy', 'requesting', 0)])
        self.assertEqual(s.getContactStatusList('buddy'),
            [('chatterbox', 'pending', 0)])
        s.approveContactRequest('buddy', 'chatterbox')
        self.assertEqual(s.getContactStatusList('buddy'),
            [('chatterbox', 'offline', 0)])
        self.assertEqual(s.getContactStatusList('chatterbox'),
            [('buddy', 'offline', 0)])
        s.sendMessage('chatterbox', 'buddy', 'hallo')
        self.assertEqual(s.getContactStatusList('chatterbox'),
            [('buddy', 'offline', 0)])
        self.assertEqual(s.getContactStatusList('buddy'),
            [('chatterbox', 'offline', 1)])

def test_suite():
    from unittest import TestSuite, makeSuite
    suite = TestSuite()
    suite.addTest(makeSuite(TestChatService))
    return suite

if __name__ == '__main__':
    framework()
