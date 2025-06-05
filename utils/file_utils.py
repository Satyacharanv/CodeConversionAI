import os
import logging
from pathlib import Path
from fastapi.responses import FileResponse

logger = logging.getLogger(__name__)

def save_uploads(files):
    uploads_dir = Path(__file__).parent.parent / "resources/uploads"
    downloads_dir = Path(__file__).parent.parent / "resources/downloads"
    os.makedirs(uploads_dir, exist_ok=True)
    os.makedirs(downloads_dir, exist_ok=True)
    for file in files:
        file_path = uploads_dir / (file.filename.replace("\\", "/"))
        file_path.parent.mkdir(parents=True, exist_ok=True)
        content = file.file.read()
        try:
            file_path.write_text(content.decode("utf-8"))
            logger.info("Saved text file: %s", file_path)
        except Exception:
            file_path.write_bytes(content)
            logger.info("Saved binary file: %s", file_path)
    logger.info("All files saved to %s", uploads_dir)
    return str(uploads_dir), str(downloads_dir)

def prepare_download_links(downloads_dir):
    links = []
    for root, dirs, files in os.walk(downloads_dir):
        for file in files:
            rel_path = os.path.relpath(os.path.join(root, file), downloads_dir)
            rel_path_url = rel_path.replace("\\", "/")
            links.append(f"/api/download/{rel_path_url}")
    logger.info("Prepared %d download links for %s", len(links), downloads_dir)
    return links

def zip_downloads(downloads_dir, filename):
    import shutil
    downloads_dir_path = Path(downloads_dir)
    zip_path = downloads_dir_path.parent / f"{filename}.zip"
    if zip_path.exists():
        zip_path.unlink()
        logger.info("Removed existing zip: %s", zip_path)
    shutil.make_archive(str(zip_path.with_suffix('')), 'zip', str(downloads_dir_path))
    logger.info("Created zip archive: %s", zip_path)

def get_file_from_downloads(filename):
    file_path = Path(filename)
    if not file_path.exists():
        logger.warning("Requested file not found: %s", file_path)
        return None
    logger.info("Serving file from downloads: %s", file_path)
    return FileResponse(str(file_path), filename=file_path.name)
