import shutil

import pandas as pd
from loguru import logger

from config import replace_dict
from utils.utils import FilesOnPrint, replace_bad_simbols


def read_excel_file(file: str) -> list:
    """Чтенеие файла (.csv, .xlsx) с заказом и создание объектов FilesOnPrint"""
    df = pd.DataFrame()
    try:
        shutil.rmtree("Файлы связанные с заказом", ignore_errors=True)
    except:
        pass

    if file.endswith(".csv"):
        try:
            df = pd.read_csv(file, delimiter=";")
            if "Название товара" not in df.columns:
                df["Название товара"] = "Нет названия"
            df = (
                df.groupby("Артикул")
                .agg(
                    {
                        "Название товара": "first",
                        "Номер заказа": "count",
                    }
                )
                .reset_index()
            )

            mask = ~df["Артикул"].str.startswith("POSTER")
            df = df[mask]

            df = df.rename(
                columns={"Номер заказа": "Количество", "Артикул": "Артикул продавца"}
            )
        except Exception as ex:
            logger.error(ex)
    else:
        try:
            df = pd.read_excel(file)
            columns_list = list(map(str.lower, df.columns))

            if "Информация о заказе" in df.columns:
                df = pd.read_excel(file, skiprows=1)
                df = df.rename(columns={"Ваш SKU": "Артикул продавца"})

                # Оставляем только нужные столбцы
                df = df.loc[:, ["Артикул продавца", "Количество"]]

                # Фильтруем строки по содержанию подстрок
                # keywords = ['25', '37', '44', '56', 'Popsocket', 'popsocket', 'POPSOCKET']
                # df = df[df['Артикул продавца'].str.contains('|'.join(keywords))]
            elif len(columns_list) == 2:
                try:
                    df = df.rename(
                        columns={
                            df.columns[0]: "Артикул продавца",
                            df.columns[1]: "Количество",
                        }
                    )
                except Exception as ex:
                    logger.error(ex)
                    df = df.rename(columns={"Aртикул": "Артикул продавца"})
            else:
                df = (
                    df.groupby("Артикул продавца")
                    .agg(
                        {
                            "Стикер": "count",
                        }
                    )
                    .reset_index()
                )
                df = df.rename(columns={"Стикер": "Количество"})
        except Exception as ex:
            logger.error(ex)

    files_on_print = []
    try:
        for index, row in df.iterrows():
            art = str(row["Артикул продавца"])
            if "-poster-" in art.lower():
                file_on_print = FilesOnPrint(
                    art=replace_bad_simbols(art.strip().lower()),
                    origin_art=art,
                    count=row["Количество"],
                )
                files_on_print.append(file_on_print)
            elif "poster-" not in art.lower():
                if art in replace_dict:
                    art_replace = replace_dict[art]
                else:
                    art_replace = art
                file_on_print = FilesOnPrint(
                    art=replace_bad_simbols(art_replace.strip().lower()),
                    origin_art=art,
                    count=row["Количество"],
                )
                files_on_print.append(file_on_print)
    except Exception as ex:
        logger.error(ex)
    return files_on_print
