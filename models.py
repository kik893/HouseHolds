from flask import Flask,request,current_app
from werkzeug.utils import secure_filename
from flask_sqlalchemy import SQLAlchemy
from sqlalchemy import Column, DateTime

from app import app,db
from datetime import datetime,timedelta
from werkzeug.security import generate_password_hash
import os
import pytz
from sqlalchemy.orm import validates

class Admin(db.Model):
    id = db.Column(db.Integer,primary_key=True) 
    username = db.Column(db.String(32),unique=True,nullable=False)
    email=db.Column(db.String(32),nullable=False)
    password=db.Column(db.String(50),nullable=False)
    gender=db.Column(db.String(10),nullable=False)

    
   

class Service(db.Model):
    id = db.Column(db.Integer,primary_key=True)
    name = db.Column(db.String(32),nullable=False)
    description = db.Column(db.Text, nullable=False)
    admin_id=db.Column(db.Integer,db.ForeignKey('admin.id'),nullable=False)
    packages = db.relationship('Package', backref='service', lazy=True)

class Package(db.Model):
    id = db.Column(db.Integer,primary_key=True)
    service_id = db.Column(db.Integer,db.ForeignKey('service.id'),nullable=False)
    name = db.Column(db.String(32),nullable=False)
    base_price=db.Column(db.Integer,nullable=False)
    package_type=db.Column(db.String(32),nullable=False)
    admin_id=db.Column(db.Integer,db.ForeignKey('admin.id'),nullable=False)
    rating = db.Column(db.Float, default=0, nullable=False)
    time_required = db.Column(db.Integer, nullable=False)  # time in hours
    status = db.Column(db.String(50),default='available')
    bookings = db.relationship('Booking', backref='package', lazy=True)

    @staticmethod
    def update_package_rating(package_id):
        package = Package.query.get(package_id)
        if package:
            # Calculate the new average rating
            ratings = Rating.query.filter_by(package_id=package_id).all()
            if ratings:
                rating = sum(rating.package_rating for rating in ratings) / len(ratings)
                package.rating = rating  # Ensure you have this field in your model
                db.session.commit()

class Professional(db.Model):
    id = db.Column(db.Integer,primary_key=True)
    name=db.Column(db.String(32),unique=False,nullable=False)
    username = db.Column(db.String(32),unique=True,nullable=False)
    email=db.Column(db.String(32),nullable=False)
    password=db.Column(db.String(50),nullable=False)
    gender=db.Column(db.String(10),nullable=False)
    phone=db.Column(db.Integer,nullable=False)
    experience=db.Column(db.Integer,nullable=False)
    service_type = db.Column(db.String(30),nullable=False)

    resume=db.Column(db.String(200),nullable=False)
    location = db.Column(db.String(50),nullable=False)
    pincode=db.Column(db.Integer,nullable=False)
    status = db.Column(db.String(20), nullable=False, default='pending')  # added status column
    is_flag=db.Column(db.Boolean,default=False,nullable=False) 
    rating = db.Column(db.Float, default=0,nullable=False)
    bookings = db.relationship('Booking', backref='professional', lazy=True)


    def set_resume(self, resume):
        filename = secure_filename(resume.filename)
        resume.save(os.path.join(current_app.root_path, 'static', 'uploads', filename))
        self.resume = filename

    @staticmethod
    def update_professional_rating(professional_id):
        professional = Professional.query.get(professional_id)
        if professional:
            # Calculate the new average rating
            ratings = Rating.query.filter_by(professional_id=professional_id).all()
            if ratings:
                rating = sum(rating.professional_rating for rating in ratings) / len(ratings)
                professional.rating = rating  # Ensure you have this field in your model
                db.session.commit()

             
class Customer(db.Model):
    id = db.Column(db.Integer,primary_key=True)
    username = db.Column(db.String(32),unique=True,nullable=False)
    email=db.Column(db.String(32),nullable=False)
    password=db.Column(db.String(50),nullable=False)
    gender=db.Column(db.String(10),nullable=False)
    name=db.Column(db.String(32),unique=False,nullable=False)
    phone=db.Column(db.Integer,nullable=False)
    address=db.Column(db.String(200),nullable=False)
    pincode=db.Column(db.Integer,nullable=False)
    is_flag=db.Column(db.Boolean,default=False,nullable=False) 
    ratings = db.relationship('Rating', backref='customer', lazy=True)



class Booking(db.Model):
    __tablename__ = 'booking'
    id = db.Column(db.Integer, primary_key=True)
    is_book = db.Column(db.Boolean, default=False, nullable=False)
    is_accepted = db.Column(db.Boolean, default=False)
    professional_id = db.Column(db.Integer, db.ForeignKey('professional.id'), nullable=False)
    
    customer_id = db.Column(db.Integer, db.ForeignKey('customer.id'), nullable=False)
    customer = db.relationship('Customer', backref='bookings', lazy=True)
    
    package_id = db.Column(db.Integer, db.ForeignKey('package.id'), nullable=False)
    start_date = db.Column(db.DateTime, nullable=True)  # This can be nullable if not required initially

    status = db.Column(db.String(50), default='pending', nullable=False)
    view_status = db.Column(db.String(50), default='requested', nullable=False)
    
    created_at = db.Column(db.DateTime, default=lambda: datetime.now(pytz.utc))  # Use timezone-aware UTC time
    updated_at = db.Column(db.DateTime, default=lambda: datetime.now(pytz.utc), onupdate=lambda: datetime.now(pytz.utc)) 
class Servicerequest(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    package_id = db.Column(db.Integer, db.ForeignKey('package.id'), nullable=False)
    customer_id = db.Column(db.Integer, db.ForeignKey('customer.id'), nullable=False) 
    professional_id = db.Column(db.Integer, db.ForeignKey('professional.id'), nullable=False) 
    start_date = db.Column(db.DateTime, nullable=False)
    service_status = db.Column(db.String(30), default='requested', nullable=False)
    
    @property
    def end_date(self):
        return self.start_date + timedelta(hours=self.package.time_required)
    
    # Use string reference to avoid issues with class definition order
    ratings = db.relationship('Rating', backref='service_request', lazy=True)  # Changed 'Ratings' to 'Rating'

class Rating(db.Model):   
    id = db.Column(db.Integer, primary_key=True)
    service_request_id = db.Column(db.Integer, db.ForeignKey('servicerequest.id'), nullable=False)  # Links to the service request
    package_id = db.Column(db.Integer, db.ForeignKey('package.id'), nullable=False)  # Links to the package being rated
    customer_id = db.Column(db.Integer, db.ForeignKey('customer.id'), nullable=False)  # Links to the customer who made the rating

    package_rating = db.Column(db.Integer, nullable=True, default=None)  # Rating for the service (1-5)

    professional_rating = db.Column(db.Integer, nullable=True, default=None)  # Rating for the professional (1-5)
    review_description = db.Column(db.String(250), nullable=True)  # Optional review/feedback
    professional_id = db.Column(db.Integer, db.ForeignKey('professional.id'), nullable=False)  # Professional being rated
    updated_at = db.Column(db.DateTime, default=db.func.current_timestamp(), onupdate=db.func.current_timestamp())  # Last updated timestamp
    status = db.Column(db.String(20), default='active')  # Status of the rating

    @validates('package_rating', 'professional_rating')
    def validate_rating(self, key, value):
        if value is not None and (value < 1 or value > 5):
            raise ValueError("Rating must be between 1 and 5")
        return value
with app.app_context():
    db.create_all()
    admin=Admin.query.filter_by(username='admin').first()
    if not admin:
        admin=Admin(username="admin",email="admin@gmail.com",password=generate_password_hash("admin"),gender="female")
        db.session.add(admin)
        db.session.commit()
     