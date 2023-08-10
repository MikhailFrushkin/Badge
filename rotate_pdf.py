import PyPDF2

# Путь к созданному PDF-файлу
input_pdf = r"E:\PyCharm\Badge2\Файлы на печать\37.pdf"
# Путь к выходному PDF-файлу
output_pdf = "output_a3_album_final.pdf"

# Открываем исходный PDF-файл и создаем объект PDF-документа
with open(input_pdf, "rb") as pdf_file:
    pdf_reader = PyPDF2.PdfReader(pdf_file)
    pdf_writer = PyPDF2.PdfWriter()

    # Копируем страницы из исходного файла в выходной, изменяя ориентацию метаданных
    for page in pdf_reader.pages:
        pdf_writer.add_page(page)
        # Изменяем метаданные ориентации страницы для открытия в книжной ориентации
        pdf_writer.pages[-1][PyPDF2.generic.NameObject("/Rotate")] = PyPDF2.generic.NumberObject(90)

    # Записываем результат в выходной файл
    with open(output_pdf, "wb") as output_file:
        pdf_writer.write(output_file)