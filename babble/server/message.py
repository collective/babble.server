import time
from pytz import utc
from datetime import datetime
from zope.interface import implements
from OFS.SimpleItem import SimpleItem
from interfaces import IMessage

class Message(SimpleItem):
    """ A message """

    implements(IMessage)

    def __init__(self, message, author, fullname):
        """ Initialize message 
        """
        self._cleared = False
        self.author = author
        self.text = message
        self.fullname = fullname

        ts = time.time()
        self.id = '%f' % ts
        self.time = datetime.utcfromtimestamp(ts).replace(tzinfo=utc).isoformat()
