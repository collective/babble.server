from babble.server.service import ChatService
from babble.server import UseChatService

class ChatServiceAddView:

    """Add view for Chat Service.
    """

    def __call__(self, add_input_name='', title='', submit_add=''):
        if submit_add:
            self.context.REQUEST.set('add_input_name', add_input_name)
            obj = ChatService(add_input_name)
            obj.title = title
            obj.manage_addUserFolder()
            self.context.add(obj)
            obj = self.context.aq_acquire(obj.id)
            obj.manage_permission(UseChatService,
                roles=('Authenticated',), acquire=1)
            self.request.response.redirect(self.context.nextURL())
            return ''
        return self.index()
