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


Important notice:
-----------------

If you are upgrading from babble.server 0.x to 1.x, you *must* run the upgrade
step.

This requires that you add the external method in Extensions/upgrade_to_1.0.py
in the same Zope instance where you have added the ChatService, and then run it
by clicking on the "test" tab.

Make sure to backup your Data.fs before running the upgrade!

You can use the following values when adding the External Method:

Id:             upgrade_to_1.0
Title:          Babble Server Upgrade 1.0
Module Name:    babble.server.upgrade_to_1_0
Function Name:  run
