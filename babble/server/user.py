import logging
from zope.interface import implements
from Products.BTreeFolder2.BTreeFolder2 import BTreeFolder2

from messagebox import MessageBox
from interfaces import IUser

log = logging.getLogger('babble.server/user.py')

class User(BTreeFolder2):
    """ A user on the message server """

    implements(IUser)

    _contacts = ()
    _contact_requests = ()
    _pending_contacts = ()
    _status = 'Away'

    def setStatus(self, status):
        """ set user's status """
        self._status = status

    def getStatus(self):
        """ get user's status """
        return self._status

    def addMessage(self, contact, message, author, read=False):
        """ Add a message to this user's contact's messagebox
            
            The message author could be either the user or the
            contact, and is therefore passed as a separate var.
        """
        mbox = self._getMessageBox(contact)
        mbox.addMessage(message, author, read)

    def getUnreadMessages(self, sender=None, read=True):
        """ Return uncleared messages in list of dicts with senders as keys. 
            If read=True, then mark them as read.
            If a sender is specified, then return only the messages from that
            sender. 
        """
        if sender:
            mboxes = [self._getMessageBox(sender)]
        else:
            mboxes = self.objectValues()

        messages = []
        for mbox in mboxes:
            mbox_messages = []
            for m in mbox.objectValues():
                if m.unread():
                    mbox_messages.append((m.author, m.time.Date(), m.time.TimeMinutes(), m.text))
                    if read is True:
                        m.markAsRead()

            if mbox_messages:
                messages.append({'user':mbox.id, 'messages':tuple(mbox_messages)})
        return messages

    def getUnclearedMessages(self, sender=None, read=True, clear=False):
        """ Return uncleared messages in list of dicts with senders as keys. 
            If a sender is specified, then return only the messages from that
            sender. 
            If clear=True, then mark them as cleared. Messages are usually marked
            as cleared when the chat session is over.
        """
        if sender:
            mboxes = [self._getMessageBox(sender)]
        else:
            mboxes = self.objectValues()
            
        messages = []
        for mbox in mboxes:
            mbox_messages = []
            for m in mbox.objectValues():
                if m.uncleared():
                    mbox_messages.append((m.author, m.time.Date(), m.time.TimeMinutes(), m.text))
                    if read is True:
                        m.markAsRead()
                    if clear is True:
                        m.markAsCleared()

            if mbox_messages:
                messages.append({'user':mbox.id, 'messages':tuple(mbox_messages)})
        return messages

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

    def _getMessageBox(self, owner):
        if owner not in self.objectIds():
            self._setObject(owner, MessageBox(owner))
        return self._getOb(owner)

    def _getUser(self, username):
        return self.aq_parent._getOb(username)

