import os

class Config:
    SECRET_KEY = os.environ.get('SECRET_KEY') or 'your-secret-key'
    SQLALCHEMY_DATABASE_URI = 'mysql+mysqlconnector://root:abcd1234@localhost/expense_tracker'
    SQLALCHEMY_TRACK_MODIFICATIONS = False