
import os
import subprocess
import shutil
import requests
from io import BytesIO
import zipfile


def download_and_unzip_open_s3_obj(object_url, destination_file):
    print(f"Downloading from {object_url}")
    response = requests.get(object_url)

    if response.status_code == 200:
        with zipfile.ZipFile(BytesIO(response.content)) as zip_file:
            zip_file.extractall(destination_file)

        print(f"Download successful. Object saved to: {destination_file}")
    else:
        print(f"Failed to download. Status code: {response.status_code}")
        raise Exception(f"Failed to download dataset!!")

def copy_file_to_folder(input_filepath, output_folder):
    """
    Copies a file from the input file path to the specified output folder.

    Args:
        input_filepath (str): The path to the input file to be copied.
        output_folder (str): The folder where the file should be copied to.
    """
    try:
        # Ensure the output folder exists
        os.makedirs(output_folder, exist_ok=True)
        
        # Extract the filename from the input filepath
        filename = os.path.basename(input_filepath)
        
        # Define the output filepath
        output_filepath = os.path.join(output_folder, filename)
        
        # Copy the file to the output folder
        shutil.copy(input_filepath, output_filepath)
        
        print(f"File copied successfully to {output_filepath}")
    except Exception as e:
        print(f"Error copying file: {e}")
        raise e    

def unzip_file(zip_file_path, extract_to_path):
    with zipfile.ZipFile(zip_file_path, 'r') as zip_ref:
        zip_ref.extractall(extract_to_path)

def zip_folder(folder_path, zip_filepath):
    try:
        shutil.make_archive(base_name=zip_filepath.replace('.zip', ''), format='zip', root_dir=folder_path)
    except Exception as e:
        print(f"Error : {e} during logs zipping")
        return False
