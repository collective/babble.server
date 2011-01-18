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

Additional info:
----------------

For additional info, please read the documentation at 
http://opkode.net/babbledocs/babble.server/index.html 

TODO:
-----
 - Make the read attr on messages a timestamp (instead of bool)

