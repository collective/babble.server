import logging
from zope.interface import implements
from Products.BTreeFolder2.BTreeFolder2 import BTreeFolder2
from message import Message
from interfaces import IMessageBox

log = logging.getLogger(__name__)

class MessageBox(BTreeFolder2):
    """ A container for messages """
    implements(IMessageBox)

    def addMessage(self, message, author, timestamp):
        """ Add a message to the MessageBox """
        message = Message(message, author, timestamp)
        self._setObject(message.id, message)
