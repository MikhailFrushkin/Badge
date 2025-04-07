import os
import shutil

import cv2
import numpy as np
from loguru import logger


def delete_files_except_matching_folders(directory):
    files = os.listdir(directory)
    for file_name in files:
        file_path = os.path.join(directory, file_name)
        if os.path.isfile(file_path):
            file_name_lower = file_name.lower()
            file_base_name, file_ext = os.path.splitext(file_name_lower)
            if file_ext in ['.jpg', '.png'] and file_base_name in [folder.lower() for folder in os.listdir(directory) if
                                                                   os.path.isdir(os.path.join(directory, folder))]:
                continue
            os.remove(file_path)


def delete_empty_folders(directory):
    count = 0
    for i in os.listdir(directory):
        if os.path.isfile(os.path.join(directory, i)):
            count += 1
    if count == 0:
        shutil.rmtree(directory)


def rename_files(directory):
    files = os.listdir(directory)
    for i, file_name in enumerate(files, start=1):
        file_ext = os.path.splitext(file_name)[1]
        new_file_name = f"{i}{file_ext}"
        old_file_path = os.path.join(directory, file_name)
        new_file_path = os.path.join(directory, new_file_name)
        os.rename(old_file_path, new_file_path)


def circle_one_image(file_paths):
    output_folder = os.path.join(os.path.dirname(file_paths[0]), "По отдельности")

    for index, file_path in enumerate(file_paths, start=1):
        image = cv2.imread(file_path)
        gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
        gray = cv2.GaussianBlur(gray, (5, 5), 0)
        # Детекция кругов на изображении
        circles = cv2.HoughCircles(gray, cv2.HOUGH_GRADIENT, 1, minDist=410,
                                   param1=110, param2=70, minRadius=300, maxRadius=430)
        if circles is not None:
            # Округление координат и радиусов кругов
            circles = np.round(circles[0, :]).astype(int)
            # Создание папки для сохранения найденных кругов
            os.makedirs(output_folder, exist_ok=True)
            # Сохранение найденных кругов в отдельные файлы
            for i, (x, y, r) in enumerate(circles, start=1):
                print(i, (x, y, r))
                # Вырезаем найденный круг из исходного изображения с добавлением отступа
                padding = 0  # Размер отступа в пикселях (можно настроить по необходимости)
                x_min = max(x - r - padding, 0)
                x_max = min(x + r + padding, image.shape[1])
                y_min = max(y - r - padding, 0)
                y_max = min(y + r + padding, image.shape[0])
                circle_img = image[y_min:y_max, x_min:x_max]
                # Сохраняем круг в файл
                cv2.imwrite(os.path.join(output_folder, f'{index}{i}{i}.png'), circle_img)

            print(f'{len(circles)} кругов сохранены в папке {output_folder}.')
        else:
            with open('bad.txt', 'a') as f:
                f.write(f"{file_paths}\n")
            print("Круги не найдены на изображении.")
    try:
        rename_files(output_folder)
    except Exception as ex:
        logger.error(f'Не удалось переименовать файлы в {output_folder}')
