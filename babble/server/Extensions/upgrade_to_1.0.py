def run(self, chatservice_id):
    """
    * Move existing messages from messageboxes in IUser objects, to the new
      IConversation objects.
    * Rename all old messages' ids to remove "message."
    * Change all old messages' time attr to python's datetime.
    """
    if not hasattr(self, chatservice_id):
        return "Could not find chatservice with id %s" % chatservice_id

    chatservice = getattr(self, chatservice_id)
    
    # if not hasattr(self, 'conversations'):
        
     
        
