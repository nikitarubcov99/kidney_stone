import os
import sys
from PyQt5 import QtCore, QtWidgets, uic
from PyQt5.QtGui import QPixmap
from PyQt5.QtWidgets import QApplication, QMainWindow, QTableWidget, QFileDialog, QLabel, \
    QPushButton, QProgressBar, QLineEdit, QTextEdit, QMessageBox, QDialog, QWidget
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
from datetime import datetime, date
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


def validate_snils_format(snils):
    """
    Функция для валидации введенного пользователем СНИЛСА
    :param snils: принимает СНИЛС в текстовом представлении
    :return: возвращает True, если СНИЛС введен корректно, иначе False
    """
    pattern = re.compile(r'^\d{3}-\d{3}-\d{3} \d{2}$')

    # Сопоставление шаблона с введённым СНИЛС
    if pattern.match(snils):
        return True  # СНИЛС соответствует формату
    else:
        return False


def load_and_preprocess_image(img_path):
    """
    Функция для загрузки и предобработки изображения, необходима для работы Layer-Wise Relevance Propagation
    :param img_path:получает на вход путь к изображению
    :return:возвращает предобработанное изображение
    """
    img = image.load_img(img_path, target_size=(128, 128))
    x = image.img_to_array(img)
    x = np.expand_dims(x, axis=0)
    x = preprocess_input(x)
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
    pdf_document = fitz.open(pdf_path)
    pdf_document[page_number].insert_image(fitz.Rect(30, 285, 230, 485), stream=open(image_path, "rb").read())
    pdf_document[page_number].insert_image(fitz.Rect(330, 285, 530, 485), stream=open(image_path1, "rb").read())
    pdf_document.saveIncr()
    pdf_document.close()


def get_patient_info(patient_id):
    """
    Функция для получения информации о пациенте из БД по id пациента
    :param patient_id: Принимает на вход id пациента
    :return: Возвращает словарь, содержащий информацию о пациенте
    """
    try:
        patient = PatientModel.get_by_id(patient_id)
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
    """
    Функция для получения информации о враче из БД по id врача
    :param doctor_id: Принимает на вход id врача
    :return: Возвращает словарь, содержащий информацию о враче
    """
    try:
        doctor = DoctorModel.get_by_id(doctor_id)
        return {
            "Фамилия": doctor.doctor_family,
            "Имя": doctor.doctor_name,
            "Отчество": doctor.doctor_second_name,
            "Категория": doctor.doctor_class
        }
    except DoctorModel.DoesNotExist:
        return "Врач с таким ID не найден."


class PatientDetailsWindow(QDialog):
    """
    Класс для создания окна подробной информации о карте пациента.
    """
    def __init__(self, card_id, parent=None):
        """
        Конструктор класса.
        :param card_id: Принимает id карты пациента для отображения.
        :param parent: Принимает родительскую форму, для переотрисовки родительской при закрытии этой.
        """
        super().__init__(parent)
        self.card_id = card_id
        self.card = None
        self.init_ui()
        self.fill_data()
        self.parent = parent

    def init_ui(self):
        """
        Метод инициализации и отрисовки окна карты.
        :return: Ничего не возвращает.
        """
        uic.loadUi('ui/Card.ui', self)
        self.pushButton.clicked.connect(self.generate_pdf)
        self.pushButton_3.clicked.connect(self.close)

    def closeEvent(self, event):
        """
        Метод для обработки события закрытия формы.
        :param event: Принимает событие закрытия формы.
        :return: Ничего не возвращает.
        """
        if self.parent:
            self.parent.reopen()
        event.accept()

    def generate_pdf(self):
        """
        Метод для создания pdf файла с отчетом
        :return: ничего не возвращает
        """
        pdf = FPDF()
        pdf.add_page()
        font_path = 'fonts/timesnrcyrmt.ttf'
        pdf.add_font("Times", "", font_path, uni=True)
        pdf.set_font("Times", size=14)
        snils = self.label_16.text()
        snils_full_string = snils  # Ваша строка с СНИЛС
        snils_number = re.search(r'\d{3}-\d{3}-\d{3} \d{2}', snils_full_string)
        if snils_number:
            snils_number = snils_number.group()
        else:
            snils_number = "Не найден"
        for patient in PatientModel.select().where(PatientModel.patient_snils == snils_number):
            patient_id = patient.patient_id
            patient_name = patient.patient_name
            patient_second_name = patient.patient_second_name
            patient_family = patient.patient_family
            patient_age = patient.patient_age
            patient_count = patient.patient_analyses_count
        for card in PatientsCardsModel.select().where(PatientsCardsModel.patient_card_patient_id == patient_id):
            doctor_id = card.patient_card_doctor_id
            diagnose = card.diagnose
            mkb_diagnose = card.mkb_diagnose
            card_creation_date = card.card_creation_date
            start_image = card.start_image
            anomaly_image = card.anomaly_image
        for doctor in DoctorModel.select().where(DoctorModel.doctor_id == doctor_id):
            doctor_name = doctor.doctor_name
            doctor_second_name = doctor.doctor_second_name
            doctor_family = doctor.doctor_family
            doctor_class = doctor.doctor_class

        current_datetime = datetime.now()
        current_date_str = current_datetime.strftime("%Y-%m-%d")
        intro = '            Отчет об анализе на наличие лейкемии по пятну крови'.encode('utf-8')
        fio_intro = 'Данные пациента: '.encode('utf-8')
        patient_fio = f'Фамилия: {patient_family}   Имя: {patient_name}   Отчество: {patient_second_name}      полных лет: {patient_age}'.encode(
            'utf-8')
        patient = f'СНИЛС: {snils_number}     диагноз по МКБ-10: {mkb_diagnose}     кол-во анализов {patient_count}'.encode(
            'utf-8')
        doctor_intro = 'Информация о лечащем враче: '.encode('utf-8')
        doctor_fio = f'Фамилия: {doctor_family}   Имя: {doctor_name}   Отчество: {doctor_second_name}'.encode(
            'utf-8')
        doctor_cat = f'Категория лечащего врача: {doctor_class}'.encode('utf-8')
        image_intro_norm = 'Изначальное изображение                          Изображение с аномалиями'.encode('utf-8')
        if 'мочекаменная' in diagnose:
            analys_result = '              При анализе обнаружена мочекаменная болезнь'.encode('utf-8')
        else:
            analys_result = '                              Заболеваний не обнаружено'.encode('utf-8')
        open_date = f'Дата создания карточки {card_creation_date}                       Дата осмотра {current_date_str}'.encode(
            'utf-8')
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
        pdf.ln(10)
        pdf.set_font("Times", size=16)
        pdf.multi_cell(400, 10, str(image_intro_norm.decode('utf-8')))
        pdf.set_font("Times", size=18)
        pdf.ln(75)
        pdf.multi_cell(400, 10, str(analys_result.decode('utf-8')))
        pdf.set_font("Times", size=14)
        pdf.multi_cell(400, 10, str(open_date.decode('utf-8')))
        pdf_path = f"reports/{patient_family} {patient_name[0]}. {patient_second_name[0]}.  {current_date_str}.pdf"
        pdf.output(pdf_path)
        start_image_blob = start_image
        anomaly_image_blob = anomaly_image
        with open('start_image.png', 'wb') as f:
            f.write(start_image_blob)
        with open('anomaly_image.png', 'wb') as f:
            f.write(anomaly_image_blob)
        image_path = "C:/Users/dmitr/PycharmProjects/kidney_stone/start_image.png"
        image_path1 = "C:/Users/dmitr/PycharmProjects/kidney_stone/anomaly_image.png"
        existing_pdf_path = pdf_path
        target_page_number = 0
        add_image_to_existing_pdf(existing_pdf_path, image_path, image_path1, target_page_number)
        os.remove(image_path1)
        os.remove(image_path)

    def fill_data(self):
        """
        Метод для заполнения формы карточки пациента.
        :return: Ничего не возвращает.
        """
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
            file_name = "C:/Users/dmitr/PycharmProjects/kidney_stone/image_from_db.jpg"
            self.pixmap = QPixmap(file_name)
            self.pixmap = self.pixmap.scaled(241, 221)
            self.label_10.setPixmap(self.pixmap)
            os.remove(file_name)
        if self.card.anomaly_image:
            with open("image_from_db1.jpg", "wb") as file:
                file.write(self.card.anomaly_image)
                file.close()
            file_name = "C:/Users/dmitr/PycharmProjects/kidney_stone/image_from_db1.jpg"
            self.pixmap = QPixmap(file_name)
            self.pixmap = self.pixmap.scaled(241, 221)
            self.label_11.setPixmap(self.pixmap)
            os.remove(file_name)


class ui_doctor(QMainWindow):
    """
    Класс реализующий инициализацию компонентов и дальнейшее взаимодействие с окном программы "создание отчета"
    """

    def __init__(self, parent=None, login=None):
        """
        Консструктор класса
        """
        super().__init__(parent)
        self.parent = parent
        self.login = login
        self.setupUi()

    def setupUi(self):
        """
        Метод для загрузки компонент интерфейса из ui файла
        :return: ничего не возвращает
        """
        uic.loadUi('ui/main_doctor.ui', self)
        self.tableWidget.setColumnWidth(3, 450)

        self.tableWidget.setHorizontalHeaderLabels(["ФИО", "Статус", "Дата", "Просмотр"])
        self.show_list()
        self.pushButton.clicked.connect(self.openAddVisitForm)
        self.pushButton_2.clicked.connect(self.close)
        self.show()

    def reopen(self):
        """
        Метод необходим для реализации переоткрытия окон при закрытии последующих.
        :return: Ничего не возвращает.
        """
        self.show_list()
        self.show()

    def closeEvent(self, event):
        """
        Обработка события закрытия формы.
        :param event: Принимает событие закрытия формы.
        :return: Ничего не возвращает.
        """
        if self.parent:
            self.parent.show()
        super().closeEvent(event)

    def show_list(self):
        """
        Метод для отображения списка карт на форме.
        :return: Ничего не возвращает.
        """
        user = UserModel.get(UserModel.user_login == self.login)
        doctor_id = user.doctor_id
        patient_cards = PatientsCardsModel.select().where(PatientsCardsModel.patient_card_doctor_id == doctor_id)
        doctor = DoctorModel.get_by_id(doctor_id)
        self.label.setText(f"{doctor.doctor_family} {doctor.doctor_name[0]}. {doctor.doctor_second_name[0]}.")
        self.tableWidget.setRowCount(patient_cards.count())
        for row, card in enumerate(patient_cards):
            patient = card.patient_card_patient_id
            fio = f"{patient.patient_family} {patient.patient_name[0]}.{patient.patient_second_name[0]}."
            self.tableWidget.setItem(row, 0, QTableWidgetItem(fio))
            self.tableWidget.setItem(row, 1, QTableWidgetItem(card.diagnose))
            self.tableWidget.setItem(row, 2, QTableWidgetItem(str(card.card_creation_date)))
            btn_view = QPushButton('Просмотр', self)
            btn_view.clicked.connect(lambda *args, card=card: self.view_card_details(card))
            self.tableWidget.setCellWidget(row, 3, btn_view)

    def view_card_details(self, card):
        """
        Метод для взаимодействия с кнопкой просмотра в таблице карт.
        :param card: Получает на вход карту которую нужно отобразить.
        :return: Ничего не возвращает.
        """
        self.details_window = PatientDetailsWindow(card, self)
        self.details_window.fill_data()
        self.details_window.show()
        self.hide()

    def openAddVisitForm(self):
        """
        Метод для открытия формы добавления посещения.
        :return: Ничего не возвращает.
        """
        self.addVisitForm = AddVisitForm(self)
        self.addVisitForm.show()
        self.hide()


class AddVisitForm(QMainWindow):
    """
    Класс для добавления посещения в БД
    """
    def __init__(self, parent=None):
        """
        Конструктор класса.
        :param parent: Принимает родительскую форму, для переотрисовки родительской при закрытии этой.
        """
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
        """
        Метод для реализации возможности переоткрытия формы.
        :param event: Принимает на вход событие закрытия формы.
        :return: Ничего не возвращает.
        """
        if self.parent:
            self.parent.reopen()
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
        selected_doctor_id = self.comboBox.currentIndex()
        if selected_doctor_id == 0:
            msg = QMessageBox()
            msg.setIcon(QMessageBox.Critical)
            msg.setText("Ошибка")
            msg.setInformativeText('Выберите врача')
            msg.setWindowTitle("Error")
            msg.exec_()
            return
        selected_patient_id = self.comboBox_2.currentIndex()
        if selected_doctor_id == 0:
            msg = QMessageBox()
            msg.setIcon(QMessageBox.Critical)
            msg.setText("Ошибка")
            msg.setInformativeText('Выберите пациента')
            msg.setWindowTitle("Error")
            msg.exec_()
            return
        visit_date = self.label_3.text()
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
            card = PatientsCardsModel.get(
                PatientsCardsModel.patient_card_patient_id == selected_patient_id,
                PatientsCardsModel.patient_card_doctor_id == selected_doctor_id
            )
            card.card_creation_date = date_str
            card.diagnose = diagnose_text
            card.mkb_diagnose = mkb
            card.start_image = binary
            card.anomaly_image = binary1
            card.save()
            print("Существующая карта обновлена.")
        except DoesNotExist:
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
        try:
            patient = PatientModel.get_by_id(selected_patient_id)
            patient.patient_analyses_count += 1
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
                                                '"C:/Users/dmitr"')[0]
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
        :return:
        """
        if (predict_classes > 0.75) * 1:
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
        if model_k == 0:
            saved_model = tf.keras.models.load_model("kidney_stones_model.h5")
            model_k += 1
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
        relevance = relevances[0]
        relevance = np.squeeze(relevance)
        plt.ioff()
        plt.imshow(relevance, cmap='magma')
        plt.savefig("cam.jpg")
        plt.close()
        file_name = "cam.jpg"
        self.pixmap = QPixmap(file_name)
        self.pixmap = self.pixmap.scaled(201, 221)
        self.label_6.setPixmap(self.pixmap)
