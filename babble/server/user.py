import logging
from DateTime.interfaces import IDateTime
from zope.interface import implements
from Products.BTreeFolder2.BTreeFolder2 import BTreeFolder2
from messagebox import MessageBox
from interfaces import IUser

log = logging.getLogger('babble.server/user.py')

class User(BTreeFolder2):
    """ A user on the message server """

    implements(IUser)
    _status = 'online'

    def _getMessageBox(self, owner):
        """ The MessageBox is a container inside the 'User' object that stores
            the messages sent and received by that user.
        """
        if owner not in self.objectIds():
            self._setObject(owner, MessageBox(owner))
        return self._getOb(owner)


    def setStatus(self, status):
        """ Sets the user's status """
        self._status = status


    def getStatus(self):
        """ Returns the user's status """
        return self._status


    def addMessage(self, contact, message, author, read=False):
        """ Add a message to this user's contact's messagebox
            
            The message author could be either the user or the
            contact (conversation partnet), and is therefore passed 
            as a separate var.
        """
        mbox = self._getMessageBox(contact)
        mbox.addMessage(message, author, read)


    def getMessages(self, since):
        """ Return all messages since a certain date, and the timestamp of the
            newest message.

            If 'since' is not provided, all messages are returned.

            The date format of 'since' must be iso8601. 
            
            To generate a date in this format, use the ISO8601() method for
            Zope2 DateTime objects and isoformat() for python's builtin
            datetime types.

            It's very important that timezone information is also included!
            I.e datetime.now(utc) instead of datetime.now()
        """
        timestamp = since
        messages = {}
        for mbox in self.objectValues():
            mbox_messages = []
            for m in mbox.objectValues():
                # In older versions timestamps were saved as Zope2 DateTime
                # objs
                if IDateTime.providedBy(m.time):
                    message_time = m.time.ISO8601()
                    if message_time > since:
                        date = m.time.Date()
                        time = m.time.toZone('UTC').TimeMinutes()
                        mbox_messages.append((m.author, date, time, m.text))

                else:
                    message_time = m.time.isoformat()
                    if message_time > since:
                        date = m.time.strftime('%Y/%m/%d')
                        time = m.time.strftime('%H:%M')
                        mbox_messages.append((m.author, date, time, m.text))

                if message_time  > timestamp:
                    timestamp = message_time

            if mbox_messages:
                messages[mbox.id] = tuple(mbox_messages)

        return messages, timestamp


    def getUnreadMessages(self, read=True):
        """ Return unread messages in a dictionary with the senders as keys.
            If read=True, then mark them as read.
        """
        mboxes = self.objectValues()
        messages = {}
        for mbox in mboxes:
            mbox_messages = []
            for m in mbox.objectValues():
                if m.unread():
                    if IDateTime.providedBy(m.time):
                        message_time = m.time.ISO8601()
                        date = m.time.Date()
                        time = m.time.toZone('UTC').TimeMinutes()
                        mbox_messages.append((m.author, date, time, m.text))

                    else:
                        message_time = m.time.isoformat()
                        date = m.time.strftime('%Y/%m/%d')
                        time = m.time.strftime('%H:%M')
                        mbox_messages.append((m.author, date, time, m.text))

                    if read is True:
                        m.markAsRead()

            if mbox_messages:
                messages[mbox.id] = tuple(mbox_messages)
        return messages


    def getUnclearedMessages(self, sender=None, read=True, clear=False):
        """ Return uncleared messages in list of dicts with senders as keys. 
            If a sender is specified, then return only the messages sent by
            him/her.

            If clear=True, then mark them as cleared. Messages are usually marked
            as cleared when the chat session is over.
        """
        if sender:
            mboxes = [self._getMessageBox(sender)]
        else:
            mboxes = self.objectValues()
            
        messages = {}
        for mbox in mboxes:
            mbox_messages = []
            for m in mbox.objectValues():
                if m.uncleared():
                    if IDateTime.providedBy(m.time):
                        message_time = m.time.ISO8601()
                        date = m.time.Date()
                        time = m.time.toZone('UTC').TimeMinutes()
                        mbox_messages.append((m.author, date, time, m.text))

                    else:
                        message_time = m.time.isoformat()
                        date = m.time.strftime('%Y/%m/%d')
                        time = m.time.strftime('%H:%M')
                        mbox_messages.append((m.author, date, time, m.text))

                    if read is True:
                        m.markAsRead()
                    if clear is True:
                        m.markAsCleared()

            if mbox_messages:
                messages[mbox.id] = tuple(mbox_messages)
        return messages

