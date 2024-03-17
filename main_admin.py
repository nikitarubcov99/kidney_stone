import os
import re
import sys

import fitz
import innvestigate
from PyQt5 import QtCore, QtWidgets, uic
from PyQt5.QtCore import QDate
from PyQt5.QtGui import QPixmap, QImage
from PyQt5.QtWidgets import QApplication, QMainWindow, QTableWidget, QFileDialog, QLabel, \
    QPushButton, QProgressBar, QLineEdit, QTextEdit, QMessageBox, QDialog, QWidget, QVBoxLayout, QTableWidgetItem
import cv2
import keras
from datetime import datetime
import matplotlib
import numpy as np
from fpdf import FPDF
from matplotlib import pyplot as plt

from models.models import *
import psycopg2
import tensorflow as tf
from keras.applications import EfficientNetB3
from keras.applications.efficientnet import preprocess_input
from tensorflow.keras.preprocessing import image
from tensorflow.keras.applications.vgg16 import preprocess_input


def load_and_preprocess_image(img_path):
    img = image.load_img(img_path, target_size=(128, 128))  # Загружаем и изменяем размер изображения
    x = image.img_to_array(img)  # Преобразуем изображение в массив numpy
    x = np.expand_dims(x, axis=0)  # Добавляем дополнительное измерение, т.к. модель ожидает батч изображений
    x = preprocess_input(x)  # Предварительная обработка, как для обучения модели (зависит от вашей модели)
    return x

def add_image_to_existing_pdf(pdf_path, image_path, image_path1, page_number):
    """
    Функция для добавления изображений в pdf файл
    :param pdf_path: путь к файлу в котором будет храниться отчет
    :param image_path: путь к исходному изображению
    :param image_path1: путь к изображению с тепловой картой аномалий
    :param page_number: номер страницы pdf файла на которую нужно вставить изображение
    :return:
    """
    # Открываем существующий PDF-файл
    pdf_document = fitz.open(pdf_path)

    # Открываем изображение
    pdf_document[page_number].insert_image(fitz.Rect(30, 255, 230, 455), stream=open(image_path, "rb").read())
    pdf_document[page_number].insert_image(fitz.Rect(330, 255, 530, 455), stream=open(image_path1, "rb").read())

    pdf_document.saveIncr()

    # Закрываем документ
    pdf_document.close()
def get_patient_info(patient_id):
    try:
        # Получаем информацию о пациенте по ID
        patient = PatientModel.get_by_id(patient_id)
        # Возвращаем словарь с информацией о пациенте
        return {
            "Фамилия": patient.patient_family,
            "Имя": patient.patient_name,
            "Отчество": patient.patient_second_name,
            "Возраст": patient.patient_age,
            "Дата рождения": patient.patient_birth_date.strftime('%Y-%m-%d'),
            "СНИЛС": patient.patient_snils,
            "Наличие камней в почках": patient.patient_has_kidney_stone,
            "Количество анализов": patient.patient_analyses_count
        }
    except PatientModel.DoesNotExist:
        return "Пациент с таким ID не найден."


def get_doctor_info(doctor_id):
    try:
        # Получаем информацию о враче по ID
        doctor = DoctorModel.get_by_id(doctor_id)
        # Возвращаем словарь с информацией о враче
        return {
            "Фамилия": doctor.doctor_family,
            "Имя": doctor.doctor_name,
            "Отчество": doctor.doctor_second_name,
            "Категория": doctor.doctor_class
        }
    except DoctorModel.DoesNotExist:
        return "Врач с таким ID не найден."


class PatientDetailsWindow(QDialog):
    def __init__(self, card_id, parent=None):
        super().__init__(parent)
        self.card_id = card_id
        self.card = None  # Инициализируем card как None
        self.init_ui()
        self.fill_data()
        self.parent = parent

    def init_ui(self):
        uic.loadUi('ui/Card.ui', self)
        self.pushButton.clicked.connect(self.generate_pdf)
        self.pushButton_3.clicked.connect(self.close)

    def closeEvent(self, event):
        # При закрытии формы показываем родительское окно (вторую форму)
        if self.parent:
            self.parent.reopen()  # Используйте метод reopen() для показа второй формы
        event.accept()

    def generate_pdf(self):
        """
        Метод для создания pdf файла с отчетом
        :return: ничего не возвращает
        """
        # инициализируем документ и шрифт
        pdf = FPDF()
        pdf.add_page()
        font_path = 'fonts/timesnrcyrmt.ttf'
        pdf.add_font("Times", "", font_path, uni=True)
        pdf.set_font("Times", size=14)
        # описываем все строки которые будут добавлены в pdf отчет
        intro = '            Отчет об анализе на наличие лейкемии по пятну крови'.encode('utf-8')
        fio_intro = 'Данные пациента: '.encode('utf-8')
        patient_fio = f'Фамилия: {self.label.text()} Имя: {self.label_2.text()} Отчество: {self.label_3.text()} полных лет: {self.patient_age}'.encode(
            'utf-8')
        patient = f'СНИЛС: {self.patient_snils}     диагноз по МКБ-10: {self.mkb_diagnose}     кол-во анализов {self.patient_count}'.encode(
            'utf-8')
        doctor_intro = 'Информация о лечащем враче: '.encode('utf-8')
        doctor_fio = f'Фамилия: {self.doctor_name} Имя: {self.doctor_second_name} Отчество: {self.doctor_family}'.encode(
            'utf-8')
        doctor_cat = f'Категория лечащего врача: {self.doctor_class}'.encode('utf-8')
        image_intro_norm = 'Изначальное изображение                          Изображение с аномалиями'.encode('utf-8')
        if self.diagnose == 'лейкимия':
            analys_result = '                            При анализе обнаружена лейкемия'.encode('utf-8')
        else:
            analys_result = '                              Заболеваний не обнаружено'.encode('utf-8')
        open_date = f'Дата создания карточки {self.output_date_str}                       Дата осмотра {self.current_date_str}'.encode(
            'utf-8')
        # добавляем полученные строки в pdf файл отчета
        pdf.set_font("Times", size=18)
        pdf.multi_cell(200, 10, str(intro.decode('utf-8')), align='С')
        pdf.set_font("Times", size=16)
        pdf.multi_cell(200, 10, str(fio_intro.decode('utf-8')))
        pdf.set_font("Times", size=14)
        pdf.multi_cell(400, 10, str(patient_fio.decode('utf-8')))
        pdf.multi_cell(400, 10, str(patient.decode('utf-8')))
        pdf.set_font("Times", size=16)
        pdf.multi_cell(400, 10, str(doctor_intro.decode('utf-8')))
        pdf.set_font("Times", size=14)
        pdf.multi_cell(400, 10, str(doctor_fio.decode('utf-8')))
        pdf.multi_cell(400, 10, str(doctor_cat.decode('utf-8')))
        pdf.set_font("Times", size=16)
        pdf.multi_cell(400, 10, str(image_intro_norm.decode('utf-8')))
        pdf.set_font("Times", size=18)
        pdf.ln(75)
        pdf.multi_cell(400, 10, str(analys_result.decode('utf-8')))
        pdf.set_font("Times", size=14)
        pdf.multi_cell(400, 10, str(open_date.decode('utf-8')))
        pdf_path = f"reports/{self.patient_name} {self.patient_second_name[0]}. {self.patient_family[0]}.  {self.current_date_str}.pdf"
        pdf.output(pdf_path)
        # добавляем исходное изображение и изображение с тепловой картой аномалий в pdf файл отчета
        with open("image_from_db.jpeg", "wb") as file:
            file.write(self.start_image)
            file.close()
        with open("image_from_db1.jpeg", "wb") as file:
            file.write(self.anomaly_image)
            file.close()
        image_path = "C:/Users/nero1/PycharmProjects/pythonProject7/image_from_db.jpeg"
        image_path1 = "C:/Users/nero1/PycharmProjects/pythonProject7/image_from_db1.jpeg"
        existing_pdf_path = pdf_path
        target_page_number = 0
        add_image_to_existing_pdf(existing_pdf_path, image_path, image_path1, target_page_number)
        os.remove(image_path1)
        os.remove(image_path)
    def fill_data(self):
        self.card = PatientsCardsModel.get_by_id(self.card_id)
        patient_dict = get_patient_info(self.card.patient_card_patient_id)
        doctor_dict = get_doctor_info(self.card.patient_card_doctor_id)
        diagnose = self.card.diagnose
        mkb = self.card.mkb_diagnose
        date = self.card.card_creation_date
        date_string = date.strftime('%Y-%m-%d')

        self.label.setText(patient_dict['Имя'])
        self.label_2.setText(patient_dict['Отчество'])
        self.label_3.setText(patient_dict['Фамилия'])
        self.label_5.setText(doctor_dict['Имя'])
        self.label_6.setText(doctor_dict['Отчество'])
        self.label_4.setText(doctor_dict['Фамилия'])
        self.label_16.setText(f"СНИЛС пациента: {patient_dict['СНИЛС']}")
        if 'мочекаменная' in diagnose:
            self.label_9.setText(f'Обнаружена мочекаменная болезнь, код по МКБ-10 {mkb}')
        else:
            self.label_9.setText('Заболеваний не обнаружено')
        self.label_20.setText(date_string)
        self.label_22.setText(str(patient_dict['Количество анализов']))

        if self.card.start_image:
            with open("image_from_db.jpg", "wb") as file:
                file.write(self.card.start_image)
                file.close()
            file_name = "C:/Users/nero1/PycharmProjects/pythonProject3/image_from_db.jpg"
            self.pixmap = QPixmap(file_name)
            self.pixmap = self.pixmap.scaled(241, 221)
            self.label_10.setPixmap(self.pixmap)
            os.remove(file_name)
        if self.card.anomaly_image:
            with open("image_from_db1.jpg", "wb") as file:
                file.write(self.card.anomaly_image)
                file.close()
            file_name = "C:/Users/nero1/PycharmProjects/pythonProject3/image_from_db1.jpg"
            self.pixmap = QPixmap(file_name)
            self.pixmap = self.pixmap.scaled(241, 221)
            self.label_11.setPixmap(self.pixmap)
            os.remove(file_name)


class ui_admin(QMainWindow):
    """
    Класс реализующий инициализацию компонентов и дальнейшее взаимодействие с окном программы "создание отчета"
    """

    def __init__(self, parent=None):
        """
        Консструктор класса
        """
        super().__init__(parent)
        self.setupUi()
        self.parent = parent

    def setupUi(self):
        """
        Метод для загрузки компонент интерфейса из ui файла
        :return: ничего не возвращает
        """
        uic.loadUi('ui/main_admin.ui', self)
        self.tableWidget.setColumnWidth(3, 450)

        self.tableWidget.setHorizontalHeaderLabels(["ФИО", "Статус", "Дата", "Просмотр"])
        self.show_list()
        self.pushButton.clicked.connect(self.openAddVisitForm)
        self.pushButton_2.clicked.connect(self.openAddDoctorForm)
        self.pushButton_3.clicked.connect(self.openAddPatientForm)
        self.pushButton_4.clicked.connect(self.close)
        self.show()

    def reopen(self):
        self.show_list()
        self.show()

    def closeEvent(self, event):
        # При закрытии окна показываем родительское окно
        if self.parent:
            self.parent.show()
        super().closeEvent(event)

    def show_list(self):
        patient_cards = PatientsCardsModel.select()
        self.tableWidget.setRowCount(patient_cards.count())
        for row, card in enumerate(patient_cards):
            # Здесь предполагается, что у вас есть соответствующие поля в модели PatientsCardsModel
            # Вам нужно будет адаптировать это к вашей конкретной модели и её полям
            patient = card.patient_card_patient_id
            fio = f"{patient.patient_family} {patient.patient_name[0]}.{patient.patient_second_name[0]}."
            self.tableWidget.setItem(row, 0, QTableWidgetItem(fio))
            self.tableWidget.setItem(row, 1, QTableWidgetItem(card.diagnose))
            self.tableWidget.setItem(row, 2, QTableWidgetItem(str(card.card_creation_date)))

            btn_view = QPushButton('Просмотр', self)
            btn_view.clicked.connect(lambda *args, card=card: self.view_card_details(card))
            self.tableWidget.setCellWidget(row, 3, btn_view)

    def view_card_details(self, card):
        # Эта функция будет вызвана при нажатии на кнопку "Просмотр"
        self.details_window = PatientDetailsWindow(card, self)
        self.details_window.fill_data()
        self.details_window.show()
        self.hide()

    def openAddDoctorForm(self):
        self.addDoctorForm = AddDoctorForm(self)
        self.addDoctorForm.show()
        self.hide()

    def openAddPatientForm(self):
        self.addPatientForm = AddPatientForm(self)
        self.addPatientForm.show()
        self.hide()

    def openAddVisitForm(self):
        self.addVisitForm = AddVisitForm(self)
        self.addVisitForm.show()
        self.hide()


class AddDoctorForm(QMainWindow):
    def __init__(self, parent=None):
        super(AddDoctorForm, self).__init__(parent)
        self.parent = parent
        self.should_close = False
        uic.loadUi('ui/add_doctor.ui', self)
        categories = ["Без категории", "Вторая", "Первая", "Высшая"]
        self.comboBox.addItems(categories)
        self.pushButton.clicked.connect(self.add_doctor)
        # self.should_close = True
        self.pushButton_2.clicked.connect(self.close)

    def add_doctor(self):
        # Считываем данные из формы
        family = self.lineEdit_3.text()
        if len(family) == 0:
            msg = QMessageBox()
            msg.setIcon(QMessageBox.Critical)
            msg.setText("Ошибка")
            msg.setInformativeText('Заполните поле фамилия')
            msg.setWindowTitle("Error")
            msg.exec_()
            return
        name = self.lineEdit.text()
        if len(name) == 0:
            msg = QMessageBox()
            msg.setIcon(QMessageBox.Critical)
            msg.setText("Ошибка")
            msg.setInformativeText('Заполните поле имя')
            msg.setWindowTitle("Error")
            msg.exec_()
            return
        second_name = self.lineEdit_2.text()
        if len(second_name) == 0:
            msg = QMessageBox()
            msg.setIcon(QMessageBox.Critical)
            msg.setText("Ошибка")
            msg.setInformativeText('Заполните поле отчество')
            msg.setWindowTitle("Error")
            msg.exec_()
            return
        category = self.comboBox.currentText()
        login = self.lineEdit_4.text()
        if len(login) == 0:
            msg = QMessageBox()
            msg.setIcon(QMessageBox.Critical)
            msg.setText("Ошибка")
            msg.setInformativeText('Заполните поле логин')
            msg.setWindowTitle("Error")
            msg.exec_()
            return
        password = self.lineEdit_5.text()
        if len(password) == 0:
            msg = QMessageBox()
            msg.setIcon(QMessageBox.Critical)
            msg.setText("Ошибка")
            msg.setInformativeText('Заполните поле пароль')
            msg.setWindowTitle("Error")
            msg.exec_()
            return
        # Создаем новую запись в базе данных

        doctor = DoctorModel.select().where(DoctorModel.doctor_name == name and DoctorModel.doctor_family == family
                                            and DoctorModel.doctor_second_name == second_name).get_or_none()
        if doctor is not None:
            # Если находим, сообщаем, что такой врач уже существует
            msg = QMessageBox()
            msg.setIcon(QMessageBox.Information)
            msg.setText("Информация")
            msg.setInformativeText("Врач с такими данными уже существует в базе данных.")
            msg.setWindowTitle("Информация")
            msg.exec_()
            return
        else:
            doctor = DoctorModel.create(
                doctor_family=family,
                doctor_name=name,
                doctor_second_name=second_name,
                category=category
            )

        doctor.save()

        user = UserModel.select().where(UserModel.user_login == login).get_or_none()
        # Если находим, сообщаем, что такой врач уже существует
        if user is not None:
            msg = QMessageBox()
            msg.setIcon(QMessageBox.Information)
            msg.setText("Информация")
            msg.setInformativeText("Пользователь с таким логином уже существует.")
            msg.setWindowTitle("Информация")
            msg.exec_()
            return
        else:
            UserModel.create(user_login=login,
                             user_password=password,
                             superuser=False,
                             doctor=doctor.id
                             )

    def closeEvent(self, event):
        if self.should_close:
            if self.parent:
                self.parent.reopen()  # Используйте метод reopen() для показа второй формы
            event.accept()  # Закрываем окно, если should_close == True
        else:
            event.ignore()  # Игнорируем событие закрытия, если should_close == False
            self.should_close = True


class AddPatientForm(QMainWindow):
    def __init__(self, parent=None):
        super(AddPatientForm, self).__init__(parent)
        self.parent = parent
        self.should_close = False
        uic.loadUi('ui/add_patient.ui', self)
        self.dateEdit.setCalendarPopup(True)
        self.dateEdit.setDate(QDate.currentDate())
        self.dateEdit.setMinimumDate(QDate(1900, 1, 1))
        self.dateEdit.setMaximumDate(QDate.currentDate())
        self.dateEdit.setDisplayFormat("yyyy.MM.dd")
        doctors = DoctorModel.select()
        doctor_list = ["не выбрано"]
        for doctor in doctors:
            doctor_list.append(f"{doctor.doctor_family} {doctor.doctor_name[0]} {doctor.doctor_second_name[0]}")
        self.comboBox.addItems(doctor_list)
        self.pushButton.clicked.connect(self.add_patient)
        self.pushButton_2.clicked.connect(self.close)

    def closeEvent(self, event):
        if self.should_close:
            if self.parent:
                self.parent.reopen()  # Используйте метод reopen() для показа второй формы
            event.accept()  # Закрываем окно, если should_close == True
        else:
            event.ignore()  # Игнорируем событие закрытия, если should_close == False
            self.should_close = True

    def add_patient(self):
        # Считываем данные из формы
        family = self.lineEdit_3.text()  # Предполагается, что это QLineEdit для фамилии
        if len(family) == 0:
            msg = QMessageBox()
            msg.setIcon(QMessageBox.Critical)
            msg.setText("Ошибка")
            msg.setInformativeText('Заполните поле фамилия')
            msg.setWindowTitle("Error")
            msg.exec_()
            return
        name = self.lineEdit.text()  # QLineEdit для имени
        if len(name) == 0:
            msg = QMessageBox()
            msg.setIcon(QMessageBox.Critical)
            msg.setText("Ошибка")
            msg.setInformativeText('Заполните поле имя')
            msg.setWindowTitle("Error")
            msg.exec_()
            return
        second_name = self.lineEdit_2.text()  # QLineEdit для отчества
        if len(second_name) == 0:
            msg = QMessageBox()
            msg.setIcon(QMessageBox.Critical)
            msg.setText("Ошибка")
            msg.setInformativeText('Заполните поле отчество')
            msg.setWindowTitle("Error")
            msg.exec_()
            return
        age = self.lineEdit_5.text()  # QLineEdit для отчества
        if len(age) == 0:
            msg = QMessageBox()
            msg.setIcon(QMessageBox.Critical)
            msg.setText("Ошибка")
            msg.setInformativeText('Заполните поле полных лет')
            msg.setWindowTitle("Error")
            msg.exec_()
            return
        birth_date = self.dateEdit.date().toPyDate()  # Преобразуем QDate в Python datetime.date
        birth_date_qdate  = self.dateEdit.date()
        birth_date_str = birth_date_qdate.toString("yyyy.MM.dd")
        if len(birth_date_str) == 0:
            msg = QMessageBox()
            msg.setIcon(QMessageBox.Critical)
            msg.setText("Ошибка")
            msg.setInformativeText('Введите дату рождения')
            msg.setWindowTitle("Error")
            msg.exec_()
            return
        snils = self.lineEdit_6.text()
        if len(snils) == 0:
            msg = QMessageBox()
            msg.setIcon(QMessageBox.Critical)
            msg.setText("Ошибка")
            msg.setInformativeText('Заполните поле СНИЛС')
            msg.setWindowTitle("Error")
            msg.exec_()
            return
        selected_doctor_id = self.comboBox.currentIndex()
        if selected_doctor_id == 0:
            msg = QMessageBox()
            msg.setIcon(QMessageBox.Critical)
            msg.setText("Ошибка")
            msg.setInformativeText('Выберите лечащего врача')
            msg.setWindowTitle("Error")
            msg.exec_()
            return
        try:
            patient = PatientModel.get(PatientModel.patient_snils == snils)
            # Если находим, сообщаем, что такой пациент уже существует
            msg = QMessageBox()
            msg.setIcon(QMessageBox.Information)
            msg.setText("Информация")
            msg.setInformativeText("Пациент с таким СНИЛС уже существует в базе данных.")
            msg.setWindowTitle("Информация")
            msg.exec_()
            return
        except DoesNotExist:
            patient = PatientModel.create(
                patient_name=name,
                patient_second_name=second_name,
                patient_family=family,
                patient_age=age,
                patient_birth_date=birth_date,
                patient_snils=snils,
                responsible_doctor=selected_doctor_id
            )


class AddVisitForm(QMainWindow):
    def __init__(self, parent=None):
        super(AddVisitForm, self).__init__(parent)
        self.parent = parent
        uic.loadUi('ui/add_visit.ui', self)
        doctors = DoctorModel.select()
        doctor_list = ["не выбрано"]
        for doctor in doctors:
            doctor_list.append(f"{doctor.doctor_family} {doctor.doctor_name[0]} {doctor.doctor_second_name[0]}")
        patients = PatientModel.select()
        patient_list = ["не выбрано"]
        for patient in patients:
            patient_list.append(f"{patient.patient_family} {patient.patient_name[0]} {patient.patient_second_name[0]}")
        self.comboBox.addItems(doctor_list)
        self.comboBox_2.addItems(patient_list)
        self.pushButton.clicked.connect(self.get_file_path)
        self.pushButton_2.clicked.connect(self.load_model)
        self.pushButton_3.clicked.connect(self.save_to_card)
        self.pushButton_4.clicked.connect(self.close)

    def closeEvent(self, event):
        # При закрытии формы показываем родительское окно (вторую форму)
        if self.parent:
            self.parent.reopen()  # Используйте метод reopen() для показа второй формы
        event.accept()

    def save_to_card(self):
        """
        Метод для сохранения осмотра в бд
        :return: ничего не возвращает
        """
        anomaly_file_name = "cam.jpg"
        if not os.path.exists(anomaly_file_name):
            msg = QMessageBox()
            msg.setIcon(QMessageBox.Critical)
            msg.setText("Ошибка")
            msg.setInformativeText('Сначала проведите анализ')
            msg.setWindowTitle("Error")
            msg.exec_()
            return
        start_file_name = self.label_8.text()
        if len(start_file_name) == 0:
            msg = QMessageBox()
            msg.setIcon(QMessageBox.Critical)
            msg.setText("Ошибка")
            msg.setInformativeText('Сначала проведите анализ')
            msg.setWindowTitle("Error")
            msg.exec_()
            return
        selected_doctor_id = self.comboBox.currentIndex()  # Получить выбранный ID врача
        if selected_doctor_id == 0:
            msg = QMessageBox()
            msg.setIcon(QMessageBox.Critical)
            msg.setText("Ошибка")
            msg.setInformativeText('Выберите врача')
            msg.setWindowTitle("Error")
            msg.exec_()
            return
        selected_patient_id = self.comboBox_2.currentIndex()  # Получить выбранный ID пациента
        if selected_doctor_id == 0:
            msg = QMessageBox()
            msg.setIcon(QMessageBox.Critical)
            msg.setText("Ошибка")
            msg.setInformativeText('Выберите пациента')
            msg.setWindowTitle("Error")
            msg.exec_()
            return
        visit_date = self.label_3.text()  # Форматируем дату как строку
        date_match = re.search(r'\d{4}-\d{2}-\d{2}', visit_date)
        diagnose = self.label_7.text()
        if len(diagnose) == 0:
            msg = QMessageBox()
            msg.setIcon(QMessageBox.Critical)
            msg.setText("Ошибка")
            msg.setInformativeText('Сначала проведите анализ')
            msg.setWindowTitle("Error")
            msg.exec_()
            return
        diagnose_bool = False
        if date_match:
            date_str = date_match.group()
        if "мочекаменная" in diagnose:
            diagnose_text = "мочекаменная болезнь"
            mkb = "N20"
            diagnose_bool = True
        else:
            diagnose_text = "здоров"
            mkb = "здоров"
        fin = open(start_file_name, "rb")
        img = fin.read()
        binary = psycopg2.Binary(img)
        fin.close()

        fin = open(anomaly_file_name, "rb")
        img = fin.read()
        binary1 = psycopg2.Binary(img)
        fin.close()

        try:
            # Попытка найти существующую карту пациента
            card = PatientsCardsModel.get(
                PatientsCardsModel.patient_card_patient_id == selected_patient_id,
                PatientsCardsModel.patient_card_doctor_id == selected_doctor_id
            )
            # Если карта найдена, обновляем её данные
            card.card_creation_date = date_str
            card.diagnose = diagnose_text
            card.mkb_diagnose = mkb
            card.start_image = binary
            card.anomaly_image = binary1
            card.save()
            print("Существующая карта обновлена.")
        except DoesNotExist:
            # Если карта не найдена, создаём новую
            new_card = PatientsCardsModel.create(
                patient_card_patient_id=selected_patient_id,
                patient_card_doctor_id=selected_doctor_id,
                card_creation_date=date_str,
                diagnose=diagnose_text,
                mkb_diagnose=mkb,
                start_image=binary,
                anomaly_image=binary1
            )
            print("Новая карта успешно добавлена в базу данных.")
        os.remove(anomaly_file_name)
        # Обновление данных пациента (если необходимо)
        try:
            patient = PatientModel.get_by_id(selected_patient_id)
            patient.patient_analyses_count += 1  # Например, обновляем количество анализов
            patient.patient_has_kidney_stone = diagnose_bool
            patient.save()
        except DoesNotExist:
            print("Пациент не найден в базе данных.")

    def get_file_path(self):
        """
        Метод для получения пути к выбранному для анализа файлу.
        :return: ничего не возвращает
        """
        self.label_7.clear()
        self.label_5.clear()
        file_name = QFileDialog.getOpenFileName(self, 'Open file',
                                                '"C:/Users/nero1"')[0]
        # Вызов метода для вывода изображения\
        self.label_8.setText(file_name)
        self.print_image()

    def print_image(self):
        """
        Метод для отображения выбранного пользователем изображения.
        :return: ничего не возвращает
        """
        file_name = self.label_8.text()
        self.pixmap = QPixmap(file_name)
        self.pixmap = self.pixmap.scaled(201, 221)

        # Добавление изображения в поле
        self.label_5.setPixmap(self.pixmap)

    def result_implementation(self, predict_classes):
        """
        Метод для имплементации результатов работы нейронной сети
        :param predict_classes: хранит класс предсказанный нейронной сетью
        :param classes: список, хранит возможный набор классов [здоров, лейкемия]
        :return:
        """
        if ((predict_classes > 0.75) * 1):
            self.label_7.setText(f'Состояние почек в норме')
        else:
            self.label_7.setText(f'У пациента мочекаменная болезнь')
        current_date = datetime.now()
        formatted_date = current_date.strftime('%Y-%m-%d')
        self.label_3.setText(f"Дата обследования {formatted_date}")

    def load_model(self):
        """
        Метод для загрузки и использования модели, модель загружается в память только при первом вызове метода.
        :return:
        """
        file_name = self.label_8.text()
        global saved_model, normal_data, img
        classes = ['мочекамення болезнь', 'здоров']
        model_k = 0
        img_size = 128

        # Проверка загружена ли модель в память
        if model_k == 0:
            saved_model = tf.keras.models.load_model("kidney_stones_model.h5")
            model_k += 1

        # Пред обработка выбранного пользователем изображения для классификации, если файла не существует по пути,
        # вызывается исключение
        try:
            img = cv2.imread(file_name)
            img = cv2.resize(img, (img_size, img_size))
            img = np.expand_dims(img, axis=0)
        except Exception as e:
            print(e)
        pred = saved_model.predict(img)
        self.result_implementation(pred)

        tf.compat.v1.disable_eager_execution()
        saved_model = tf.keras.models.load_model("kidney_stones_model.h5")
        model_wo_softmax = keras.models.Model(inputs=saved_model.inputs,
                                              outputs=saved_model.layers[-2].output)
        analyzer = innvestigate.create_analyzer("integrated_gradients", model_wo_softmax)

        X = load_and_preprocess_image(file_name)
        relevances = analyzer.analyze(X)
        relevance = relevances[0]  # Берем релевантность для первого (и единственного) образца
        relevance = np.squeeze(relevance)  # Убираем лишние измерения

        plt.ioff()

        # Создаем изображение, как обычно, с использованием цветовой карты
        plt.imshow(relevance, cmap='magma')
        # Сохраняем изображение в файл, не отображая его
        plt.savefig("cam.jpg")
        plt.close()  # Закрываем фигуру
        file_name = "cam.jpg"
        self.pixmap = QPixmap(file_name)
        self.pixmap = self.pixmap.scaled(201, 221)

        # Добавление изображения в поле
        self.label_6.setPixmap(self.pixmap)
