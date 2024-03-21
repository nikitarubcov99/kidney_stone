from peewee import *
from datetime import datetime

pg_db = PostgresqlDatabase('kidney_stone', user='postgres', password='123',
                           host='localhost', port=5432)


class BaseModel(Model):
    class Meta:
        database = pg_db


class DoctorModel(BaseModel):
    doctor_id = IdentityField()
    doctor_name = CharField(null=False, max_length=32)
    doctor_second_name = CharField(null=False, max_length=32)
    doctor_family = CharField(null=False, max_length=32)
    doctor_class = CharField(null=False, default='вторая категория')

    class Meta:
        db_table = "doctors"
        order_by = ('doctor_id',)


class PatientModel(BaseModel):
    patient_id = IdentityField()
    patient_name = CharField(null=False, max_length=32)
    patient_second_name = CharField(null=False, max_length=32)
    patient_family = CharField(null=False, max_length=32)
    patient_age = IntegerField(null=False, default=0)
    patient_birth_date = DateField(null=False, default=datetime.now())
    patient_snils = CharField(null=False, unique=True, max_length=15)
    patient_has_kidney_stone = BooleanField(null=False, default=False)
    patient_analyses_count = IntegerField(null=False, default=0)
    responsible_doctor = ForeignKeyField(DoctorModel, backref='patients', on_delete='CASCADE')

    class Meta:
        db_table = "patients"
        order_by = ('patient_id',)


class PatientsCardsModel(BaseModel):
    card_id = IdentityField()
    patient_card_patient_id = ForeignKeyField(PatientModel, backref='patients', to_field='patient_id',
                                              on_delete='cascade',
                                              on_update='cascade')
    patient_card_doctor_id = ForeignKeyField(DoctorModel, backref='doctors', to_field='doctor_id', on_delete='cascade',
                                             on_update='cascade')
    card_creation_date = DateField(null=False, default=datetime.now())
    diagnose = CharField(null=False, default='нет заболевания')
    mkb_diagnose = CharField(max_length=6)
    start_image = BlobField(null=True)
    anomaly_image = BlobField(null=True)

    class Meta:
        db_table = 'cards'
        order_by = ('card_id',)


class UserModel(BaseModel):
    user_id = IdentityField()
    user_login = CharField(null=False, max_length=32)
    user_password = CharField(null=False, max_length=32)
    superuser = BooleanField(null=False)  # False - doctor, True - admin
    doctor = ForeignKeyField(DoctorModel, backref='user', null=True)

    class Meta:
        db_table = 'users'
        order_by = ('user_id',)


# DoctorModel.create_table()
# PatientModel.create_table()
# PatientsCardsModel.create_table()
# UserModel.create_table()

# DoctorModel.create(doctor_name='Иван', doctor_second_name='Иванович', doctor_family='Иванов', doctor_class='высшая категория')
# UserModel.create(user_login='admin', user_password='admin', superuser=True)
# UserModel.create(user_login='doctor', user_password='doctor', superuser=False, doctor=1)
# PatientModel.create(patient_name = 'Петр', patient_second_name='Петрович', patient_family='Петров', patient_age=21, patient_birth_date=datetime(2003, 1, 1), patient_snils="123-456-789 00",
#                     patient_has_kidney_stone=False, patient_analyses_count=0, responsible_doctor = 1)
