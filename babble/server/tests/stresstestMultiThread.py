import sys
import threading
import random
import time
import traceback
import transaction
import simplejson as json

from Testing import makerequest
from unittest import TestCase, TestSuite, TextTestRunner, makeSuite
from ZODB import DB
from ZODB.POSException import ConflictError
from ZODB.POSException import ReadConflictError
from ZODB.POSException import BTreesConflictError
from ZODB.DemoStorage import DemoStorage
from OFS.Application import Application

from babble.server.service import ChatService
from babble.server import config

sys.setcheckinterval(200)
stuff = {}

def _getDB():
    db = stuff.get('db')
    if not db:
        ds = DemoStorage()
        db = DB(ds)
        conn = db.open()
        root = conn.root()
        app = Application()
        root['Application']= app
        transaction.commit()
        _populate(root['Application'])
        stuff['db'] = db
        conn.close()
    return db

def _delDB():
    transaction.abort()
    del stuff['db']

def _populate(app):
    try: app._delObject('chatservice')
    except AttributeError: pass

    app._setObject('chatservice', ChatService('chatservice'))
    cs = app._getOb('chatservice')
    from Products.BTreeFolder2.BTreeFolder2 import manage_addBTreeFolder
    manage_addBTreeFolder(cs, 'users', 'Users')
    manage_addBTreeFolder(cs, 'conversations', 'Conversations')
    transaction.commit()

class TestMultiThread(TestCase):

    def testConcurrentChats(self):
        self.go(5)

    def go(self, usercount):
        chats = []
        db = _getDB()

        conn = db.open()
        app = conn.root()['Application']
        chatservice = getattr(app, 'chatservice')

        for i in range(usercount):
            user = 'user%s'%i
            buddy = user + 'buddy'
            chatservice.register(user, user)
            chatservice.register(buddy, buddy)
            transaction.commit()

            thread = ChatThread(db, user, buddy)
            chats.append(thread)
            thread = ChatThread(db, buddy, user)
            chats.append(thread)

        print 'Creating %d threads' % (len(chats))

        for thread in chats:
            thread.start()
            time.sleep(0.1)

        while threading.activeCount()-1 > 0:
            pass


class ChatThread(threading.Thread):

    def __init__(self, db, user, buddy):
        self.user = user
        self.buddy = buddy
        self.db = db
        threading.Thread.__init__(self)

    def run(self):
        try:
            while 1:
                self.conn = self.db.open()
                self.app = self.conn.root()['Application']
                self.app = makerequest.makerequest(self.app)

                try:
                    self.send_and_read()
                    return
                except ReadConflictError:
                    print "R",
                except BTreesConflictError:
                    print "B",
                except ConflictError:
                    print "W",
                
                transaction.abort()
                self.conn.close()
                time.sleep(random.randrange(10) * .1)
        finally:
            transaction.abort()
            self.conn.close()
            del self.app
            print '%s finished' % self.__class__

    def send_and_read(self):
        chatservice = getattr(self.app, 'chatservice')
        for i in range(200):
            chatservice.sendMessage(self.user, self.user, self.buddy, 'message%s'%i)
            transaction.commit()
            messages = json.loads(chatservice.getUnclearedMessages(self.user, self.user, self.buddy, config.NULL_DATE))
            transaction.commit()
            # print '%s -> %s: %s' % (self.buddy, self.user, len(messages['messages'].values()[0]))
            # time.sleep(random.randrange(10) * .1)


def test_suite():
    test_multithread = makeSuite(TestMultiThread, 'test')
    suite = TestSuite((test_multithread,))
    return suite

if __name__ == '__main__':
    runner = TextTestRunner(verbosity=9, descriptions=9)
    runner.run(test_suite())
        
