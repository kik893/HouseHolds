from flask import  Flask 
from flask_sqlalchemy import SQLAlchemy
app = Flask(__name__)

app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///test.db'


db=SQLAlchemy(app)

import config

import models

import routes