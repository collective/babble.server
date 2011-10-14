def run(self):
    """
    * Move existing messages from messageboxes in IUser objects, to the new
      IConversation objects.
    * Rename all old messages' ids to remove "message."
    * Change all old messages' time attr to python's datetime.
    """
    
