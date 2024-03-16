import sys
from models import *
import cv2
import numpy as np
import tensorflow as tf
from PyQt5 import QtCore, QtWidgets, uic
from PyQt5.QtGui import QPixmap
from PyQt5.QtWidgets import QApplication, QMainWindow, QTableWidget, QFileDialog, QLabel, \
    QPushButton, QMessageBox
from main_admin import *
from main_doctor import *
from models.models import UserModel


def loginByBD(login, password):
    try:
        player = UserModel.select().where(
            UserModel.user_login == login and UserModel.user_password == password).get()
        return player
    except Exception as error:
        return None

class Window(QMainWindow, QTableWidget):
    def __init__(self):
        super().__init__()
        uic.loadUi('ui/Login.ui', self)
        # Инициализация основного окна программы и его компонентов
        self.pixmap = None
        self.showDialog = None
        self.file_name = None
        self.acceptDrops()
        self.setWindowTitle("Login")
        self.show()
        self.pushButton.clicked.connect(self.login_event)
        self.pushButton_2.clicked.connect(self.exit_app)


    def openMainAdmin(self):
        """
        Метод для инициализации окна программы для создания отчета
        :return: ничего не возвращает
        """
        self.ui = ui_admin()
        self.ui.setupUi()

    def openMainDoctor(self):
        """
        Метод для инициализации окна программы для создания отчета
        :return: ничего не возвращает
        """
        self.ui = ui_doctor()
        self.ui.setupUi()


    def login_event(self):
        # Обработка логина
        login = self.lineEdit.text()
        if len(login) == 0:
            msg = QMessageBox()
            msg.setIcon(QMessageBox.Critical)
            msg.setText("Ошибка")
            msg.setInformativeText('Не заполнено поле логин')
            msg.setWindowTitle("Error")
            msg.exec_()
            return
        # Обработка пароля
        password = self.lineEdit_2.text()
        if len(password) == 0:
            msg = QMessageBox()
            msg.setIcon(QMessageBox.Critical)
            msg.setText("Ошибка")
            msg.setInformativeText('Не заполнено поле пароль')
            msg.setWindowTitle("Error")
            msg.exec_()
            return
        user = loginByBD(login, password)
        if user is None:
            msg = QMessageBox()
            msg.setIcon(QMessageBox.Critical)
            msg.setText("Ошибка")
            msg.setInformativeText('Нет такого пользователя')
            msg.setWindowTitle("Error")
            msg.exec_()
        elif user.superuser == True:
            self.openMainAdmin()
        elif user.superuser == False:
            self.openMainDoctor()




    def get_file_path(self):
        """
        Метод для получения пути к выбранному для анализа файлу.
        :return:
        """
        self.label.clear()
        self.label1.clear()
        file_name = QFileDialog.getOpenFileName(self, 'Open file',
                                                '"C:/Users/nero1/zhenya"')[0]
        # Вызов метода для вывода изображения
        self.print_image(file_name)
        # Вызов метода для классификации пневмонии на изображении
        self.load_model(file_name)

    def print_image(self, file_name):
        """
        Метод для отображения выбранного пользователем изображения.
        :param file_name: указывает путь к выбранному файлу.
        :return:
        """
        self.pixmap = QPixmap(file_name)
        self.pixmap = self.pixmap.scaled(400, 400)

        # Добавление изображения в поле
        self.label.setPixmap(self.pixmap)

    def result_implementation(self, predict_classes):
        """
        Метод для интрпритации численного результата работы нейронной сети.
        :param predict_classes: хранит предсказанный для выбранного изображения класс.
        :return:
        """
        if predict_classes[0] == 0:
            self.label1.setText('Обнаружена пневмония')
        else:
            self.label1.setText('Патологий необнаружено')

    def load_model(self, file_name):
        """
        Метод для загрузки и использования модели, модель загружается в память только при первом вызове метода.
        :param file_name: хранит путь к файлу выбранному пользователем для анализа.
        :return:
        """
        global saved_model, normal_data
        model_k = 0
        data = []
        img_size = 150

        # Проверка загружена ли модель в память
        if model_k == 0:
            saved_model = tf.keras.models.load_model("pneumonia_classify")
            model_k += 1

        # Предобработка выбранного пользователем изображения для классификации, если файла не существует по пути,
        # вызывается исключение
        try:
            img_arr = cv2.imread(file_name, cv2.IMREAD_GRAYSCALE)
            resized_arr = cv2.resize(img_arr, (img_size, img_size))
            data.append(resized_arr)
            normal_data = np.array(data)
            normal_data = np.array(normal_data) / 255
            normal_data = normal_data.reshape(-1, img_size, img_size, 1)
        except Exception as e:
            print(e)

        # Использование модели для классификации выбранного пользователем изображения
        predict = saved_model.predict(normal_data)
        predict_classes = np.argmax(predict, axis=1)

        # Вызов метода для интерпритации результатов работы модели
        self.result_implementation(predict_classes)

    @staticmethod
    def exit_app():
        """
        Метод для закрытия приложения.
        :return:
        """
        QApplication.quit()


# Объявления приложения PyQt
App = QApplication(sys.argv)
App.setStyleSheet("QLabel{font-size: 14pt;}")

# Создание экземпляра главного окна программы
window = Window()

# Запуск приложения
sys.exit(App.exec())
