from Acquisition import aq_base
from Products.BTreeFolder2.BTreeFolder2 import manage_addBTreeFolder
from babble.server.service import ChatService
from babble.server import UseChatService

class ChatServiceAddView:
    """Add view for Chat Service.
    """

    def __call__(self, add_input_name='', title='', submit_add=''):
        if submit_add:
            self.request.set('add_input_name', add_input_name)
            obj = ChatService(add_input_name)
            obj.title = title
            self.context.add(obj)
            obj = self.context.aq_acquire(obj.id)

            aq_base(obj).manage_addUserFolder()
            manage_addBTreeFolder(aq_base(obj), 'users', 'Users')

            obj.manage_permission(UseChatService,
                roles=('Authenticated',), acquire=1)
            self.request.response.redirect(self.context.nextURL())
            return ''

        return self.index()
