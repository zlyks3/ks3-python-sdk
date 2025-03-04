import os
from ks3 import user
from ks3 import handler
try:
    from ks3.encryption import Crypts
except:
    pass
import xml.sax


class CompleteMultiPartUpload(object):
    """
    Represents a completed MultiPart Upload.  Contains the
    following useful attributes:

     * location - The URI of the completed upload
     * bucket_name - The name of the bucket in which the upload
                     is contained
     * key_name - The name of the new, completed key
     * etag - The MD5 hash of the completed, combined upload
     * version_id - The version_id of the completed upload
     * encrypted - The value of the encryption header
    """

    def __init__(self, bucket=None):
        self.bucket = bucket
        self.location = None
        self.bucket_name = None
        self.key_name = None
        self.etag = None
        self.version_id = None
        self.encrypted = None

    def __repr__(self):
        return '<CompleteMultiPartUpload: %s.%s>' % (self.bucket_name,
                                                     self.key_name)

    def startElement(self, name, attrs, connection):
        return None

    def endElement(self, name, value, connection):
        if name.startswith("ns2"):
            name = name.split(":")[1]
        if name == 'Location':
            self.location = value
        elif name == 'Bucket':
            self.bucket_name = value
        elif name == 'Key':
            self.key_name = value
        elif name == 'ETag':
            self.etag = value
        else:
            setattr(self, name, value)


class Part(object):
    """
    Represents a single part in a MultiPart upload.
    Attributes include:

     * part_number - The integer part number
     * last_modified - The last modified date of this part
     * etag - The MD5 hash of this part
     * size - The size, in bytes, of this part
    """

    def __init__(self, bucket=None):
        self.bucket = bucket
        self.part_number = None
        self.last_modified = None
        self.etag = None
        self.size = None

    def __repr__(self):
        if isinstance(self.part_number, int):
            return '<Part %d>' % self.part_number
        else:
            return '<Part %s>' % None

    def startElement(self, name, attrs, connection):
        return None

    def endElement(self, name, value, connection):
        if name.startswith("ns2"):
            name = name.split(":")[1]
        if name == 'PartNumber':
            self.part_number = int(value)
        elif name == 'LastModified':
            self.last_modified = value
        elif name == 'ETag':
            self.etag = value
        elif name == 'Size':
            self.size = int(value)
        else:
            setattr(self, name, value)


def part_lister(mpupload, part_number_marker=None):
    """
    A generator function for listing parts of a multipart upload.
    """
    more_results = True
    part = None
    while more_results:
        parts = mpupload.get_all_parts(None, part_number_marker)
        for part in parts:
            yield part
        part_number_marker = mpupload.next_part_number_marker
        more_results = mpupload.is_truncated


class MultiPartUpload(object):
    """
    Represents a MultiPart Upload operation.
    """

    def __init__(self, bucket=None):
        self.bucket = bucket
        self.bucket_name = None
        self.key_name = None
        self.id = id
        self.initiator = None
        self.owner = None
        self.storage_class = None
        self.initiated = None
        self.part_number_marker = None
        self.next_part_number_marker = None
        self.max_parts = None
        self.is_truncated = False
        self._parts = None
        self.crypt_context = None
        # self.size_accumulator = 0
        self.size_accumulator = {}
        self.total_size = 0


    def __repr__(self):
        return '<MultiPartUpload %s>' % self.key_name

    def __iter__(self):
        return part_lister(self)

    def to_xml(self):
        s = '<CompleteMultipartUpload>\n'
        for part in self:
            s += '  <Part>\n'
            s += '    <PartNumber>%d</PartNumber>\n' % part.part_number
            s += '    <ETag>%s</ETag>\n' % part.etag
            s += '  </Part>\n'
        s += '</CompleteMultipartUpload>'
        return s

    def set_crypt_context(self, crypt):
        self.crypt_context = crypt

    def startElement(self, name, attrs, connection):
        #if name == 'Initiator':
        if name == 'ns2:Initiator':
            self.initiator = user.User(self)
            return self.initiator
        #elif name == 'Owner':
        elif name == 'ns2:Owner':
            self.owner = user.User(self)
            return self.owner
        #elif name == 'Part':
        elif name == 'ns2:Part':
            part = Part(self.bucket)
            self._parts.append(part)
            return part
        return None

    def endElement(self, name, value, connection):
        if name.startswith("ns2"):
            name = name.split(":")[1]
        if name == 'Bucket':
            self.bucket_name = value
        elif name == 'Key':
            self.key_name = value
        elif name == 'UploadId':
            self.id = value
        elif name == 'StorageClass':
            self.storage_class = value
        elif name == 'PartNumberMarker':
            self.part_number_marker = value
        elif name == 'NextPartNumberMarker':
            self.next_part_number_marker = value
        elif name == 'MaxParts':
            self.max_parts = int(value)
        elif name == 'IsTruncated':
            if value == 'true':
                self.is_truncated = True
            else:
                self.is_truncated = False
        elif name == 'Initiated':
            self.initiated = value
        else:
            setattr(self, name, value)

    def get_all_parts(self, max_parts=None, part_number_marker=None,
                      encoding_type=None):
        """
        Return the uploaded parts of this MultiPart Upload.  This is
        a lower-level method that requires you to manually page through
        results.  To simplify this process, you can just use the
        object itself as an iterator and it will automatically handle
        all of the paging with S3.
        """
        self._parts = []
        query_args = 'uploadId=%s' % self.id
        if max_parts:
            query_args += '&max-parts=%d' % max_parts
        if part_number_marker:
            query_args += '&part-number-marker=%s' % part_number_marker
        if encoding_type:
            query_args += '&encoding-type=%s' % encoding_type
        response = self.bucket.connection.make_request('GET', self.bucket.name,
                                                       self.key_name,
                                                       query_args=query_args)
        body = response.read()
        if response.status == 200:
            h = handler.XmlHandler(self, self)
            xml.sax.parseString(body, h)
            return self._parts

    def upload_part_from_file(self, fp, part_num, headers=None, replace=True,
                              cb=None, num_cb=10, md5=None, size=None, is_last_part="origin"):
        """
        Upload another part of this MultiPart Upload.

        .. note::

            After you initiate multipart upload and upload one or more parts,
            you must either complete or abort multipart upload in order to stop
            getting charged for storage of the uploaded parts. Only after you
            either complete or abort multipart upload, Amazon S3 frees up the
            parts storage and stops charging you for the parts storage.

        :type fp: file
        :param fp: The file object you want to upload.

        :type part_num: int
        :param part_num: The number of this part.

        The other parameters are exactly as defined for the
        :class:`boto.s3.key.Key` set_contents_from_file method.

        :rtype: :class:`boto.s3.key.Key` or subclass
        :returns: The uploaded part containing the etag.
        """
        if part_num < 1:
            raise ValueError('Part numbers must be greater than zero')
        query_args = 'partNumber=%d&uploadId=%s' % (part_num, self.id)
        key = self.bucket.new_key(self.key_name)
        if self.bucket.connection.local_encrypt and self.crypt_context:
            #Get sizes of the whole file and the part
            fp.seek(0,os.SEEK_END)
            part_size = fp.tell()
            fp.seek(0,os.SEEK_SET)
            assert part_size, "upload part size can not be 0 !"
            self.total_size = os.fstat(fp.fileno()).st_size
            if part_size == self.total_size:
                assert is_last_part != "origin", "Please indicate 'is_last_part=False/True' \
                                                  when calling upload_part_from_file."
            else:
                size_now = self.add_all_part(part_num)
                temp_accumulator = size_now + part_size
                if temp_accumulator == self.total_size:
                    is_last_part = True
                else:
                    is_last_part = False
            if not is_last_part:
                assert (part_size % 16 == 0), "The part size must be multiples of 16 except the last part in local encrypt mode."
            self.crypt_context.part_num = part_num
            self.crypt_context.is_last_part = is_last_part
            self.crypt_context.action_info = "upload_part"
            response = key.set_contents_from_file(fp, headers=headers, replace=replace,
                                                  cb=cb, num_cb=num_cb, md5=md5,reduced_redundancy=False,
                                                  query_args=query_args, size=size, crypt_context=self.crypt_context)
            # key.set_contents_from_file() raise an exception when fail.
            self.size_accumulator[part_num] = part_size
        else:
            key.set_contents_from_file(fp, headers=headers, replace=replace,
                                       cb=cb, num_cb=num_cb, md5=md5,
                                       reduced_redundancy=False,
                                       query_args=query_args, size=size)
        return key
    def add_all_part(self, part_num):
        sum = 0
        for i in range(1,part_num):
            if self.size_accumulator.get(i):
                sum += self.size_accumulator[i]
        return sum
    def copy_part_from_key(self, src_bucket_name, src_key_name, part_num,
                           start=None, end=None, src_version_id=None,
                           headers=None):
        """
        Copy another part of this MultiPart Upload.

        :type src_bucket_name: string
        :param src_bucket_name: Name of the bucket containing the source key

        :type src_key_name: string
        :param src_key_name: Name of the source key

        :type part_num: int
        :param part_num: The number of this part.

        :type start: int
        :param start: Zero-based byte offset to start copying from

        :type end: int
        :param end: Zero-based byte offset to copy to

        :type src_version_id: string
        :param src_version_id: version_id of source object to copy from

        :type headers: dict
        :param headers: Any headers to pass along in the request
        """
        if part_num < 1:
            raise ValueError('Part numbers must be greater than zero')
        query_args = 'uploadId=%s&partNumber=%d' % (self.id, part_num)
        if start is not None and end is not None:
            rng = 'bytes=%s-%s' % (start, end)
            provider = self.bucket.connection.provider
            if headers is None:
                headers = {}
            else:
                headers = headers.copy()
            headers[provider.copy_source_range_header] = rng
        return self.bucket.copy_key(self.key_name, src_bucket_name,
                                    src_key_name,
                                    src_version_id=src_version_id,
                                    storage_class=None,
                                    headers=headers,
                                    query_args=query_args)

    def complete_upload(self):
        """
        Complete the MultiPart Upload operation.  This method should
        be called when all parts of the file have been successfully
        uploaded to S3.

        :rtype: :class:`boto.s3.multipart.CompletedMultiPartUpload`
        :returns: An object representing the completed upload.
        """
        xml = self.to_xml()
        return self.bucket.complete_multipart_upload(self.key_name,
                                                     self.id, xml)

    def cancel_upload(self):
        """
        Cancels a MultiPart Upload operation.  The storage consumed by
        any previously uploaded parts will be freed. However, if any
        part uploads are currently in progress, those part uploads
        might or might not succeed. As a result, it might be necessary
        to abort a given multipart upload multiple times in order to
        completely free all storage consumed by all parts.
        """
        self.bucket.cancel_multipart_upload(self.key_name, self.id)
