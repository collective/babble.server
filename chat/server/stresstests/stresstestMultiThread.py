import sys, os, time
import time, threading, random
from unittest import TestCase, TestSuite, TextTestRunner, makeSuite

from Testing import makerequest
import transaction
import ZODB
from ZODB.POSException import ConflictError, ReadConflictError, \
    BTreesConflictError
from ZODB.DemoStorage import DemoStorage
from OFS.Application import Application
from OFS.Folder import Folder
from zLOG.EventLogger import log_time

from babble.server.service import ChatService

sys.setcheckinterval(200)

stuff = {}

def _getDB():
    db = stuff.get('db')
    if not db:
        ds = DemoStorage()
        db = ZODB.DB(ds)
        conn = db.open()
        root = conn.root()
        app = Application()
        root['Application']= app
        _populate(app)
        transaction.commit()
        stuff['db'] = db
        conn.close()
    return db

def _delDB():
    transaction.abort()
    del stuff['db']

def _populate(app):
    chatservice = ChatService('chatservice')

    try: app._delObject('chatservice')
    except AttributeError: pass

    app._setObject('chatservice', chatservice)

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

        for thread in chats:
            thread.start()
            time.sleep(0.1)

        active = threading.activeCount()
        while active > 0:
            active = threading.activeCount()-1
            print 'waiting for %s threads' % active
            print "chats: ", numActive(chats),
            time.sleep(5)

def numActive(threads):
    i = 0
    for thread in threads:
        if not thread.isFinished():
            i+=1
    return i

class ChatThread(threading.Thread):
    def __init__(self, db, user, buddy):
        self.user = user
        self.buddy = buddy
        self.finished = 0
        self.db = db
        threading.Thread.__init__(self)

    def run(self):
        i = 0
        try:
            while 1:
                self.conn = self.db.open()
                self.app = self.conn.root()['Application']
                self.app = makerequest.makerequest(self.app)

                try:
                    self.run1()
                    return
                except ReadConflictError:
                    #traceback.print_exc()
                    print "R",
                except BTreesConflictError:
                    print "B",
                except ConflictError:
                    print "W",
                except:
                    transaction.abort()
                    print log_time()
                    traceback.print_exc()
                    raise
                
                i = i + 1
                transaction.abort()
                self.conn.close()
                time.sleep(random.randrange(10) * .1)
        finally:
            transaction.abort()
            self.conn.close()
            del self.app
            self.finished = 1
            print '%s finished' % self.__class__

    def run1(self):
        chatservice = getattr(self.app, 'chatservice')
        for i in range(100):
            chatservice.sendMessage(self.user, self.buddy, 'message%s'%i)
            transaction.commit()
            messages = chatservice.getMessagesForUser(self.user, self.buddy)
            print '%s -> %s: %s' % (self.buddy, self.user, str(messages))
            transaction.commit()
            time.sleep(random.randrange(10) * .1)

    def isFinished(self):
        return self.finished
        

def test_suite():
    test_multithread = makeSuite(TestMultiThread, 'test')
    suite = TestSuite((test_multithread,))
    return suite

if __name__ == '__main__':
    runner = TextTestRunner(verbosity=9, descriptions=9)
    runner.run(test_suite())
