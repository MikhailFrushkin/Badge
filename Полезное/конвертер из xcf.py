import os
from subprocess import run

gimp_path = 'C:\\Program Files\\GIMP 2\\bin\\gimp-console-2.10.exe'


def convert(file, name_file='new'):
    filename = file
    new_name = os.path.basename(file).replace('.xcf', '.png')
    folder = os.path.dirname(file)

    # Ensure the directory exists
    os.makedirs(folder, exist_ok=True)

    if name_file == 'new':
        output_path = os.path.join(folder, new_name)
    elif name_file == 'skin':
        skin_folder = os.path.join(folder, 'Подложка')
        os.makedirs(skin_folder, exist_ok=True)
        output_path = os.path.join(skin_folder, 'Подложка.png')

    # Normalize and encode the output path
    output_path = output_path.replace('\\', '\\\\')

    gimp_command = [
        gimp_path,
        '-i',
        '-b',
        f'(gimp-file-load RUN-NONINTERACTIVE "{filename}" "{filename}")',
        '-b',
        f'(gimp-file-save RUN-NONINTERACTIVE 1 (car (gimp-image-merge-visible-layers (aref (cadr (gimp-image-list)) 0) 0)) "{output_path}" "{name_file}.png")',
        '-b',
        '(gimp-quit 0)'
    ]
    run(gimp_command, shell=False)


if __name__ == '__main__':
    file_path = r'D:\\База значков\\сделать\\2.xcf'
    convert(file_path)
