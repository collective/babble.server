import logging
from zope.interface import implements

from Products.BTreeFolder2.BTreeFolder2 import BTreeFolder2

from interfaces import IUser

log = logging.getLogger('babble.server/user.py')

# Deprecated... currently not in use.

class User(BTreeFolder2):
    """ A user on the message server """

    implements(IUser)
    _status = 'online'

    def setStatus(self, status):
        """ Sets the user's status """
        self._status = status

    def getStatus(self):
        """ Returns the user's status """
        return self._status
