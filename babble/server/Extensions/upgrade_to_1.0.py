from DateTime.interfaces import IDateTime
from Products.BTreeFolder2.BTreeFolder2 import manage_addBTreeFolder
from babble.server.conversation import Conversation
from babble.server.messagebox import MessageBox

def run(self, chatservice_id):
    """
    * Move existing messages from messageboxes in IUser objects, messageboxes
      in IConversation objects.
    * Rename all old messages' ids to remove the previx "message."
    * Change all old messages' time attr to python's datetime.
    """
    if not hasattr(self, chatservice_id):
        return "Could not find chatservice with id %s" % chatservice_id

    service = getattr(self, chatservice_id)
    
    if not hasattr(self, 'conversations'):
        manage_addBTreeFolder(service, 'conversations', 'Conversations')
    convs = self._getOb('conversations')

    for user in getattr(self, 'users'):
        for oldmbox in user.objectValues('MessageBox'):

            ord1 = ''.join([str(ord(c)) for c in user])
            ord2 = ''.join([str(ord(c)) for c in oldmbox.id])
            cid = '-'.join(sorted([ord1, ord2]))
            if not convs.hasObject(id):
                convs._setObject(id, Conversation(id, user, oldmbox.id))
            c = convs._getOb(id)
            if oldmbox.id not in c.objectIds():
                c._setObject(oldmbox.id, MessageBox(oldmbox.id))
            newmbox = c._getOb(oldmbox.id)
            mids = []
            for message in oldmbox.objectValues('Message'):
                if message.author != oldmbox.id:
                    # We now only store one author's messages per mbox. So
                    # we ignore the other messages. They will be deleted.
                    continue
                message.id = message.id.strip('message.')

                # Switch from zope's DateTime to python's datetime
                if IDateTime.providedBy(message.time):
                    message.time = message.time.asdatetime()

                mids.append(message.id)

            # Move the messages from the old mbox to the new one.
            cp = oldmbox.manage_cutObjects(mids)
            newmbox.manage_pasteObjects(cb_copy_data=cp)
            # Delete the messages left over (they are duplicates)
            oldmbox.manage_delObjects(oldmbox.objectIds())

