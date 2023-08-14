import asyncio
import os
import re

import aiohttp
from google.oauth2 import service_account
from googleapiclient.discovery import build
from loguru import logger

from config import google_sticker_path1, sticker_path1, google_sticker_path2, sticker_path2, sticker_path3, \
    google_sticker_path3, sticker_path_all
from utils import ProgressBar


async def download_file(session, url, file_name, local_directory):
    """Download a file asynchronously using aiohttp."""
    async with session.get(url) as response:
        if response.status == 200:
            file_path = os.path.join(local_directory, file_name)
            with open(file_path, 'wb') as f:
                while True:
                    chunk = await response.content.read(1024)
                    if not chunk:
                        break
                    f.write(chunk)
            logger.success(f"Downloaded {file_name} successfully.")
            return True
        else:
            logger.error(f"Failed to download {file_name}: Status code {response.status}")
            return False


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
        if drive_file_name.endswith('.pdf') and drive_file_name not in local_files:
            missing_files.append(drive_file_name)

    return missing_files


async def download_missing_files_from_drive(folder_url: str, local_directory: str, self=None):
    """Download missing files from Google Drive to the specified local directory asynchronously."""
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
    if self:
        self.second_statusbar.showMessage(f'Скачивание стикеров', 100000)
        progress = ProgressBar(len(missing_files), self)

    # Download missing files from Google Drive asynchronously
    async with aiohttp.ClientSession() as session:
        tasks = []
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
                if self:
                    progress.update_progress()
                download_url = f"https://drive.google.com/uc?id={file_id}"
                tasks.append(download_file(session, download_url, missing_file_name, local_directory))
            else:
                logger.error(f"File '{missing_file_name}' not found on Google Drive.")

        await asyncio.gather(*tasks)


def main_download_stickers(self=None):
    sticker_paths = [
        (google_sticker_path1, sticker_path1),
        (google_sticker_path2, sticker_path2),
        (google_sticker_path3, sticker_path3)
    ]

    for google_sticker_path, sticker_path in sticker_paths:
        folder_url = f"https://drive.google.com/drive/folders/{google_sticker_path}"
        local_directory = f"{sticker_path_all}"
        asyncio.run(download_missing_files_from_drive(folder_url, local_directory, self))

    if self:
        self.second_statusbar.showMessage(f'Скачивание стикеров завершено', 1000)


if __name__ == '__main__':
    main_download_stickers()
