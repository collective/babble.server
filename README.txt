Introduction
============

babble.server is a messaging service for Zope2 based systems.

It's the chat server for babble.client, an instant messaging
client for Plone, but it doesn't have any dependencies on Plone or babble.client
and is designed to be usable as a backend, independent of any frontend.

Features:
---------

- User accounts: users must be registered for the chat service
- Security: most messaging actions requires the user to authenticate 
- User status support: users can set their status, such as 'busy', 'chatty' or
  'invisible'.
- Web service: all public API methods return JSON strings.
- 100% test coverage.

Usage:
------

Simply add the Chat Service in the ZMI (Zope Management Interface) by clicking
on the dropdown box and choosing it from the list.


API:
----

For a detailed look at the API methods with a description of each ones 
purpose and the JSON values it returns, please see:
- babble.server.interfaces.py:IChatService.py

The current API is:

    * confirmAsOnline(username)
    * register(username, password)
    * isRegistered(username)
    * setUserPassword(username, password)
    * getOnlineUsers()
    * setStatus(username, password, status)
    * getStatus(username)
    * sendMessage(username, password, recipient, message)
    * getUnreadMessages(username, password, read=True)
    * getUnclearedMessages(username, password, sender=None, read=True, clear=False)


