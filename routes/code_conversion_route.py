from fastapi import APIRouter, UploadFile, File, Form
from controllers.code_conversion_controller import (
    upload_files_controller, download_file_controller, download_project_zip_controller
)
import logging

logger = logging.getLogger(__name__)
logging.basicConfig(level=logging.INFO)

router = APIRouter()

@router.post("/upload_files")
async def upload_files(
    file: UploadFile = File(...),
    code_language: str = Form(...),
    fro_version: str = Form(...),
    to_version: str = Form(...)
):
    logger.info("Received upload_files request: %s", file.filename)
    return await upload_files_controller(file, code_language, fro_version, to_version)

@router.get("/download/{filename:path}")
def download_file(filename: str):
    logger.info("Download file requested: %s", filename)
    return download_file_controller(filename)

@router.get("/download_project_zip/{filename:path}")
def download_project_zip(filename: str):
    logger.info("Download project zip requested: %s", filename)
    return download_project_zip_controller(filename)
