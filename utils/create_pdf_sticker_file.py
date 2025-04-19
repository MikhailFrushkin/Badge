import json
import os
from pprint import pprint

import barcode
import requests
from barcode.writer import ImageWriter
from loguru import logger
from reportlab.lib.pagesizes import landscape
from reportlab.lib.units import mm
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
from reportlab.pdfgen import canvas
import fitz

from config import OUTPUT_READY_FILES, BASE_DIR

font_path = "C:\\Windows\\Fonts\\Arial.ttf"


class PDFMerger:
    @staticmethod
    def merge_pdfs(arts_paths, name, ready_path):
        pdf_writer = fitz.open()
        for input_path in arts_paths:
            try:
                pdf_reader = fitz.open(input_path)
                pdf_writer.insert_pdf(pdf_reader)
                pdf_reader.close()
            except FileNotFoundError:
                logger.error(f"Файл {input_path} не найден.")
                continue
            except Exception as ex:
                logger.error(f"Ошибка при чтении файла {input_path}: {ex}, он удален!")
                continue

        current_output_path = os.path.join(ready_path, f"{name}.pdf")
        pdf_writer.save(current_output_path)
        pdf_writer.close()


def generate_ean13_with_text(code, filename):
    try:
        ean = barcode.get_barcode_class("code128")
        image_writer = ImageWriter()
        image_writer.font_path = font_path
        ean_barcode = ean(str(code), writer=image_writer)
        ean_barcode.save(filename)
    except Exception as e:
        logger.error(f"Ошибка при генерации штрих-кода: {e}")
        logger.error(f"Код: {code}, Имя файла: {filename}")


class PDF:
    def __init__(self, name, logo):
        self.name = name
        self.canvas = canvas.Canvas(
            self.name + ".pdf", pagesize=landscape((58 * mm, 40 * mm))
        )
        self.logo = logo

        pdfmetrics.registerFont(TTFont("Arial", font_path))
        self.font = "Arial"
        self.size = 9
        self.canvas.setFont(self.font, self.size)

        self.canvas.drawImage(
            self.logo, x=0, y=55, width=58 * mm, height=20 * mm, mask="auto"
        )

    @staticmethod
    def split_string_by_length(string, length):
        return [string[i: i + length] for i in range(0, len(string), length)]

    def write_text(self, txt, x, y, max_chars_per_line=28):
        lines = self.split_string_by_length(txt, max_chars_per_line)
        y_offset = 0
        for line in lines:
            self.canvas.drawString(x, y - y_offset, line)
            y_offset += self.size + 3

    def save(self):
        self.canvas.save()


class StickerGenerator:
    def __init__(self, output_dir):
        self.output_dir = output_dir
        os.makedirs(self.output_dir, exist_ok=True)

    def generate_sticker(self, art, barcode, category, brand):
        try:
            barcode_path = os.path.join(self.output_dir, art)
            generate_ean13_with_text(barcode, barcode_path)
            pdf = PDF(
                os.path.join(self.output_dir, art),
                f"{barcode_path}.png",
            )
            pdf.write_text(f"{category}", 8, 50)
            pdf.write_text(f"Бренд: {brand}", 8, 38)
            pdf.write_text(f"Артикул: {art}", 8, 26)
            pdf.save()
        except Exception as ex:
            logger.error(ex)


class OrderBarcodeCreator:
    def __init__(self, arts, name_doc):
        self.arts = arts
        self.name_doc = name_doc
        self.ready_path = OUTPUT_READY_FILES
        self.output_dir = os.path.join(BASE_DIR, "output")
        self.sticker_generator = StickerGenerator(self.output_dir)

    def get_info_arts(self):
        url_all_cards = "https://mycego.online/production_programs/control-price-wb/"
        response = requests.post(url_all_cards, json={"arts": self.arts})

        if response.status_code == 200:
            response_data = response.json()
            # with open('info_art.json', 'w', encoding='utf-8') as file:
            #     json.dump(response_data, file, indent=4, ensure_ascii=False)
            return {i.get("art").lower(): i for i in response_data}
        else:
            logger.error(response.status_code)
            logger.error(response.text)

    def create_order(self):
        not_found_stickers = []
        data_arts = self.get_info_arts()
        arts_paths = []
        for art in self.arts:
            if art.lower() in data_arts:
                try:
                    data_art = data_arts.get(art.lower())
                    path_barcode = os.path.join(self.output_dir, f"{art.upper()}.pdf")
                    if not os.path.exists(path_barcode):
                        self.sticker_generator.generate_sticker(
                            art=art,
                            barcode=data_art.get("barcode"),
                            category=data_art.get("subjectName").get("name"),
                            brand=data_art.get("brand").get("name")
                        )
                    arts_paths.append(path_barcode)
                except Exception as ex:
                    logger.error(ex)
            else:
                not_found_stickers.append(art)

        if arts_paths:
            PDFMerger.merge_pdfs(arts_paths, self.name_doc, self.ready_path)
        return not_found_stickers


def create_barcodes(arts, name_doc):
    try:
        order_creator = OrderBarcodeCreator(arts, name_doc)
        not_found_stickers = order_creator.create_order()
        if not_found_stickers:
            logger.error(not_found_stickers)
        return not_found_stickers
    except PermissionError as pe:
        logger.error(f'Нужно закрыть документ {pe}')
    except Exception as ex:
        logger.error(ex)
