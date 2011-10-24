import logging
from zope.interface import implements
from Products.BTreeFolder2.BTreeFolder2 import BTreeFolder2
from messagebox import MessageBox
from interfaces import IConversation
from utils import hashed

log = logging.getLogger(__name__)

class Conversation(BTreeFolder2):
    """ A conversation between two persons """
    implements(IConversation)


    def __init__(self, id, user1, user2):
        super(Conversation, self).__init__(id)
        self.partner = {user1:user2, user2:user1}


    def _getMessageBox(self, owner):
        """ The MessageBox is a container that stores
            the messages sent a user.

            We store the sent and received messages in two different
            messageboxes, instead of the conversation itself, to avoid conflict
            errors.
        """
        owner = hashed(owner)
        if owner not in self.objectIds():
            self._setObject(owner, MessageBox(owner))
        return self._getOb(owner)


    def addMessage(self, text, author):
        """ Add a message to the Conversation """
        mbox = self._getMessageBox(author)
        return mbox.addMessage(text, author)


