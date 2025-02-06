from app import app
from dotenv import load_dotenv
import os 
load_dotenv()
app.config['SQLALCHEMY_DATABASE_URI']=os.getenv('SQLALCHEMY_DATABASE_URI')
app.config['SQLALCHEMY_TRACK_MODIFICATIONS']=os.getenv('SQLALCHEMY_TRACK_MODIFICATIONS')
app.config['SECRET_KEY']=os.getenv('SECRET_KEY')
app.config['UPLOAD_FOLDER']=os.path.join(os.path.dirname(os.path.abspath(__file__)),'static/profile')