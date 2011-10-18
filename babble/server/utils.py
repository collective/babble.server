from hashlib import sha224

def hash_encode(username):
    try:
        return sha224(username).hexdigest()
    except UnicodeEncodeError:
        return sha224(username.encode('utf-8')).hexdigest()
