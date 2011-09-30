from time import time
from datetime import datetime
from pytz import utc
from zope.interface import implements
from OFS.SimpleItem import SimpleItem
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
        self.time = datetime.now(utc)
        self.id = 'message.%s' % time()
        
    def unread(self):
        """ Has this message been read? """
        return not self._read

    def markAsRead(self):
        """ Mark this message as being read """
        self._read = True

    def uncleared(self):
        """ Has this message been cleard? """
        return not self._cleared

    def markAsCleared(self):
        """ Mark this message as cleared """
        self._cleared= True
