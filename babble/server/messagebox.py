from zope.interface import implements
from Products.BTreeFolder2.BTreeFolder2 import BTreeFolder2
from message import Message
from interfaces import IMessageBox

class MessageBox(BTreeFolder2):
    """ A container for messages """
    implements(IMessageBox)

    def addMessage(self, message, author, read=False):
        """ Add a message to the MessageBox """
        message = Message(message, author, read)
        self._setObject(message.id, message)
