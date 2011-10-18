import time
import dateutil.parser
import transaction
from hashlib import sha224
from pytz import utc
from zExceptions import BadRequest
from DateTime.interfaces import IDateTime
from Products.BTreeFolder2.BTreeFolder2 import manage_addBTreeFolder
from babble.server.conversation import Conversation
from babble.server.messagebox import MessageBox
from babble.server.interfaces import IChatService
from babble.server.message import Message

def run(self):
    """
    * Move existing messages from messageboxes in IUser objects, messageboxes
      in IConversation objects.
    * Rename all old messages' ids to remove the previx "message."
    * Change all old messages' time attr to python's datetime.
    """
    services = []
    for o in self.objectValues():
        if IChatService.providedBy(o):
            services.append(o)

    for service in services:

        if not hasattr(service, 'conversations'):
            manage_addBTreeFolder(service, 'conversations', 'Conversations')
        convs = service._getOb('conversations')

        for user in getattr(service, 'users').objectValues():
            for oldmbox in user.objectValues():

                cid = '.'.join(sorted([sha224(user.id).hexdigest(), sha224(oldmbox.id).hexdigest()]))
                if not convs.hasObject(cid):
                    convs._setObject(cid, Conversation(cid, user.id, oldmbox.id))
                conv = convs._getOb(cid)
                if oldmbox.id not in conv.objectIds():
                    conv._setObject(oldmbox.id, MessageBox(oldmbox.id))
                newmbox = conv._getOb(oldmbox.id)
                mids = []
                oldids = []
                newids = []
                for message in oldmbox.objectValues():
                    if message.author != oldmbox.id:
                        # We now only store one author's messages per mbox. So
                        # we ignore the other messages. They will be deleted.
                        continue

                    if IDateTime.providedBy(message.time):
                        message.time = message.time.asdatetime().replace(tzinfo=utc)
                    elif type(message.time) == str:
                        message.time = dateutil.parser.parse(message.time)

                    newid = '%f' % time.mktime(message.time.timetuple())
                    message.time = message.time.isoformat()

                    newmsg= Message(message.text, message.author)
                    newmsg.time = message.time
                    newmsg.id = newid
                    try:
                        newmbox._setObject(newid, message)
                    except BadRequest:
                        continue

                transaction.commit()

    return "Succesfully migrated the messages"

