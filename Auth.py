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
    """
    Метод для реализации авторизации.
    :param login: Принимает на вход логин пользователя.
    :param password: Принимает на вход пароль пользователя.
    :return: Возвращает пользователя из БД или None если такого пользователя нет.
    """
    try:
        player = UserModel.select().where(
            UserModel.user_login == login and UserModel.user_password == password).get()
        return player
    except Exception as error:
        return None


class Window(QMainWindow, QTableWidget):
    """
    Класс окна авторизации
    """
    def __init__(self):
        """
        Конструктор класса.
        """
        super().__init__()
        uic.loadUi('ui/Login.ui', self)
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

    def openMainDoctor(self, login):
        """
        Метод для инициализации окна программы для создания отчета
        :return: ничего не возвращает
        """
        self.ui = ui_doctor(login=login)

    def login_event(self):
        login = self.lineEdit.text()
        if len(login) == 0:
            msg = QMessageBox()
            msg.setIcon(QMessageBox.Critical)
            msg.setText("Ошибка")
            msg.setInformativeText('Не заполнено поле логин')
            msg.setWindowTitle("Error")
            msg.exec_()
            return
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
            msg.setInformativeText('Неверный логин или пароль')
            msg.setWindowTitle("Error")
            msg.exec_()
        elif user.superuser == True:
            self.openMainAdmin()
        elif user.superuser == False:
            self.openMainDoctor(login=login)

    @staticmethod
    def exit_app():
        """
        Метод для закрытия приложения.
        :return:
        """
        QApplication.quit()


App = QApplication(sys.argv)
App.setStyleSheet("QLabel{font-size: 14pt;}")

window = Window()

# Запуск приложения
sys.exit(App.exec())
