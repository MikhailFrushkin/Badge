import sys
from datetime import datetime

from PyQt5.QtWidgets import QApplication, QMainWindow, QLabel, QVBoxLayout, QWidget, QPushButton
from PyQt5.QtGui import QPixmap
from db import Article
from PyQt5.QtCore import Qt


class ImageLabelApp(QMainWindow):
    def __init__(self, size):
        super().__init__()
        self.size = size
        self.init_ui()
        self.load_articles()

    def init_ui(self):
        self.central_widget = QWidget(self)
        self.setCentralWidget(self.central_widget)

        self.image_label = QLabel(self)
        self.image_label.setAlignment(Qt.AlignCenter)  # Центрируем изображение в окне
        self.button_layout = QVBoxLayout()

        self.yes_button = QPushButton("Да", self)
        self.yes_button.clicked.connect(self.on_yes_clicked)
        self.no_button = QPushButton("Нет", self)
        self.no_button.clicked.connect(self.on_no_clicked)

        button_width = 300  # Задайте желаемую ширину кнопок
        button_height = 50  # Задайте желаемую высоту кнопок

        self.yes_button.setFixedSize(button_width, button_height)
        self.no_button.setFixedSize(button_width, button_height)

        self.button_layout.addWidget(self.yes_button)
        self.button_layout.addWidget(self.no_button)
        main_layout = QVBoxLayout(self.central_widget)
        main_layout.addWidget(self.image_label)
        main_layout.addLayout(self.button_layout)

        window_width = 1000  # Задайте фиксированную ширину окна
        window_height = 800  # Задайте фиксированную высоту окна
        self.setGeometry(
            (QApplication.desktop().width() - window_width) // 2,
            (QApplication.desktop().height() - window_height) // 2,
            window_width,
            window_height
        )
        self.setFixedSize(window_width, window_height)  # Фиксируем размер окна

        self.articles = []
        self.current_article_index = 0

    def load_articles(self):
        """3558"""
        offset_value = 3558
        self.articles = Article.select().where(Article.size == self.size).offset(offset_value)
        print(self.articles.count())
        if self.articles.count() > 0:
            self.load_image(self.current_article_index)

    def load_image(self, article_index):
        if 0 <= article_index < len(self.articles):     
            article = self.articles[article_index]
            image_paths = article.images.split(',')  # Предполагается, что пути разделены запятыми

            if image_paths:
                self.current_image_index = 0
                self.show_image(image_paths[self.current_image_index])

    def show_image(self, image_path):
        pixmap = QPixmap(image_path)

        # Получение размеров окна
        window_width = self.central_widget.width()
        window_height = self.central_widget.height()

        # Масштабирование изображения до размеров окна
        scaled_pixmap = pixmap.scaled(window_width, window_height, Qt.KeepAspectRatio)

        self.image_label.setPixmap(scaled_pixmap)

    def on_yes_clicked(self):
        self.save_to_file(self.articles[self.current_article_index].art, "да.txt")
        self.next_article()

    def on_no_clicked(self):
        self.save_to_file(self.articles[self.current_article_index].art, "нет.txt")
        self.next_article()

    def save_to_file(self, image_path, filename):
        with open(filename, "a") as file:
            file.write(image_path + "\n")

    def next_article(self):
        print(self.current_article_index)
        self.current_article_index += 1
        if self.current_article_index < len(self.articles):
            self.load_image(self.current_article_index)
        else:
            self.close()


if __name__ == '__main__':
    app = QApplication(sys.argv)
    window = ImageLabelApp(44)
    window.show()
    sys.exit(app.exec_())
