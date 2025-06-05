import logging
from fastapi import UploadFile
from services.code_conversion_service import (
    handle_upload_and_migration, get_file_response, get_project_zip_response, process_uploaded_file
)

logger = logging.getLogger(__name__)
logging.basicConfig(level=logging.INFO)

async def upload_files_controller(file: UploadFile, code_language: str, fro_version: str, to_version: str):
    logger.info("Controller: upload_files_controller called for %s", file.filename)
    filename = file.filename.lower()
    if filename.endswith('.zip'):
        logger.info("File is a zip archive.")
        return await process_uploaded_file(file, code_language, fro_version, to_version, is_zip=True)
    else:
        logger.info("File is a single code file.")
        return await process_uploaded_file(file, code_language, fro_version, to_version, is_zip=False)

def download_file_controller(filename):
    return get_file_response(filename)

def download_project_zip_controller(filename):
    return get_project_zip_response(filename)
