from PIL import Image, ExifTags
import os


def exif_transpose(img):
    try:
        exif = dict(img._getexif().items())
        if exif[274] == 3:
            return img.transpose(Image.ROTATE_180)
        elif exif[274] == 6:
            return img.transpose(Image.ROTATE_270)
        elif exif[274] == 8:
            return img.transpose(Image.ROTATE_90)
    except (AttributeError, KeyError, IndexError):
        # No EXIF data, or invalid orientation tag
        pass
    return img


def compress_images(input_dir, output_dir, target_size=(1024, 1024)):
    # Проверяем, существует ли выходная директория, и создаем ее, если необходимо
    if not os.path.exists(output_dir):
        os.makedirs(output_dir)

    # Получаем список файлов в указанной директории
    files = os.listdir(input_dir)

    for file in files:
        # Формируем полный путь к файлу
        input_path = os.path.join(input_dir, file)
        output_path = os.path.join(output_dir, file)

        try:
            # Открываем изображение
            img = Image.open(input_path)

            # Корректируем ориентацию изображения
            img = exif_transpose(img)

            # Сжимаем изображение без изменения пропорций
            img.thumbnail(target_size)

            # Сохраняем сжатое изображение
            img.save(output_path)

            print(f"Изображение {file} успешно сжато.")
        except Exception as e:
            print(f"Ошибка при обработке изображения {file}: {str(e)}")


if __name__ == "__main__":
    # Укажите путь к директории с исходными изображениями и директории для сохранения сжатых изображений
    input_directory = r"D:\user_photos"
    output_directory = r"D:\user_photos2"

    # Вызываем функцию сжатия изображений
    compress_images(input_directory, output_directory)
