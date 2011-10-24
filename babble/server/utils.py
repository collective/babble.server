from hashlib import sha224

def hashed(str):
    try:
        return sha224(str).hexdigest()
    except UnicodeEncodeError:
        return sha224(str.encode('utf-8')).hexdigest()
