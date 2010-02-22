from zope.interface import implements
from OFS.SimpleItem import SimpleItem
from DateTime import DateTime

from interfaces import IMessage

class Message(SimpleItem):
    """ A message """

    implements(IMessage)

    def __init__(self, message, author, read=False):
        """ Initialize message 
        """
        self._cleared = False
        self._read = read
        self.author = author
        self.text = message
        self.time = DateTime()
        self.id = 'message.%s' % self.time.millis()
        
    def unread(self):
        return not self._read

    def markAsRead(self):
        self._read = True

    def uncleared(self):
        return not self._cleared

    def markAsCleared(self):
        self._cleared= True