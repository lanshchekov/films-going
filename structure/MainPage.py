import datetime
import sqlite3
from contextlib import closing

from PyQt5 import QtCore
from PyQt5.QtCore import QEvent
from PyQt5.QtGui import QFont, QMouseEvent
from PyQt5.QtWidgets import QMainWindow, QListWidgetItem, QFileDialog, QMessageBox

from design.py.main_page_design import Ui_MainPage
from structure.FilmInfo import FilmInfo


def get_clean_film_title(film_title: str) -> str:
    ignored_symbols = ",.!?:;-'\"/\\()"
    res = ""
    film_title = film_title.lower().replace('ё', 'е').replace("&quot;", '')
    last_symbol = ''
    for symbol in film_title:
        if symbol in ignored_symbols:
            continue
        if symbol == ' ' and last_symbol == ' ':
            continue
        res += symbol
        last_symbol = symbol
    return res.strip()  # strip именно здесь, чтобы обработать все дополнительные случаи


class MainPage(QMainWindow, Ui_MainPage):
    # TODO: Добавлять только уникальные фильмы (без повторов)
    # TODO: Настроить работу окон + закрытие БД по закрытию окна
    # TODO: Добавить документацию в правый нижний угол (по кнопке)

    APP_NAME = "Films Going"
    SPLITTER = ";;"
    ELEMENTS_QUANTITY = 5
    YEAR_RANGE = (1800, datetime.datetime.now().year)
    DURATION_RANGE = (1, 10_000)
    FILE_FORMATS = (".txt",)
    DEFAULT_GENRE_INDEX = 0

    def __init__(self):
        super(MainPage, self).__init__()
        self.setupUi(self)

        self.con = sqlite3.connect("db/films_db.sqlite")
        with closing(self.con.cursor()) as cur:
            self.GENRES = [genre[0].capitalize() for genre in
                           cur.execute("""SELECT title FROM genres""").fetchall()]

        self.film_info = None
        self.theoretic_min_year = None
        self.theoretic_max_year = None
        self.theoretic_min_duration = None
        self.theoretic_max_duration = None

        self.update_filter_limits()
        self.genre_box.addItems(self.GENRES)
        self.reset_filter()  # Ставим фильтр в начальное состояние

        # Чтобы текст в QComboBox был выровнен по центру
        self.genre_box.setEditable(True)
        self.genre_box.lineEdit().setReadOnly(True)
        self.genre_box.lineEdit().setAlignment(QtCore.Qt.AlignCenter)
        self.genre_box.lineEdit().setFont(QFont("Cascadia Code", 11, QFont.Bold))
        self.genre_box.lineEdit().installEventFilter(self)  # Чтобы по нажатию открывалось меню QComboBox
        for i in range(self.genre_box.count()):
            self.genre_box.setItemData(i, QtCore.Qt.AlignCenter, QtCore.Qt.TextAlignmentRole)

        self.genre_box.setStyleSheet("""
         QComboBox {
            background-color: rgb(47, 47, 47);
            color: rgb(203, 116, 47);
            border: 0px;
            border-top-right-radius: 3px;
            border-bottom-right-radius: 3px;
            letter-spacing: 0.2px;
            padding-left: 5px;
            padding-right: 5px;
            outline: 0;
        }

         QComboBox::drop-down {
             subcontrol-origin: padding;
             subcontrol-position: top right;
             width: 18px;
             border-top-right-radius: 3px;
             border-bottom-right-radius: 3px;
             background: rgb(203, 116, 47);
         }

         QComboBox::down-arrow {
             width: 0;
         }""")
        self.genre_box.currentIndexChanged.connect(self.control_filter_value)

        self.start_year_spin.valueChanged.connect(self.control_filter_value)
        self.end_year_spin.valueChanged.connect(self.control_filter_value)
        self.min_duration_spin.valueChanged.connect(self.control_filter_value)
        self.max_duration_spin.valueChanged.connect(self.control_filter_value)

        self.films_list.verticalScrollBar().setStyleSheet("""
          QScrollBar:vertical {
            border: 0;
            background: rgb(30, 30, 30);
            width: 17px;
            margin: 25px 0 25px 0;
          }

          QScrollBar::handle:vertical {
            background: qlineargradient(spread:pad, x1:0.5, y1:0, x2:0.5, y2:1,
            stop:0 rgba(203, 116, 47, 255), stop:1 rgba(231, 146, 78, 255));
            min-height: 25px;
          }

          QScrollBar::add-line:vertical {
            border: 0;
            border-bottom-left-radius: 2px;
            border-bottom-right-radius: 2px;
            background: rgb(224, 139, 70);
            height: 23px;
            subcontrol-position: bottom;
            subcontrol-origin: margin;
        }

        QScrollBar::sub-line:vertical {
            border: 0;
            border-top-left-radius: 2px;
            border-top-right-radius: 2px;
            background: rgb(224, 139, 70);
            height: 23px;
            subcontrol-position: top;
            subcontrol-origin: margin;
        }

        QScrollBar::add-page:vertical, QScrollBar::sub-page:vertical {
            background: none;
        }""")
        self.films_list.itemDoubleClicked.connect(self.show_film_info)

        self.search_button.clicked.connect(self.find_film)
        self.reset_filter_button.clicked.connect(self.reset_filter)
        self.add_film_button.clicked.connect(self.add_film)

        self.find_film()  # Сразу отображаем все фильмы

    def add_film(self) -> None:
        data_file_name = QFileDialog.getOpenFileName(
            self, "Выбрать отформатированный файл", '',
            ";;".join(['*' + frmt for frmt in self.FILE_FORMATS]))[0]
        if not data_file_name:
            return
        with open(data_file_name, encoding="utf-8") as dfn:
            with closing(self.con.cursor()) as cur:
                for film_data in dfn:
                    if self.is_valid_format(film_data):
                        title, year, genre, duration, description = film_data.split(self.SPLITTER)
                        year, duration = int(year), int(duration)
                        cur.execute("""
                            INSERT INTO films(title, year, genre, duration, description)
                            VALUES(?, ?, (SELECT id FROM genres WHERE genres.title = ?), ?, ?)
                        """, (title, year, genre.lower(), duration, description))
                    else:
                        self.con.rollback()
                        QMessageBox.critical(self, self.APP_NAME,
                                             "Неверно отформатированный файл")
                        break
                else:
                    self.con.commit()
                    self.update_filter_limits()
                    QMessageBox.information(self, self.APP_NAME,
                                            f"Данные успешно добавлены")
                    self.control_filter_value()  # [Чтобы возможно обновить вид кнопки сброса фильтра]
                    self.find_film()

    def is_valid_format(self, film_data) -> bool:
        sep_film_data = film_data.split(self.SPLITTER)
        if len(sep_film_data) != self.ELEMENTS_QUANTITY:
            return False
        title, year, genre, duration, description = sep_film_data
        if not get_clean_film_title(title):
            return False
        if not (year.isnumeric() and duration.isnumeric()):
            return False
        year, duration = int(year), int(duration)
        if not self.YEAR_RANGE[0] <= year <= self.YEAR_RANGE[1]:
            return False
        if not self.DURATION_RANGE[0] <= duration <= self.DURATION_RANGE[1]:
            return False
        if genre.capitalize() not in self.GENRES:
            return False
        return True

    def show_film_info(self, film: QListWidgetItem) -> None:
        presented_name = film.text().rsplit(maxsplit=1)
        title, year = presented_name[0], int(presented_name[1][1:-1])
        with closing(self.con.cursor()) as cur:
            film_id, genre, duration, description = cur.execute(f"""
                SELECT films.id, genres.title, duration, description
                FROM films JOIN genres ON genres.id = films.genre
                WHERE replace(films.title, "&quot;", '') = ? AND films.year = ?
            """, (title, year)).fetchone()
        self.film_info = FilmInfo(film_id, title, year, genre, duration, description)
        self.film_info.show()

    def update_filter_limits(self) -> None:
        self.theoretic_min_year = self.get_min_year()
        self.theoretic_max_year = self.get_max_year()
        self.theoretic_min_duration = self.get_min_duration()
        self.theoretic_max_duration = self.get_max_duration()

        self.start_year_spin.setRange(self.theoretic_min_year, self.theoretic_max_year)
        self.end_year_spin.setRange(self.theoretic_min_year, self.theoretic_max_year)
        self.min_duration_spin.setRange(self.theoretic_min_duration, self.theoretic_max_duration)
        self.max_duration_spin.setRange(self.theoretic_min_duration, self.theoretic_max_duration)

    def reset_filter(self) -> None:
        self.genre_box.setCurrentIndex(self.DEFAULT_GENRE_INDEX)
        self.start_year_spin.setValue(self.theoretic_min_year)
        self.end_year_spin.setValue(self.theoretic_max_year)
        self.min_duration_spin.setValue(self.theoretic_min_duration)
        self.max_duration_spin.setValue(self.theoretic_max_duration)

    def eventFilter(self, obj, event: QEvent) -> bool:
        if obj is self.genre_box.lineEdit() and event.type() == QMouseEvent.MouseButtonPress:
            if event.button() == QtCore.Qt.MouseButton.LeftButton:
                self.genre_box.showPopup()
        return super(MainPage, self).eventFilter(obj, event)

    def find_film(self) -> None:
        self.films_list.clear()

        search_title = get_clean_film_title(self.search_film.text())
        genre = self.genre_box.currentText().lower()
        start_year = self.start_year_spin.value()
        end_year = self.end_year_spin.value()
        min_duration = self.min_duration_spin.value()
        max_duration = self.max_duration_spin.value()

        with closing(self.con.cursor()) as cur:
            query = cur.execute(f"""SELECT title, year FROM films
                WHERE genre IN (
                    SELECT id FROM genres WHERE title = "{genre}"
                    OR "{genre}" = "не выбрано"
                )
                AND year BETWEEN {start_year} AND {end_year}
                AND duration BETWEEN {min_duration} AND {max_duration}""")

            for item in sorted(query.fetchall(), key=lambda x: x[1], reverse=True):
                film_title = item[0].replace("&quot;", '') + f" ({item[1]})"
                if search_title in get_clean_film_title(film_title):
                    film = QListWidgetItem(film_title)
                    film.setTextAlignment(QtCore.Qt.AlignCenter)
                    self.films_list.addItem(film)
            self.films_list.scrollToTop()

    def control_filter_value(self) -> None:
        obj = self.sender()
        if obj == self.start_year_spin:
            self.start_year_spin.setMaximum(self.end_year_spin.value())
        elif obj == self.end_year_spin:
            self.end_year_spin.setMinimum(self.start_year_spin.value())
        elif obj == self.min_duration_spin:
            self.min_duration_spin.setMaximum(self.max_duration_spin.value())
        elif obj == self.max_duration_spin:
            self.max_duration_spin.setMinimum(self.min_duration_spin.value())
        self.reset_filter_button.setEnabled(not self.is_filer_reset())

    def is_filer_reset(self) -> bool:
        filter_values = (self.genre_box.currentIndex(), self.start_year_spin.value(),
                         self.end_year_spin.value(), self.min_duration_spin.value(),
                         self.max_duration_spin.value())
        reset_values = (self.DEFAULT_GENRE_INDEX, self.theoretic_min_year, self.theoretic_max_year,
                        self.theoretic_min_duration, self.theoretic_max_duration)
        return filter_values == reset_values

    def get_min_year(self) -> int:
        with closing(self.con.cursor()) as cur:
            return cur.execute("""SELECT MIN(year) FROM films""").fetchone()[0]

    def get_max_year(self) -> int:
        with closing(self.con.cursor()) as cur:
            return cur.execute("""SELECT MAX(year) FROM films""").fetchone()[0]

    def get_min_duration(self) -> int:
        with closing(self.con.cursor()) as cur:
            return cur.execute("""SELECT MIN(duration) FROM films""").fetchone()[0]

    def get_max_duration(self) -> int:
        with closing(self.con.cursor()) as cur:
            return cur.execute("""SELECT MAX(duration) FROM films""").fetchone()[0]
