import logging
from services.migration_agent import run_migration_agent
from utils.file_utils import save_uploads, prepare_download_links, zip_downloads, get_file_from_downloads
from models.migration import MigrationResult
from fastapi.responses import JSONResponse
from fastapi.responses import StreamingResponse
import shutil
from pathlib import Path
import zipfile
import io
from fastapi import UploadFile
import os
import uuid

# Configure logger
logger = logging.getLogger(__name__)
logging.basicConfig(level=logging.INFO)

async def handle_upload_and_migration(files, code_language, fro_version, to_version):
    logger.info("Starting upload and migration for %d file(s)", len(files))
    uploads_dir, downloads_dir = save_uploads(files)
    migration_summary, download_links = await run_migration_agent(
        uploads_dir, downloads_dir, code_language, fro_version, to_version
    )
    zip_downloads(downloads_dir, str(files[0].filename))
    logger.info("Migration and zipping complete for %s", files[0].filename)
    return {
        "summary": migration_summary,
        "download_links": download_links,
        "project_zip_link": "/api/download_project_zip"
    }

def get_file_response(filename):
    logger.info("Fetching file: %s", filename)
    file_response = get_file_from_downloads(filename)
    if not file_response:
        logger.warning("File not found: %s", filename)
        return JSONResponse(status_code=404, content={"error": "File not found"})
    return file_response

def get_project_zip_response(filename):
    downloads_dir = Path(__file__).parent.parent / "resources/downloads"
    zip_path = downloads_dir / f"{filename}.zip"
    if zip_path.exists():
        zip_path.unlink()
    shutil.make_archive(str(zip_path.with_suffix('')), 'zip', str(downloads_dir))
    logger.info("Project zip created: %s", zip_path)
    zip_file = open(zip_path, "rb")
    return StreamingResponse(zip_file, media_type="application/zip", headers={"Content-Disposition": f"attachment; filename={filename}.zip"})

async def process_uploaded_file(file: UploadFile, code_language: str, fro_version: str, to_version: str, is_zip: bool):
    job_id = str(uuid.uuid4())
    uploads_dir = Path(__file__).parent.parent / "resources/uploads" / job_id
    downloads_dir = Path(__file__).parent.parent / "resources/downloads" / job_id
    uploads_dir.mkdir(parents=True, exist_ok=True)
    downloads_dir.mkdir(parents=True, exist_ok=True)
    logger.info("Processing upload: %s (zip: %s)", file.filename, is_zip)

    if is_zip:
        contents = await file.read()
        with zipfile.ZipFile(io.BytesIO(contents)) as zip_ref:
            zip_ref.extractall(uploads_dir)
        logger.info("Extracted zip file to %s", uploads_dir)
    else:
        file_path = uploads_dir / file.filename
        with open(file_path, "wb") as f:
            f.write(await file.read())
        logger.info("Saved file to %s", file_path)

    migration_summary, download_links = await run_migration_agent(
        str(uploads_dir), str(downloads_dir), code_language, fro_version, to_version
    )
    zip_downloads(str(downloads_dir), str(file.filename))
    logger.info("Migration and zipping complete for %s", file.filename)
    return {
        "summary": migration_summary,
        "download_links": download_links,
        "project_zip_link": f"/api/download_project_zip?filename={file.filename}"
    }
