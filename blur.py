import os

import cv2
import numpy as np


def blur_image(image_path, output_path):
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
    blurred_circle = cv2.GaussianBlur(result_image, (55, 55), 25)  # Измените параметры размытия по вашему усмотрению

    # Создайте круговую маску для result_image
    circle_mask = np.zeros((result_image.shape[0], result_image.shape[1]), dtype=np.uint8)
    cv2.circle(circle_mask, (result_image.shape[1] // 2, result_image.shape[0] // 2), radius, (255), -1)

    # Вычислите новые размеры увеличенного изображения
    new_height = int(result_image.shape[0] * 1.2)
    new_width = int(result_image.shape[1] * 1.2)

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

    print(f"Увеличенное изображение сохранено в: {output_path}")


if __name__ == '__main__':
    folder_name = r'E:\test\2PAC-11NEW-6-56'
    for index, filename in enumerate(os.listdir(folder_name), start=1):
        if (filename.split('.')[0].startswith('!') or filename.split('.')[0].isdigit()) \
                and os.path.isfile(os.path.join(folder_name, filename)):
            blur_image(image_path=os.path.join(folder_name, filename),
                       output_path=os.path.join(folder_name, '!' + filename))
