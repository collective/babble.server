import logging
from zope.interface import implements
from Products.BTreeFolder2.BTreeFolder2 import BTreeFolder2

from messagebox import MessageBox
from interfaces import IUser

log = logging.getLogger('babble.server/user.py')

class User(BTreeFolder2):
    """ A user on the message server """

    implements(IUser)

    _online = False
    _contacts = ()
    _contact_requests = ()
    _pending_contacts = ()
    _status = 'Away'

    def signIn(self):
        """ sign in """
        self._online = True

    def signOut(self):
        """ sign out """
        self._online = False

    def isOnline(self):
        """ is user online """
        return self._online

    def setStatus(self, status):
        """ set user's status """
        self._status = status

    def getStatus(self):
        """ get user's status """
        return self._status

    def addMessage(self, recipient, message):
        mbox = self._getMessageBox(recipient)
        mbox.addMessage(message)

    def getAllMessages(self):
        """ Get all new messages, mark them as read.
        """
        messages = []
        for mbox in self.objectValues():
            mbox_messages = []
            for m in mbox.objectValues():
                if m.unread():
                    mbox_messages.append((m.time.Date(), m.time.TimeMinutes(), m.text))
                    m.markAsRead()

            if mbox_messages:
                messages.append({'user':mbox.id, 'messages':tuple(mbox_messages)})
        return messages

    def getMessagesFromSender(self, sender, read=True):
        mbox = self._getMessageBox(sender)
        messages = []
        m_ids = mbox.objectIds()
        if not m_ids:
            return ()

        for m in mbox.objectValues():
            if m.unread():
                messages.append((m.time.ISO8601(), m.text))
                if read is True:
                    m.markAsRead()

        return tuple(messages)

    def getNumMessagesFromSender(self, sender):
        mbox = self._getMessageBox(sender)
        return len([m for m in mbox.objectValues() if m.unread()])

    def requestContact(self, contact):
        if contact in self._contacts:
            raise "Cannot request contact with existing contact %s" % contact

        if contact not in self._contact_requests:
            self._contact_requests = self._contact_requests + (contact,)

    def addPendingContact(self, contact):
        if contact not in self._pending_contacts:
            self._pending_contacts = self._pending_contacts + (contact,)

    def approveContactRequest(self, contact):
        if contact in self._pending_contacts:
            clist = list(self._pending_contacts)
            clist.remove(contact)
            self._pending_contacts = tuple(clist)

        if contact in self._contact_requests:
            clist = list(self._contact_requests)
            clist.remove(contact)
            self._contact_requests = tuple(clist)

        if contact not in self._contacts:
            self._contacts = self._contacts + (contact,)

    def declineContactRequest(self, contact):
        if contact in self._contact_requests:
            clist = list(self._contact_requests)
            clist.remove(contact)
            self._contact_requests = tuple(clist)

        if contact in self._pending_contacts:
            clist = list(self._pending_contacts)
            clist.remove(contact)
            self._pending_contacts = tuple(clist)

    def removeContact(self, contact):
        if contact in self._contacts:
            clist = list(self._contacts)
            clist.remove(contact)
            self._contacts = tuple(clist)

    def getPendingContacts(self):
        return self._pending_contacts

    def getContactRequests(self):
        return self._contact_requests

    def getContacts(self):
        return self._contacts

    def getContactStatusList(self):
        contact_status_list = []

        for contact_list, status  in [
                (self._pending_contacts, 'pending'),
                (self._contact_requests, 'requesting'),
                (self._contacts, 'approved'),
                ]:

            for name in contact_list:
                user = self._getUser(name)
                if status == 'approved':
                    status = user.getStatus()
                num_msgs = self.getNumMessagesFromSender(name)
                contact_status_list.append((name, status, num_msgs))

        return contact_status_list

    def _getMessageBox(self, recipient):
        if recipient not in self.objectIds():
            self._setObject(recipient, MessageBox(recipient))
        return self._getOb(recipient)

    def _getUser(self, username):
        return self.aq_parent._getOb(username)

