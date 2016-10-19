#KS3 SDK for python使用指南
---

##开发前准备
###安装python sdk
1、通过git下载SDK到本地
```
git clone http://git.op.ksyun.com/bailingzhou/ks3-python-sdk.git
```
2、进入ks3-python-sdk目录

    cd  ks3-python-sdk

3、安装SDK

    python setup.py install

###创建一个connection
注：（[AccessKeyID和AccessKeySecret])

ACCESS_KEY_ID：金山云提供的ACCESS KEY ID

SECRET_ACCESS_KEY：金山云提供的SECRET KEY ID

YOUR_REGION_ENDPOINT: 金山云提供的各个Region的域名,参考 [KS3文档中心](http://ks3.ksyun.com/doc/api/index.html)

    from ks3.connection import Connection
    ak = 'YOUR_ACCESS_KEY'
    sk = 'YOUR_SECRET_KEY'
    c = Connection(ak, sk, host='YOUR_REGION_ENDPOINT')

###运行环境
适用于2.6、2.7的Python版本

##安全性
###使用场景
由于在App端明文存储AccessKeyID、AccessKeySecret是极不安全的，因此推荐的使用场景如下图所示：

![](http://androidsdktest21.kssws.ks-cdn.com/ks3-android-sdk-authlistener.png)

###KingSoftS3Client初始化
- 利用AccessKeyID、AccessKeySecret初始化

对应的初始化代码如下：
```
[[KingSoftS3Client initialize] connectWithAccessKey:strAccessKey withSecretKey:strSecretKey];

```

##SDK介绍及使用

###资源管理操作
* [List Buckets](#list-buckets) 列出客户所有的Bucket信息
* [Create Bucket](#create-bucket) 创建一个新的Bucket
* [Delete Bucket](#delete-bucket) 删除指定Bucket
* [Get Bucket ACL](#get-bucket-acl) 获取Bucket的ACL
* [Put Bucket ACL](#put-bucket-acl) 设置Bucket的ACL
* [Get Object](#get-object) 下载Object数据
* [Put Object](#put-object) 上传Object数据
* [List Objects](#list-objects) 列举Bucket内的Object
* [Get Object ACL](#get-object-acl) 获得Bucket的acl
* [Put Object ACL](#put-object-acl) 上传object的acl
* [Upload Part](#upload-part) 上传分块

###Service操作

####List Buckets：

*列出客户所有的 Bucket 信息*

    buckets = c.get_all_buckets()
    for b in  buckets:
        print b.name

###Bucket操作

####Create Bucket： 

*创建一个新的Bucket*

在建立了连接后，可以创建一个bucket。bucket在s3中是一个用于储存key/value的容器。用户可以将所有的数据存储在一个bucket里，也可以为不同种类数据创建相应的bucket。

    bucket_name = "YOUR_BUCKET_NAME"
    b = c.create_bucket(bucket_name)

注：这里如果出现409 conflict错误，说明请求的bucket name有冲突，因为bucket name是全局唯一的

####Delete Bucket:

*删除指定Bucket*

删除一个bucket可以通过delete_bucket方法实现。

    c.delete_bucket(bucket_name)

如果bucket下面存在key，那么需要首先删除所有key

    b = c.get_bucket(bucket_name)
    for k in b.list():
        k.delete()
    c.delete_bucket(bucket_name)

####Get Bucket ACL:

*获取Bucket的ACL*

    acp = b.get_acl()
    >>> acp
    <Policy: MTM1OTk4ODE= (owner) = FULL_CONTROL>
    >>> acp.acl
    <ks3.acl.ACL object at 0x23cf750>
    >>> acp.acl.grants
    [<ks3.acl.Grant object at 0xf63810>]
    >>> for grant in acp.acl.grants:
    ...   print grant.permission, grant.display_name, grant.email_address, grant.id
    ...

####Put Bucket ACL:

*设置Bucket的ACL
  
    //设置bucket的权限
    b.set_acl("public-read")

###Object操作

####Get Object：
*下载该Object数据*
 
下载object，并且作为字符串返回

    from ks3.connection import Connection
     
    bucket_name = "YOUR_BUCKET_NAME"
    key_name = "YOUR_KEY_NAME"
    b = c.get_bucket(bucket_name)
    k = b.get_key(key_name)
    s = k.get_contents_as_string()
    print s

下载object，并且保存到文件中

    k.get_contents_to_filename("/root/KS3SDK_download_test")

####Put Oobject
*上传Object数据* 

将指定目录的文件上传

    bucket_name = "YOUR_BUCKET_NAME"
    key_name = "YOUR_KEY_NAME"
     
    b = c.get_bucket(bucket_name)
    k = b.new_key(key_name)
    k.set_contents_from_filename("/root/KS3SDK_upload_test")

将字符串所谓value上传

    k.set_contents_from_string('This is a test of S3')

####List Oobject
*列举Bucket内的Object*

    b = c.get_bucket(bucket_name)
    keys = b.list()

*列举Bucket内的目录*

    from ks3.prefix import Prefix
    from ks3.key import Key

    b = c.get_bucket(bucket_name)
    keys = b.list(delimiter='/')
    for k in keys:
        if isinstance(k,Key):
            print 'file:%s' % k.name
        elif isinstance(k,Prefix):
            print 'dir:%s' % k.name

####Get Object ACL
*获得Object的acl*

    b = c.get_bucket(bucket_name)
    policy = b.get_acl(key_name)
    print policy.to_xml()

####Put Object ACL

    b.set_acl("public-read", test_key)

####Upload Part：
*分块上传*

如果你想上传一个大文件，你可以将它分成几个小份，逐个上传，s3会按照顺序把它们合成一个最终的object。整个过程需要几步来完成，下面的demo程序是通过python的FileChunkIO模块来实现的。所以可能需要首先运行pip install FileChunkIO来安装。

    >>> import math, os
    >>> from ks3.connection import Connection
    >>> from filechunkio import FileChunkIO
     
    # Connect to S3
    >>> bucket_name = "YOUR_BUCKET_NAME"
    >>> c = Connection(ak, sk)
    >>> b = c.get_bucket(bucket_name)
     
    # Get file info
    >>> source_path = 'path/to/your/file.ext'
    >>> source_size = os.stat(source_path).st_size
     
    # Create a multipart upload request
    >>> mp = b.initiate_multipart_upload(os.path.basename(source_path))
     
    # Use a chunk size of 50 MiB (feel free to change this)
    >>> chunk_size = 52428800
    >>> chunk_count = int(math.ceil(source_size / chunk_size))
     
    # Send the file parts, using FileChunkIO to create a file-like object
    # that points to a certain byte range within the original file. We
    # set bytes to never exceed the original file size.
    >>> for i in range(chunk_count + 1):
    >>>     offset = chunk_size * i
    >>>     bytes = min(chunk_size, source_size - offset)
    >>>     with FileChunkIO(source_path, 'r', offset=offset,
                             bytes=bytes) as fp:
    >>>         mp.upload_part_from_file(fp, part_num=i + 1)
     
    # Finish the upload
    >>> mp.complete_upload()
