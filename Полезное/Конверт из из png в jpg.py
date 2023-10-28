import os
from concurrent.futures import ThreadPoolExecutor

from PIL import Image, ImageDraw, ImageOps
from loguru import logger


def convert_square_to_circle(image_path, output_path, quality=95):
    try:
        image = Image.open(image_path)
        width, height = image.size
        if image.mode != 'RGBA':
            image = image.convert('RGB')

        # Радиус круга (половина стороны квадрата)
        radius = min(width, height) // 2

        # Создаем новое изображение с белым фоном
        new_image = Image.new('RGB', (radius * 2, radius * 2), (255, 255, 255, 0))

        # Создаем маску для вырезания круга
        mask = Image.new('L', (radius * 2, radius * 2), 0)
        draw = ImageDraw.Draw(mask)
        draw.ellipse((0, 0, radius * 2, radius * 2), fill=255)

        # Применяем маску к исходному изображению
        image_with_mask = ImageOps.fit(image, mask.size, centering=(0.5, 0.5))
        image_with_mask.putalpha(mask)

        new_image.paste(image_with_mask, (0, 0), image_with_mask)
        new_image.save(output_path, format='JPEG', quality=quality)
    except Exception as e:
        print(f"Произошла ошибка: {e}")


def process_image(filename):
    try:
        folder_name = r'E:\2'
        input_image_path = os.path.join(folder_name, filename)
        new_name = filename.split('.')[0] + '.jpg'

        output_image_path = os.path.join(folder_name, new_name)
        convert_square_to_circle(input_image_path, output_image_path, quality=100)
        os.remove(input_image_path)
    except Exception as ex:
        logger.error(f"Ошибка при обработке {filename}: {ex}")


if __name__ == '__main__':
    count = 0
    directory = r'E:\База значков\AniKoya'
    process_image('10.png')
    # for i in os.listdir(directory):
    #     count += 1
    #     folder_name = os.path.join(directory, i)
    #     if os.path.isdir(os.path.join(directory, i)):
    #         print(count, folder_name)
    #
    #         with ThreadPoolExecutor(max_workers=4) as executor:  # Максимальное количество одновременных потоков
    #             for filename in os.listdir(folder_name):
    #                 if filename.endswith('.png') and (
    #                         filename.split('.')[0].startswith('!') or filename.split('.')[0].strip().isdigit()):
    #                     executor.submit(process_image, filename)
