
import boto3
import os
from .dirUtils import unzip_file
from .logger import get_logger

class S3Helper:
    def __init__(self, aws_access_key : str, aws_secret_key : str, aws_region : str) -> None:
        self.s3 = boto3.client("s3", 
                               aws_access_key_id = aws_access_key,
                               aws_secret_access_key = aws_secret_key,
                               region_name = aws_region)
        self.logger = get_logger("S3Helper")
        
    def download_zip_file(self, bucket_name : str, s3_key : str, local_file_path : str, extract_folder : str):
        try:
            self.s3.download_file(bucket_name, s3_key, local_file_path)
            if not os.path.exists(local_file_path):
                raise FileNotFoundError("Error during file download")
            unzip_file(local_file_path, extract_folder)
            return extract_folder
        except Exception as e:
            self.logger.error(str(e))
            raise e
        
    def download_file(self, bucket_name : str, s3_key : str, local_file_path : str):
        try:
            self.s3.download_file(bucket_name, s3_key, local_file_path)
        except Exception as e:
            self.logger.error(e)
            raise e 

    def upload_file(self, filename, key, bucket_name):
        try:
            self.s3.upload_file(filename, bucket_name, key)
        except Exception as e:
            self.logger.error(e)
            raise e 

    def upload_original_audio(self, file_path, bucket_name):
        try:
            filename = file_path.split('/')[-1]
            s3_key = f"files/{filename}"
            self.s3.upload_file(file_path, bucket_name, s3_key)
            return s3_key
        except Exception as e:
            self.logger.error(e)
            return ''
