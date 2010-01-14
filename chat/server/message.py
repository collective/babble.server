from zope.interface import implements
from OFS.SimpleItem import SimpleItem
from DateTime import DateTime

from interfaces import IMessage

class Message(SimpleItem):
    """ A message """

    implements(IMessage)

    def __init__(self, message):
        """ initialize message """
        self.time = DateTime()
        self.id = 'message.%s' % self.time.millis()
        self.text = message
        self._read = False

    def unread(self):
        return not self._read

    def markAsRead(self):
        self._read = True
