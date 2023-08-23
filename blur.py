import datetime
import os

import cv2
import numpy as np
from loguru import logger
from peewee import *

from db import Article

db = SqliteDatabase('mydatabase.db')


class Article(Model):
    art = CharField(null=True, index=True)
    folder = CharField(null=True)
    nums = IntegerField(null=True)
    nums_in_folder = IntegerField(null=True)
    size = IntegerField(null=True)
    skin = CharField(null=True)
    sticker = CharField(null=True)
    images = TextField(null=True)
    shop = CharField(null=True)
    created_at = DateTimeField(default=datetime.datetime.now)

    class Meta:
        database = db

    def __str__(self):
        return self.art


def blur_image(image_path, output_path, size_b):
    data_b = {
        25: 1.40,
        37: 1.29,
        44: 1.18,
        56: 1.13,
    }
    # Открываем изображение
    original_image = cv2.imread(image_path)

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
    blurred_circle = cv2.GaussianBlur(result_image, (71, 71), 30)  # Измените параметры размытия по вашему усмотрению

    # Создайте круговую маску для result_image
    circle_mask = np.zeros((result_image.shape[0], result_image.shape[1]), dtype=np.uint8)
    cv2.circle(circle_mask, (result_image.shape[1] // 2, result_image.shape[0] // 2), radius, (255), -1)

    # Вычислите новые размеры увеличенного изображения
    new_height = int(result_image.shape[0] * data_b[size_b])
    new_width = int(result_image.shape[1] * data_b[size_b])

    # Увеличьте изображение с размытым кругом
    enlarged_result = cv2.resize(blurred_circle, (new_width, new_height), interpolation=cv2.INTER_LINEAR)

    # Вычислите смещение для вставки увеличенного изображения с размытым кругом
    offset_y = (enlarged_result.shape[0] - result_image.shape[0]) // 2
    offset_x = (enlarged_result.shape[1] - result_image.shape[1]) // 2

    # Вставьте увеличенное изображение с размытым кругом в общий результат
    enlarged_result[offset_y:offset_y + result_image.shape[0], offset_x:offset_x + result_image.shape[1]] = \
        np.where(circle_mask[:, :, None] > 0, result_image,
                 enlarged_result[offset_y:offset_y + result_image.shape[0], offset_x:offset_x + result_image.shape[1]])

    # Сохраните увеличенное изображение с размытым кругом

    cv2.imwrite(output_path, enlarged_result)

    print(f"Изображение сохранено в: {output_path}")


def main(file, size_b):
    start = datetime.datetime.now()
    with open(file, 'r') as f:
        data = f.read()
    art_list = data.split('\n')
    print(len(art_list))
    query = (Article
             .select()
             .where((Article.size == size_b) & ~(Article.art << art_list)))

    results = query.execute()
    count = 0
    list_db = []
    for article in results:
        count += 1
        print(count, article.art)
        list_db.append(article.art)
        folder_name = article.folder
        for index, filename in enumerate(os.listdir(folder_name), start=1):
            if (filename.split('.')[0].startswith('!') or filename.split('.')[0].isdigit()) \
                    and os.path.isfile(os.path.join(folder_name, filename)):
                if os.path.exists(os.path.join(folder_name, filename)):
                    try:
                        blur_image(image_path=os.path.join(folder_name, filename),
                                   output_path=os.path.join(folder_name, filename), size_b=size_b)
                    except Exception as ex:
                        logger.error(ex)
                        logger.error(os.path.join(folder_name, filename))
    print('Время: ', start - datetime.datetime.now())


if __name__ == '__main__':
    # main(file='да25.txt', size_b=25)
    # main(file='да37.txt', size_b=37)
    # main(file='да44.txt', size_b=44)
    main(file='да56.txt', size_b=56)

    # folder_name = r'E:\test\Новая папка'
    # for index, filename in enumerate(os.listdir(folder_name), start=1):
    #     if (filename.split('.')[0].startswith('!') or filename.split('.')[0].isdigit()) \
    #             and os.path.isfile(os.path.join(folder_name, filename)):
    #         if os.path.exists(os.path.join(folder_name, filename)):
    #             try:
    #                 blur_image(image_path=os.path.join(folder_name, filename),
    #                            output_path=os.path.join(folder_name, filename), size_b=56)
    #             except Exception as ex:
    #                 logger.error(ex)
    #                 logger.error(os.path.join(folder_name, filename))
