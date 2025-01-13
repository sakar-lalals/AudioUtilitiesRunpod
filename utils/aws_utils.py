import os

import boto3
import botocore
from .logger import get_logger

from .exceptions import AWSAccessKeyNotExistsException, AWSSecretKeyNotExistsException


class S3Helper:
    def __init__(self, AWS_ACCESS_KEY : str, AWS_SECRET_KEY : str, region_name : str) -> None:
        self.s3 = boto3.client("s3", 
                            aws_access_key_id = AWS_ACCESS_KEY, 
                            aws_secret_access_key = AWS_SECRET_KEY,
                            region_name = region_name
                            )

        self.logger = get_logger("S3Helper")
    
    def get_file(self, file_path, bucket_name : str = 'lalals'):
        try:
            s3_obj =  self.s3.get_object(Bucket = bucket_name, Key = file_path)
            return s3_obj
        except Exception as e:
            self.logger.exception(e)
            raise e
    
    def download_file(self, file_path_s3 : str, file_path_local : str, bucket_name : str = "lalals"):
        try:
            self.s3.download_file(bucket_name, file_path_s3, file_path_local)
        except Exception as e:
            self.logger.exception(e)
            raise e
    
    def upload_file(self, file_path_local : str, file_path_s3 : str, bucket_name : str = "lalals"):
        try:
            self.s3.upload_file(file_path_local, bucket_name, file_path_s3)
            return file_path_s3
        except Exception as e:
            self.logger.exception(e)
            raise e
    
    def delete_file(self, s3_path : str, bucket_name : str = "lalals"):
        try:
            self.s3.delete_object(Bucket = bucket_name, Key = s3_path)
            return True
        except Exception as e:
            self.logger.error(e)
            return False

    def upload_original_audio(self, file_path, bucket_name):
        try:
            filename = file_path.split('/')[-1]
            s3_key = f"files/{filename}"
            self.s3.upload_file(file_path, bucket_name, s3_key)
            return s3_key
        except Exception as e:
            self.logger.error(e)
            return ''

    
    def validate_file_exists(self, file_key, bucket_name):
        try:
            self.s3.head_object(Bucket=bucket_name, Key=file_key)
            return True  # File exists
        except botocore.exceptions.ClientError as e:
            self.logger.error(e)
            if e.response['Error']['Code'] == '404':
                return False  # File does not exist
            else:
                self.logger.error(e)
                return False  # Other error occurred
    
    def validate_folder_exists(self, folder_path, bucket_name):
        """
        Validate if a folder path exists in an S3 bucket.
        
        :param folder_path: The folder path to check (e.g., 'folder/subfolder/')
        :param bucket_name: The name of the S3 bucket
        :return: True if the folder path exists, False otherwise
        """
        try:
            response = self.s3.list_objects_v2(Bucket=bucket_name, Prefix=folder_path, MaxKeys=1)
            if 'Contents' in response:
                return True  # Folder path exists (at least one object with this prefix)
            else:
                return False  # Folder path does not exist (no objects with this prefix)
        except botocore.exceptions.ClientError as e:
            self.logger.error(e)
            return False    


def fetch_and_validate_access_keys() -> tuple[str, str, str]:
    """
    Fetch the aws access keys from environment
    """
    try:
        AWS_ACCESS_KEY = os.getenv("aws_access_key")
        AWS_SECRET_KEY = os.getenv("aws_secret_key")
        AWS_REGION = os.getenv("aws_region", "us-east-1")

        if not AWS_ACCESS_KEY:
            raise AWSAccessKeyNotExistsException()
        if not AWS_SECRET_KEY:
            raise AWSSecretKeyNotExistsException()
        
        return AWS_ACCESS_KEY, AWS_SECRET_KEY, AWS_REGION
    except Exception as e:
        raise e


def initialize_s3() -> S3Helper:
    """
    Initializes S3Helper
    Also returns the default aws bucket name listed in env
    """
    aws_access_key, aws_secret_key, aws_region = fetch_and_validate_access_keys()
    s3Helper = S3Helper(aws_access_key, aws_secret_key, aws_region)
    return s3Helper

def get_bucket_name() -> str:
    """
    Fetch default bucket name from environment
    """
    AWS_BUCKET_NAME = os.getenv("AWS_BUCKET_NAME", "lalals")
    return AWS_BUCKET_NAME


