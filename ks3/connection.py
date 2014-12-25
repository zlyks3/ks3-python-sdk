# coding:utf-8

#  This software code is made available without warranties of any
#  kind.  You may copy, display, modify and redistribute the software
#  code either by itself or as incorporated into your code; provided that
#  you do not remove any proprietary notices. Your use of this software
#  code is at your own risk.

import xml.sax

from ks3 import handler
from ks3.bucket import Bucket
from ks3.bucketlogging import BucketLogging
from ks3.exception import S3ResponseError, S3CreateError
from ks3.http import make_request, CallingFormat
from ks3.provider import Provider
from ks3.resultset import ResultSet

def check_lowercase_bucketname(n):
    """
    Bucket names must not contain uppercase characters. We check for
    this by appending a lowercase character and testing with islower().
    Note this also covers cases like numeric bucket names with dashes.

    >>> check_lowercase_bucketname("Aaaa")
    Traceback (most recent call last):
    ...
    BotoClientError: S3Error: Bucket names cannot contain upper-case
    characters when using either the sub-domain or virtual hosting calling
    format.

    >>> check_lowercase_bucketname("1234-5678-9123")
    True
    >>> check_lowercase_bucketname("abcdefg1234")
    True
    """
    if not (n + 'a').islower():
        raise BotoClientError("Bucket names cannot contain upper-case " \
            "characters when using either the sub-domain or virtual " \
            "hosting calling format.")
    return True

class Connection(object):

    def __init__(self, access_key_id, access_key_secret, host="kss.ksyun.com",
            port=80, provider='kss', security_token=None, profile_name=None,
            is_secure=False, debug=0):
        self.access_key_id = access_key_id
        self.access_key_secret = access_key_secret
        self.is_secure = is_secure
        self.host = host
        self.port = port
        self.debug = debug

        if isinstance(provider, Provider):
            # Allow overriding Provider
            self.provider = provider
        else:
            self._provider_type = provider
            self.provider = Provider(self._provider_type,
                                     access_key_id,
                                     access_key_secret,
                                     security_token,
                                     profile_name)

        # Allow config file to override default host, port, and host header.
        if self.provider.host:
            self.host = self.provider.host
        if self.provider.port:
            self.port = self.provider.port
        if self.provider.host_header:
            self.host_header = self.provider.host_header
        
    def make_request(self, method, bucket="", key="", data="",
            headers=None, query_args=None, metadata=None):
        if not headers:
            headers = {}
        if not query_args:
            query_args = {}
        if not metadata:
            metadata = {}

        resp = make_request(self.host, self.port, self.access_key_id,
                            self.access_key_secret, method, bucket, key,
                            query_args, headers, data, metadata)
        
        return resp

    def get_all_buckets(self, headers=None):
        response = self.make_request('GET', headers=headers)
        body = response.read()
        if response.status > 300:
            raise S3ResponseError(response.status, response.reason, body)
        rs = ResultSet([('Bucket', Bucket)])
        h = handler.XmlHandler(rs, self)
        if not isinstance(body, bytes):
            body = body.encode('utf-8')
        xml.sax.parseString(body, h)
        return rs

    def get_bucket(self, bucket_name, headers=None):
        return Bucket(self, bucket_name)

    def create_bucket(self, bucket_name, headers=None,
                      location=None, policy=None):
        check_lowercase_bucketname(bucket_name)

        if policy:
            if headers:
                headers[self.provider.acl_header] = policy
            else:
                headers = {self.provider.acl_header: policy}
        if location == None:
            data = ''
        else:
            data = '<CreateBucketConfiguration><LocationConstraint>' + \
                    location + '</LocationConstraint></CreateBucketConfiguration>'
        response = self.make_request('PUT', bucket_name, headers=headers,
                data=data)
        body = response.read()
        if response.status == 409:
            raise S3CreateError(response.status, response.reason, body)
        if response.status == 200:
            return Bucket(self, bucket_name)
        else:
            raise S3ResponseError(response.status, response.reason, body)

    def delete_bucket(self, bucket_name, headers=None):
        """
        Removes an S3 bucket.

        In order to remove the bucket, it must first be empty. If the bucket is
        not empty, an ``S3ResponseError`` will be raised.
        """
        response = self.make_request('DELETE', bucket_name, headers=headers)
        body = response.read()
        if response.status != 204:
            raise S3ResponseError(response.status, response.reason, body)

    def set_xml_logging(self, logging_str, headers=None):
        """
        Set logging on a bucket directly to the given xml string.

        :type logging_str: unicode string
        :param logging_str: The XML for the bucketloggingstatus which
            will be set.  The string will be converted to utf-8 before
            it is sent.  Usually, you will obtain this XML from the
            BucketLogging object.

        :rtype: bool
        :return: True if ok or raises an exception.
        """
        body = logging_str
        if not isinstance(body, bytes):
            body = body.encode('utf-8')
        response = self.connection.make_request('PUT', self.name, data=body,
                query_args={'logging':''}, headers=headers)
        body = response.read()
        if response.status == 200:
            return True
        else:
            raise S3ResponseError(response.status, response.reason, body)

    def enable_logging(self, target_bucket, target_prefix='',
                       grants=None, headers=None):
        """
        Enable logging on a bucket.

        :type target_bucket: bucket or string
        :param target_bucket: The bucket to log to.

        :type target_prefix: string
        :param target_prefix: The prefix which should be prepended to the
            generated log files written to the target_bucket.

        :type grants: list of Grant objects
        :param grants: A list of extra permissions which will be granted on
            the log files which are created.

        :rtype: bool
        :return: True if ok or raises an exception.
        """
        if isinstance(target_bucket, Bucket):
            target_bucket = target_bucket.name
        blogging = BucketLogging(target=target_bucket, prefix=target_prefix,
                                 grants=grants)
        return self.set_xml_logging(blogging.to_xml(), headers=headers)

    def disable_logging(self, headers=None):
        """
        Disable logging on a bucket.

        :rtype: bool
        :return: True if ok or raises an exception.
        """
        blogging = BucketLogging()
        return self.set_xml_logging(blogging.to_xml(), headers=headers)

    def get_logging_status(self, headers=None):
        """
        Get the logging status for this bucket.

        :rtype: :class:`boto.s3.bucketlogging.BucketLogging`
        :return: A BucketLogging object for this bucket.
        """
        response = self.connection.make_request('GET', self.name,
                query_args={'logging':''}, headers=headers)
        body = response.read()
        if response.status == 200:
            blogging = BucketLogging()
            h = handler.XmlHandler(blogging, self)
            if not isinstance(body, bytes):
                body = body.encode('utf-8')
            xml.sax.parseString(body, h)
            return blogging
        else:
            raise S3ResponseError(response.status, response.reason, body)

