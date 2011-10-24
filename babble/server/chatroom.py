import logging
from zExceptions import Unauthorized
from zope.interface import implements
from Products.BTreeFolder2.BTreeFolder2 import BTreeFolder2
from messagebox import MessageBox
from interfaces import IChatRoom
from utils import hashed

log = logging.getLogger(__name__)

class ChatRoom(BTreeFolder2):
    """ A conversation between multiple people in a virtual room """
    implements(IChatRoom)


    def __init__(self, id, client_path, participants=[]):
        super(ChatRoom, self).__init__(id)
        self.participants = participants
        self.partner = {}
        self.client_path = client_path
        for p in participants:
            self.partner[p] = self.client_path


    def _addParticipant(self, user):
        """ """
        self.participants.append(user)
        self.partner[user] = self.client_path


    def _removeParticipant(self, user):
        """ """
        del self.participants[self.participants.index(user)]


    def _getMessageBox(self, owner):
        """ The MessageBox is a container that stores
            the messages sent by a user.

            Each user has his own messagebox to aviod conflicts.
        """
        if owner not in self.participants:
            raise Unauthorized

        owner = hashed(owner)
        if owner not in self.objectIds():
            self._setObject(owner, MessageBox(owner))
        return self._getOb(owner)


    def addMessage(self, text, author):
        """ Add a message to the Conversation """
        mbox = self._getMessageBox(author)
        return mbox.addMessage(text, author)


