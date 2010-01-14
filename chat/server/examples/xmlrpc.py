from xmlrpclib import Server
s = Server('http://admin:local@localhost:8030/chatservice')

# add a property definition
s.manage_addProperty('msisdn', '', 'string')

# register
s.register('chatterbox', 'password')
s.register('buddyholly', 'password')

# set a property for a user
s.setUserProperty('chatterbox', 'msisdn', '270820000000')
s.setUserProperty('buddyholly', 'msisdn', '270820000001')

# get a property for a user
s.getUserProperty('chatterbox', 'msisdn')
s.getUserProperty('buddyholly', 'msisdn')

# find a user
s.findUser('msisdn', '270820000000')

# sign in
s.signIn('chatterbox')
s.signIn('buddyholly')

# check if online
s.isOnline('chatterbox')
s.isOnline('buddyholly')

# make contact request, chatterbox requests contact with buddyholly
# chatterbox has a contact request, buddyholly has a pending contact
s.requestContact('chatterbox', 'buddyholly')
s.getContactRequests('chatterbox')
s.getPendingContacts('buddyholly')

# approve contact requests, buddyholly accepts chatterbox's request
# both are contacts of each other now
s.approveContactRequest('buddyholly', 'chatterbox')
# as opposed to declineContactRequest('buddyholly', 'chatterbox')
s.getContacts('buddyholly')
s.getContacts('chatterbox')

# send message from 'chatterbox' to 'buddyholly'
s.sendMessage('chatterbox', 'buddyholly', 'hallo')

# get messages for buddyholly from chatterbox
s.getMessagesForUser('buddyholly', 'chatterbox')

