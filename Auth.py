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
        self.ui = ui_admin(self)
        self.ui.setupUi()
        self.hide()

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
