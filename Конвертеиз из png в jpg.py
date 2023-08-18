import os

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


if __name__ == '__main__':
    folder_name = r'C:\Users\Михаил\Desktop\archive'
    for index, filename in enumerate(os.listdir(folder_name), start=1):
        if (filename.split('.')[0].startswith('!') or filename.split('.')[0].isdigit()) \
                and (os.path.isfile(os.path.join(folder_name, filename)) and (filename.endswith('.png'))):
            print(filename)
            new_name = filename.split('.')[0] + '.jpg'
            input_image_path = fr'C:\Users\Михаил\Desktop\archive\{filename}'
            output_image_path = fr'C:\Users\Михаил\Desktop\archive\{new_name}'
            try:
                convert_square_to_circle(input_image_path, output_image_path, quality=95)
                os.remove(input_image_path)
            except Exception as ex:
                logger.error()
