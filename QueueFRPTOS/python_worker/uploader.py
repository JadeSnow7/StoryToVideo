# remote/python_worker/tos_uploader.py
import os
import boto3
from datetime import datetime
from dotenv import load_dotenv 
from pathlib import Path
env_path = Path(__file__).parent / '.env'
env_path = Path(__file__).parent / '.env'
load_dotenv(env_path)
class TosUploader:
    def __init__(self):
        # 建议从环境变量读取，为了测试方便这里先写死或留空
        self.ak = os.getenv("ACCESS_KEY")
        self.sk = os.getenv("SECRET_KEY")
        self.endpoint = os.getenv("ENDPOINT")
        self.bucket = os.getenv("TOS_BUCKET")

        try:
            self.s3 = boto3.client(
            's3',
            aws_access_key_id=self.ak,
            aws_secret_access_key=self.sk,
            endpoint_url=self.endpoint,
        )
            print(f"S3 Client initialized. Endpoint: {self.endpoint}")
        except Exception as e:
            print(f"Failed to init TOS client: {e}")
            self.s3 = None

    def upload_file(self, local_path, object_key=None):
        """
        上传文件并返回可访问的 URL
        :param local_path: 本地文件路径
        :param object_key: 云端存储的路径（文件名），如果不传则自动生成
        :return: 公网访问 URL
        """
        if not self.s3:
            raise Exception("TOS client is not initialized")

        if not object_key:
            # 如果没指定文件名，用日期+文件名自动生成，避免冲突
            filename = os.path.basename(local_path)
            date_folder = datetime.now().strftime("%Y%m%d")
            object_key = f"storyboard/{date_folder}/{filename}"

        try:#上传文件
            with open(local_path, 'rb') as f:
                self.s3.upload_fileobj(
                    f,
                    self.bucket,
                    object_key,
                )
            
            # 构造返回 URL
            # 注意：如果 Bucket 是私有读，这里需要生成带签名的 URL
            # 如果是公共读，直接拼接即可
            # 格式: https://{bucket}.{endpoint}/{key}
            # url = f"{self.endpoint}/{self.bucket}/{object_key}"
            # print(f"Uploaded to {url}")
            # return url
            url = self.s3.generate_presigned_url(
            'get_object',
                Params={'Bucket': self.bucket, 'Key': object_key},
            ExpiresIn=3600
            )
            print("下载链接:", url)
            return url
        
        except FileNotFoundError:
            print("The file was not found")
            return ""
        except Exception as e:
            print(f"Upload failed: {e}")
            return ""