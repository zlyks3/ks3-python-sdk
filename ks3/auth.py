
from hashlib import sha1

import base64
import hmac
import time
import urllib

def canonical_string(method, bucket="", key="", query_args=None, headers=None, expires=None):
    if not headers:
        headers = {}
    if not query_args:
        query_args = ""
        
    interesting_headers = {}
    for header_key in headers:
        lk = header_key.lower()
        if lk in ['content-md5', 'content-type', 'date'] or lk.startswith("x-kss-"):
            interesting_headers[lk] = headers[header_key].strip()
    if not interesting_headers.has_key('content-type'):
        interesting_headers['content-type'] = ''
    if not interesting_headers.has_key('content-md5'):
        interesting_headers['content-md5'] = ''
    if interesting_headers.has_key('x-kss-date'):
        interesting_headers['date'] = ''
    if expires:
        interesting_headers['date'] = str(expires)

    sorted_header_keys = interesting_headers.keys()
    sorted_header_keys.sort()
    buf = "%s\n" % method
    for header_key in sorted_header_keys:
        if header_key.startswith("x-kss-"):
            buf += "%s:%s\n" % (header_key, interesting_headers[header_key])
        else:
            buf += "%s\n" % interesting_headers[header_key]

    if bucket:
        buf += "/%s" % bucket
    buf += "/%s" % urllib.quote_plus(key.encode('utf-8'))
    
    if query_args and "prefix=" not in query_args:
        buf += "?" + query_args

    return buf

def encode(secret_access_key, str_to_encode, urlencode=False):
    b64_hmac = base64.encodestring(hmac.new(secret_access_key, str_to_encode, sha1).digest()).strip()
    if urlencode:
        return urllib.quote_plus(b64_hmac)
    else:
        return b64_hmac

def add_auth_header(access_key_id, secret_access_key, headers, method, bucket, key, query_args):
    if not access_key_id:
        return
    if not headers.has_key('Date'):
        headers['Date'] = time.strftime("%a, %d %b %Y %H:%M:%S GMT", time.gmtime())

    c_string = canonical_string(method, bucket, key, query_args, headers)
    headers['Authorization'] = \
        "%s %s:%s" % ("KSS", access_key_id, encode(secret_access_key, c_string))

