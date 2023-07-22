import io
import os
import re

from google.oauth2 import service_account
from googleapiclient.discovery import build
from googleapiclient.http import MediaIoBaseDownload
from loguru import logger

from config import google_sticker_path1, sticker_path1, google_sticker_path2, sticker_path2, sticker_path3, \
    google_sticker_path3, sticker_path_all
from utils import ProgressBar


def get_all_files_in_folder(service, folder_url: str) -> list:
    """Get the list of files in a folder on Google Drive."""
    folder_id = re.search(r'/folders/([^/]+)', folder_url).group(1)
    files = []

    query = f"'{folder_id}' in parents"
    page_token = None
    while True:
        results = service.files().list(q=query, fields="nextPageToken, files(id, name)", pageSize=1000,
                                       pageToken=page_token).execute()
        items = results.get('files', [])
        page_token = results.get('nextPageToken')
        if items:
            files.extend(items)
        if page_token is None:
            break
    return files


def compare_files_with_local_directory(service, folder_url: str, local_directory: str) -> list:
    """Compare files on Google Drive and local directory."""
    folder_id = re.search(r'/folders/([^/]+)', folder_url).group(1)

    # Get the list of files on Google Drive
    query = f"'{folder_id}' in parents"
    page_token = None
    drive_files = []
    while True:
        results = service.files().list(q=query, fields="nextPageToken, files(id, name)", pageSize=1000,
                                       pageToken=page_token).execute()
        items = results.get('files', [])
        page_token = results.get('nextPageToken')
        if items:
            drive_files.extend(items)
        if page_token is None:
            break

    # Get the list of files in the local directory
    local_files = []
    for root, dirs, files in os.walk(local_directory):
        for file in files:
            local_files.append(file)

    # Compare the lists of files
    missing_files = []
    for drive_file in drive_files:
        drive_file_name = drive_file['name']
        if drive_file_name not in local_files:
            missing_files.append(drive_file_name)

    return missing_files


def download_file(service, file_id: str, file_name: str, local_directory: str):
    """Download a file from Google Drive."""
    request = service.files().get_media(fileId=file_id)
    fh = io.BytesIO()
    downloader = MediaIoBaseDownload(fh, request)
    done = False
    try:
        while not done:
            status, done = downloader.next_chunk()
            logger.info(f"Download {file_name}: {int(status.progress() * 100)}%")
    except Exception as e:
        logger.error(f"Failed to download {file_name}: {str(e)}")
        return False

    # Save the downloaded file to the local directory
    file_path = os.path.join(local_directory, file_name)
    with open(file_path, 'wb') as f:
        f.write(fh.getbuffer())
    logger.success(f"Downloaded {file_name} successfully.")
    return True


def download_missing_files_from_drive(folder_url: str, local_directory: str):
    """Download missing files from Google Drive to the specified local directory."""
    # Authenticate and create the Drive service
    credentials = service_account.Credentials.from_service_account_file('google_acc.json')
    service = build('drive', 'v3', credentials=credentials, static_discovery=False)

    # Get the list of missing files
    missing_files = compare_files_with_local_directory(service, folder_url, local_directory)

    if len(missing_files) == 0:
        logger.success('No new stickers found on Google Drive.')
        return

    logger.success(f'Number of new stickers on Google Drive: {len(missing_files)}')
    logger.success(f'List of new stickers: {missing_files}')

    # Get folder_id
    folder_id = re.search(r'/folders/([^/]+)', folder_url).group(1)

    # Download missing files from Google Drive
    for missing_file_name in missing_files:
        escaped_file_name = missing_file_name.replace("'", "\\'")
        query = f"'{folder_id}' in parents and name='{escaped_file_name}'"
        file_id = None
        page_token = None
        while True:
            results = service.files().list(q=query, fields="nextPageToken, files(id)", pageSize=1000,
                                           pageToken=page_token).execute()
            items = results.get('files', [])
            page_token = results.get('nextPageToken')
            if items:
                file_id = items[0]['id']
            if page_token is None or file_id is not None:
                break

        if file_id:
            download_file(service, file_id, missing_file_name, local_directory)
        else:
            logger.error(f"File '{missing_file_name}' not found on Google Drive.")


def main_download_stickers(self=None):
    sticker_paths = [
        (google_sticker_path1, sticker_path1),
        (google_sticker_path2, sticker_path2),
        (google_sticker_path3, sticker_path3)
    ]
    if self:
        self.second_statusbar.showMessage(f'Скачивание стикеров', 100000)
        progress = ProgressBar(3, self)
    for google_sticker_path, sticker_path in sticker_paths:
        folder_url = f"https://drive.google.com/drive/folders/{google_sticker_path}"
        local_directory = f"{sticker_path_all}"
        download_missing_files_from_drive(folder_url, local_directory)
        if self:
            progress.update_progress()
    if self:
        self.second_statusbar.showMessage(f'Скачивание стикеров завершено', 1000)


if __name__ == '__main__':
    main_download_stickers()
