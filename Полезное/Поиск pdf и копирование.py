import os
import shutil


def main():
    directory = r'E:\Старая база значков'
    directory_out = r'E:\База значков\Значки ШК'
    for root, dirs, files in os.walk(directory):
        for file in files:
            if file.endswith('.pdf') and not os.path.exists(os.path.join(directory_out, file)):
                print(file)
                shutil.copy2(os.path.join(root, file), os.path.join(directory_out, file))


if __name__ == '__main__':
    main()