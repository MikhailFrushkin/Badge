import datetime
import os

import cv2
import numpy as np
from loguru import logger

from base.db import Article
from config import all_badge


def blur_image(image_path, output_path, size_b):
    data_b = {
        25: 1.40,
        37: 1.30,
        44: 1.18,
        56: 1.14,
    }
    original_image = cv2.imread(image_path)
    try:
        # Получите размеры изображения
        height, width, _ = original_image.shape

        # Создайте чистый холст для результата
        result_image = np.full_like(original_image, (255, 255, 255), dtype=np.uint8)

        # Вычислите координаты центра и радиус круга
        center_x = width // 2
        center_y = height // 2
        radius = min(center_x, center_y) - 5

        # Создайте маску круга
        mask = np.zeros((height, width), dtype=np.uint8)
        cv2.circle(mask, (center_x, center_y), radius, (255, 255, 255), -1)

        # Примените маску к исходному изображению
        result_image[mask > 0] = original_image[mask > 0]

        # Примените размытие к круговой области
        blurred_circle = cv2.GaussianBlur(
            result_image, (71, 71), 30
        )  # Измените параметры размытия по вашему усмотрению

        # Создайте круговую маску для result_image
        circle_mask = np.zeros(
            (result_image.shape[0], result_image.shape[1]), dtype=np.uint8
        )
        cv2.circle(
            circle_mask,
            (result_image.shape[1] // 2, result_image.shape[0] // 2),
            radius,
            (255),
            -1,
        )

        # Вычислите новые размеры увеличенного изображения
        new_height = int(result_image.shape[0] * data_b[size_b])
        new_width = int(result_image.shape[1] * data_b[size_b])

        # Увеличьте изображение с размытым кругом
        enlarged_result = cv2.resize(
            blurred_circle, (new_width, new_height), interpolation=cv2.INTER_LINEAR
        )

        # Вычислите смещение для вставки увеличенного изображения с размытым кругом
        offset_y = (enlarged_result.shape[0] - result_image.shape[0]) // 2
        offset_x = (enlarged_result.shape[1] - result_image.shape[1]) // 2

        # Вставьте увеличенное изображение с размытым кругом в общий результат
        enlarged_result[
            offset_y : offset_y + result_image.shape[0],
            offset_x : offset_x + result_image.shape[1],
        ] = np.where(
            circle_mask[:, :, None] > 0,
            result_image,
            enlarged_result[
                offset_y : offset_y + result_image.shape[0],
                offset_x : offset_x + result_image.shape[1],
            ],
        )

        # Сохраните увеличенное изображение с размытым кругом

        cv2.imwrite(output_path, enlarged_result)

        # logger.debug(f"Изображение сохранено в: {output_path}")
    except Exception as e:
        logger.error(f"Ошибка создания файла: {image_path} {e}")
    return True


def main(file, size_b):
    start = datetime.datetime.now()
    with open(file, "r") as f:
        data = f.read()
    art_list = data.split("\n")
    query = Article.select().where((Article.size == size_b) & (Article.art << art_list))

    results = query.execute()
    count = 0
    list_db = []
    for article in results:
        count += 1
        list_db.append(article.art)
        folder_name = article.folder
        for index, filename in enumerate(os.listdir(folder_name), start=1):
            if (
                filename.startswith("!") or filename[0].strip().isdigit()
            ) and os.path.isfile(os.path.join(folder_name, filename)):
                if os.path.exists(os.path.join(folder_name, filename)):
                    try:
                        blur_image(
                            image_path=os.path.join(folder_name, filename),
                            output_path=os.path.join(folder_name, filename),
                            size_b=size_b,
                        )
                    except Exception as ex:
                        logger.error(ex)
                        logger.error(os.path.join(folder_name, filename))

    logger.debug("Время: ", start - datetime.datetime.now())


def blur_size(size, directory=None):
    if not directory:
        directory = rf"{all_badge}\сделать\{size}"
    os.makedirs(directory, exist_ok=True)
    for i in os.listdir(directory):
        folder_name = os.path.join(directory, i)
        for index, filename in enumerate(os.listdir(folder_name), start=1):
            if (
                filename.split(".")[0].startswith("!")
                or filename.split(".")[0].strip().isdigit()
            ) and os.path.isfile(os.path.join(folder_name, filename)):
                if os.path.exists(os.path.join(folder_name, filename)):
                    try:
                        blur_image(
                            image_path=os.path.join(folder_name, filename),
                            output_path=os.path.join(folder_name, filename),
                            size_b=size,
                        )
                    except Exception as ex:
                        logger.error(ex)
                        logger.error(os.path.join(folder_name, filename))


def blur_one_folder(size, folder):
    for index, filename in enumerate(os.listdir(folder), start=1):
        if (
            filename.split(".")[0].startswith("!")
            or filename.split(".")[0].strip().isdigit()
        ) and os.path.isfile(os.path.join(folder, filename)):
            if os.path.exists(os.path.join(folder, filename)):
                try:
                    blur_image(
                        image_path=os.path.join(folder, filename),
                        output_path=os.path.join(folder, filename),
                        size_b=size,
                    )
                except Exception as ex:
                    logger.error(ex)
                    logger.error(os.path.join(folder, filename))


if __name__ == "__main__":
    image_path = r"G:\База значков\AniKoya\ADVENT-UV-BLAG.NEBOZHITELEY\1.png"
    output_path = r"G:\База значков\AniKoya\ADVENT-UV-BLAG.NEBOZHITELEY\1111.png"
    size_b = 37
    blur_image(image_path, output_path, size_b)
