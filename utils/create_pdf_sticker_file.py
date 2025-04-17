import os
import shutil


def create_barcodes():
    try:
        shutil.rmtree(os.path.join(BASE_DIR, "output"), ignore_errors=True)
        order_creator = OrderBarcodeCreator(self.arts, self.name_doc, self.ready_path)
        not_found_stickers = order_creator.create_order()

    except PermissionError as ex:
        logger.error('Нужно закрыть документ')
    except Exception as ex:
        logger.error(ex)