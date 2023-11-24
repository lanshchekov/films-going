import sqlite3
from contextlib import closing
from os import listdir
from os.path import exists, join
from shutil import rmtree

from PIL import Image, ImageDraw
from PyQt5 import QtCore, QtGui
from PyQt5.QtCore import Qt
from PyQt5.QtGui import QPixmap
from PyQt5.QtWidgets import QWidget
from icrawler.builtin import GoogleImageCrawler

from design.py.film_info_design import Ui_FilmInfo


class FilmInfo(QWidget, Ui_FilmInfo):
    DIRECTORY = "design/film_img"
    IMAGE_SIZE = (1200, 800)
    FILTER_COLOR = (30, 30, 30, 140)  # RGBA
    IMAGE_RADIUS = 18
    IMAGE_EXPANSION = ".png"

    def __init__(self, film_id: int, title: str, year: int,
                 genre: str, duration: int, description: str):
        super(FilmInfo, self).__init__()
        self.setupUi(self)

        self.film_id = film_id
        self.title = title
        self.year = year
        self.genre = genre.capitalize()
        self.duration = duration
        self.description = description

        self.load_bg_image()
        path = join(self.DIRECTORY, listdir(self.DIRECTORY)[0])
        img = Image.open(path)  # TODO: нужно ли безопасно работать с картинками?
        self.modify_image(img)
        # Сохраняем в разрешении IMAGE_EXPANSION, чтобы поддерживать модификацию
        changed_path = path.rsplit('.', maxsplit=1)[0] + self.IMAGE_EXPANSION
        img.save(changed_path)
        self.image_zone.setPixmap(QPixmap(changed_path))
        self.image_zone.setAlignment(Qt.AlignCenter)

        self.film_title_label.setText(self.title)
        self.film_genre_label.setText(self.genre)
        self.film_duration_label.setText(str(self.duration))
        self.film_year_label.setText(str(self.year))
        self.description_text.setPlainText(self.description)

        self.modify_description_button.setPixmap(QPixmap("design/resource/modify_description_button_icon.svg"))
        self.modify_description_button.mousePressEvent = self.handle_mdb

        self.save_description_button.setPixmap(QPixmap("design/resource/save_description_button_icon_disabled.svg"))
        self.save_description_button.mousePressEvent = self.handle_sdb

    def handle_mdb(self, event: QtGui.QMouseEvent) -> None:
        if event.button() == QtCore.Qt.MouseButton.LeftButton:
            self.modify_description_button.setEnabled(False)
            self.modify_description_button.setPixmap(QPixmap(
                "design/resource/modify_description_button_icon_disabled.svg"))

            self.description_text.setReadOnly(False)
            self.description_text.viewport().setCursor(QtCore.Qt.CursorShape.IBeamCursor)
            self.description_text.selectAll()

            self.save_description_button.setEnabled(True)
            self.save_description_button.setPixmap(QPixmap(
                "design/resource/save_description_button_icon.svg"))

    def handle_sdb(self, event: QtGui.QMouseEvent) -> None:
        if event.button() == QtCore.Qt.MouseButton.LeftButton:
            self.save_description_button.setEnabled(False)
            self.save_description_button.setPixmap(QPixmap(
                "design/resource/save_description_button_icon_disabled.svg"))

            self.description_text.setReadOnly(True)
            self.description_text.setTextInteractionFlags(QtCore.Qt.TextInteractionFlag.NoTextInteraction)
            self.description_text.viewport().setCursor(QtCore.Qt.CursorShape.ArrowCursor)
            text_cursor = self.description_text.textCursor()
            text_cursor.clearSelection()
            self.description_text.setTextCursor(text_cursor)

            self.description = self.description_text.toPlainText()
            self.save_film_description()  # Сохраняем измененное описание в БД

            self.modify_description_button.setEnabled(True)
            self.modify_description_button.setPixmap(QPixmap(
                "design/resource/modify_description_button_icon.svg"))

    def save_film_description(self) -> None:
        with sqlite3.connect("db/films_db.sqlite") as con:
            with closing(con.cursor()) as cur:
                cur.execute(f"""
                    UPDATE films SET description = ?
                        WHERE id = ?
                """, (self.description, self.film_id))  # Используя ? решаем проблему с кавычками
        con.close()

    def load_bg_image(self) -> None:
        self.remove_directory()  # Чтобы у пользователя всегда хранилось максимум 1 изображение

        google_crawler = GoogleImageCrawler(storage={"root_dir": self.DIRECTORY})
        filters = dict(type="photo")
        search = f"{self.title} фильм {self.year}"
        google_crawler.crawl(keyword=search, filters=filters, max_num=1)

    def remove_directory(self) -> None:
        if exists(self.DIRECTORY):
            rmtree(self.DIRECTORY)

    def modify_image(self, img: Image.Image) -> None:
        img.thumbnail((self.image_zone.width(), self.image_zone.height()))
        self.set_filter(img)
        self.round_image(img)

    def set_filter(self, img: Image.Image) -> None:
        img_filter = Image.new("RGBA", img.size, self.FILTER_COLOR)
        img.paste(img_filter, mask=img_filter)

    def round_image(self, img: Image.Image) -> None:
        mask = Image.new("L", img.size, 0)
        draw = ImageDraw.Draw(mask)
        draw.rounded_rectangle((0, 0, mask.width, mask.height), self.IMAGE_RADIUS, fill="white")
        img.putalpha(mask)
