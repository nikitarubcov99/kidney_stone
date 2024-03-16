import os
import sys
from PyQt5 import QtCore, QtWidgets, uic
from PyQt5.QtGui import QPixmap
from PyQt5.QtWidgets import QApplication, QMainWindow, QTableWidget, QFileDialog, QLabel, \
    QPushButton, QProgressBar, QLineEdit, QTextEdit, QMessageBox, QDialog, QWidget, QVBoxLayout
import cv2
import keras
import matplotlib
import numpy as np
import psycopg2
import tensorflow as tf
from keras.applications import EfficientNetB3
from keras.applications.efficientnet import preprocess_input
from keras.preprocessing import image

class ui_admin(QMainWindow):
    """
    Класс реализующий инициализацию компонентов и дальнейшее взаимодействие с окном программы "создание отчета"
    """

    def __init__(self):
        """
        Консструктор класса
        """
        super().__init__()
        self.setupUi()

    def setupUi(self):
        """
        Метод для загрузки компонент интерфейса из ui файла
        :return: ничего не возвращает
        """
        uic.loadUi('ui/main_admin.ui', self)
        self.tableWidget.setColumnWidth(2, 450)

        self.tableWidget.setHorizontalHeaderLabels(["Дата", "Пациент", "Инфо", "Просмотр"])
        self.pushButton.clicked.connect(self.openAddVisitForm)
        self.pushButton_2.clicked.connect(self.openAddDoctorForm)
        self.show()

    def openAddDoctorForm(self):
        self.addDoctorForm = AddDoctorForm()
        self.addDoctorForm.show()

    def openAddVisitForm(self):
        self.addVisitForm = AddVisitForm()
        self.addVisitForm.show()


class AddDoctorForm(QMainWindow):
    def __init__(self):
        super(AddDoctorForm, self).__init__()
        uic.loadUi('ui/add_doctor.ui', self)
        categories = ["Без категории", "Вторая", "Первая", "Высшая"]
        self.comboBox.addItems(categories)


class AddVisitForm(QMainWindow):
    def __init__(self):
        super(AddVisitForm, self).__init__()
        uic.loadUi('ui/add_visit.ui', self)
        categories = ["Без категории", "Вторая", "Первая", "Высшая"]
        self.comboBox.addItems(categories)
        self.comboBox.addItems(categories)
        self.pushButton.clicked.connect(self.get_file_path)

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
        # Вызов метода для классификации пневмонии на изображении
        # self.load_model(file_name)

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

    def result_implementation(self, predict_classes, classes):
        """
        Метод для имплементации результатов работы нейронной сети
        :param predict_classes: хранит класс предсказанный нейронной сетью
        :param classes: список, хранит возможный набор классов [здоров, лейкемия]
        :return:
        """
        self.progressBar.setValue(6)
        index = np.argmax(predict_classes[0])
        klass = classes[index]
        probability = predict_classes[0][index] * 100
        if index == 0:
            self.label_2.setText(f'С вероятностью {probability:6.2f} % пациент {klass}')

        else:
            self.label_2.setText(f'С вероятностью {probability:6.2f} % на изображении {klass}')
        self.progressBar.setValue(7)

    def load_model(self):
        """
        Метод для загрузки и использования модели, модель загружается в память только при первом вызове метода.
        :return:
        """
        file_name = self.label_13.text()
        global saved_model, normal_data, img
        classes = ['здоров', 'лейкимия']
        model_k = 0
        img_size = 224

        # Проверка загружена ли модель в память
        if model_k == 0:
            saved_model = tf.keras.models.load_model("model/model.h5")
            model_k += 1

        # Пред обработка выбранного пользователем изображения для классификации, если файла не существует по пути,
        # вызывается исключение
        try:
            img = cv2.imread(file_name)
            img = cv2.resize(img, (img_size, img_size))
            img = np.expand_dims(img, axis=0)
        except Exception as e:
            print(e)
        # Использование модели для классификации выбранного пользователем изображения
        pred = saved_model.predict(img)
        # Вызов метода для интерпретации результатов работы модели
        self.result_implementation(pred, classes)