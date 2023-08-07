import os
import shutil


def copy_pdfs(source_dir, target_dir):
    # Создаем целевую директорию, если она не существует
    if not os.path.exists(target_dir):
        os.makedirs(target_dir)

    # Проходим по всем файлам в исходной директории и её поддиректориям
    for root, dirs, files in os.walk(source_dir):
        for file in files:
            # Проверяем, что файл имеет расширение ".pdf"
            if file.lower().endswith(".pdf"):
                source_file_path = os.path.join(root, file)
                target_file_path = os.path.join(target_dir, file)
                # Проверяем, существует ли файл уже в целевой директории
                if not os.path.exists(target_file_path):
                    # Копируем файл, если его там нет
                    shutil.copy2(source_file_path, target_dir)
                    print(f"Скопирован файл: {file}")


# Укажите исходную директорию и целевую директорию
source_directory = r"E:\Старая база значков"
target_directory = r"E:\Новая база значков\Значки ШК"

copy_pdfs(source_directory, target_directory)
