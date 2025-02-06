from app import app 
from flask import render_template,redirect,url_for,flash,request,session,current_app,send_file
from models import db,Admin,Professional,Service,Package,Customer,Booking,Rating,Servicerequest
from werkzeug.security import generate_password_hash,check_password_hash
from functools import wraps 
from datetime import datetime
from sqlalchemy import func
from werkzeug.utils import secure_filename
import re,pytz
import os



def login_required(func):
    @wraps(func)
    def wrapper(*args, **kwargs):
        if 'username' not in session:
            flash("You need to login first")
            return redirect(url_for('login'))
        
        username = session['username']
        
        # Check if the user is an Admin
        user = Admin.query.filter_by(username=username).first()
        if user:
            return func(*args, **kwargs)
        
        # Check if the user is a Professional
        user = Professional.query.filter_by(username=username).first()
        if user:
            return func(*args, **kwargs)
        
        # Check if the user is a Customer
        user = Customer.query.filter_by(username=username).first()
        if user:
            return func(*args, **kwargs)

        # If no user found in any table
        session.pop('username')
        flash("You need to login first")
        return redirect(url_for('login'))

    return wrapper

def blocked_user_check(func):
    @wraps(func)
    def wrapper(*args, **kwargs):
        username = session.get('username')

        if not username:
            flash("You need to login first")
            return redirect(url_for('login'))

        # Check in Professional table
        user = Professional.query.filter_by(username=username).first()
        if user and user.is_flag:
            flash("You are blocked by admin")
            return redirect(url_for('admin_dashboard'))  # Redirect to admin dashboard or appropriate page

        # Check in Customer table
        user = Customer.query.filter_by(username=username).first()
        if user and user.is_flag:
            flash("You are blocked by admin")
            return redirect(url_for('admin_dashboard'))  # Redirect to admin dashboard or appropriate page

        return func(*args, **kwargs)
    
    return wrapper

# login route 
@app.route('/')
def login():
    # Check if the session is empty
  
    return render_template('login.html')

@app.route('/clear',methods=['POST'])
def clear():
    username = ''
    password = ''
    session.clear()
    return redirect (url_for('login',username=username,password=password))
      
     

@app.route('/', methods=['POST'])
def login_post():
    username = request.form.get('username')
    password = request.form.get('password')
      
    # Check in Admin table
    admin = Admin.query.filter_by(username=username).first()
    if admin and check_password_hash(admin.password, password):
        session['username'] = username
        session['id'] = admin.id 
        return redirect(url_for('ahome'))

    # Check in Customer table
    customer = Customer.query.filter_by(username=username).first()
    if customer and check_password_hash(customer.password, password):
        if customer.is_flag:
            flash("You are blocked by admin")
            return render_template('login.html', username=username, password=password)  # Clear the form data
        session['username'] = username
        session['id'] = customer.id 
        bookings = Booking.query.filter_by(customer_id=customer.id).all()  # Fetch all bookings for this customer
        # session['bookings'] = bookings  
        return redirect(url_for('chome'))

    # Check in Professional table
    professional = Professional.query.filter_by(username=username).first()
    if professional and check_password_hash(professional.password, password):
        if professional.is_flag:
            flash("You are blocked by admin")
            return render_template('login.html')  # Clear the form data
        if professional.status == 'rejected':
            flash("Your resume is rejected by admin.")
            return render_template('login.html')  # Clear the form data
        elif professional.status != 'approved':
            flash("Your account is not approved yet. Please wait for admin approval.")
            return render_template('login.html' )  # Clear the form data
        session['username'] = username
        session['id'] = professional.id 
        return redirect(url_for('phome'))

    # If no user is found or credentials are incorrect
    flash("Username or password is incorrect")
    return render_template('login.html', username=username, password=password)  # Clear the form data 



@app.route('/approve_professional/<int:id>', methods=['POST'])
@login_required
def approve_professional(id):
    professional = Professional.query.get(id)
    if professional:
        professional.status = 'approved'  # Change the status to 'approved'
        db.session.commit()
        flash('Professional approved successfully',category="success")
        return redirect(url_for('ahome'))
    flash('Error approving professional')
    return redirect(url_for('ahome'))

@app.route('/reject_professional/<int:id>', methods=['POST'])
@login_required
def reject_professional(id):
    professional = Professional.query.get(id)
    if professional:
        professional.status = 'rejected'
        db.session.commit()
        flash('Professional rejected successfully')
        return redirect(url_for('ahome'))
    flash('Error rejecting  professional')
    return redirect(url_for('ahome'))


# create a service
@app.route('/cre_service')
def cre_service():
    return render_template('admin/cre_service.html')

@app.route('/cre_service', methods=['POST'])
@login_required
def cre_service_post():
    id = session['id']
    service_name = request.form.get('service_name')
    service_description = request.form.get('service_description')

    # Basic validation
    if not service_name or not service_description:
        flash('Service name and description are required.', category='error')
        return redirect(url_for('cre_service'))  # Redirect back to the form

    # Create the service instance
    service = Service(name=service_name, description=service_description, admin_id=id)
    
    try:
        db.session.add(service)
        db.session.commit()
        flash('Service created successfully', category='success')
    except Exception as e:
        db.session.rollback()  # Rollback the session on error
        flash('An error occurred while creating the service: ' + str(e), category='error')

    return redirect(url_for('ahome'))

# Edit a Service 
@app.route('/ser_edit/<int:id>', methods=['POST'])
@login_required
def ser_edit(id):
    # Retrieve form data
    servicename = request.form['servicename']
    description = request.form['description']
    
    # Update the service in the database
    service = Service.query.get(id)
    service.name = servicename
    service.description = description
    db.session.commit()
    
    # Redirect back to the admin home page or return a success response
    flash('Service updated successfully',category='success')
    return redirect(url_for('ahome'))
# delete a service
@app.route('/del_conf/<int:id>', methods=['GET', 'POST'])
@login_required
def del_conf(id):
    service = Service.query.get(id)
    if request.method == 'POST':
        if service:  # Check if the service exists
            # Delete associated packages
            packages = Package.query.filter_by(service_id=id).all()
            for package in packages:
                db.session.delete(package)  # Delete each package

            db.session.delete(service)  # Delete the service
            db.session.commit()  # Commit the changes
            flash('Service deleted successfully.', category="success")
            return redirect(url_for('ahome'))  # Redirect to home after deletion
        else:
            flash('Service not found.', category="error")  # Flash error if service not found
            return redirect(url_for('ahome'))  # Redirect to home if service not found
    return render_template('admin/del_conf.html', service=service)  # Render the confirmation template

# Creating a package
@app.route('/cre_pac/<int:id>')
def cre_pac(id):
    service=Service.query.filter_by(id=id).first()
    return render_template('admin/cre_pac.html',service=service,service_type=service.name)



@app.route('/cre_pac/<int:id>',methods=['POST'])
def cre_pac_post(id):
    service=Service.query.filter_by(id=id).first()
    id1=session['id']
    
    name=request.form.get('servicename')
    baseprice=request.form.get('baseprice')
    baseprice = float(baseprice) if baseprice not in (None, '') else 0.0

    if baseprice <= 0.0:
        flash('Please enter a valid price', category='error')
        return redirect(url_for('cre_pac'))  # Redirect back to the form

    
    
    
    service_type=request.form.get('service_type')
    timerequired=request.form.get('timerequired')
    service_id=service.id
    package=Package(name=name,base_price=baseprice,package_type=service_type,time_required=timerequired,service_id=service_id,admin_id=id1)
    try:
        db.session.add(package)
        db.session.commit()
        flash('Package created successfully', category='success')
    except Exception as e:
        db.session.rollback()  # Rollback in case of error
        flash('An error occurred while creating the package: ' + str(e), category='error')

    return redirect(url_for('ahome'))

# View all packages
@app.route('/view_pac/<int:id>')
def view_pac(id):
    service = Service.query.get(id)
    package = Package.query.filter_by(service_id=id).all()
    return render_template('admin/view_pac.html', packages=package, service=service)

# Edit a pacakge
@app.route('/edit_pac/<int:id>', methods=['POST'])
def edit_pac(id):
    package = Package.query.get(id)
    if package:
        package.name = request.form.get('packagename')
        package.base_price = request.form.get('baseprice')
        package.time_required = request.form.get('time')

        db.session.commit()
        flash('Package updated successfully!', category='success')
    else:
        flash('Package not found.', category='error')

    return redirect(url_for('view_pac', id=package.service_id))  # Redirect back to the view packages page
# delete a package
# delete a package
@app.route('/delp_conf/<int:id>', methods=['GET', 'POST'])
@login_required
def delp_conf(id):
    package = Package.query.get(id)
    if request.method == 'POST':
        if package:  # Check if the package exists
            db.session.delete(package)  # Delete the specific package
            db.session.commit()  # Commit the changes
            flash('Package deleted successfully.', category="success")
            return redirect(url_for('view_pac', id=package.service_id))  # Redirect to the service's package view
        else:
            flash('Package not found.', category="error")
            return redirect(url_for('view_pac', id=package.service_id))  # Redirect if package not found
    return render_template('admin/delp_conf.html', package=package)  # Render the confirmation template
# register
@app.route('/register')
def register():
    return render_template('register.html')


# Professional register
@app.route('/p_register')
def p_register():
    return render_template('professional/p_register.html')

def validate_filename(filename):
    filename_list = filename.split('.')
    allowed_ext = ['pdf']
    return len(filename_list) > 1 and filename_list[-1] in allowed_ext

@app.route('/p_register', methods=['POST'])
def p_register_post():
    username = request.form.get('username')
    name = request.form.get('name')
    em = request.form.get('email')
    pw = request.form.get('password')
    gen = request.form.get('gender')
    ph = request.form.get('phone')
    loc = request.form.get('location')
    pin = request.form.get('pincode')
    exp = request.form.get('experience')
    service = request.form.get('service')
    resume = request.files.get('resume')

    if not username or not pw:
        flash("Please fill all the mandatory fields")
        return redirect(url_for('p_register'))

    if not ph or len(ph) != 10:  # Corrected phone number validation
        flash("Please enter a valid phone number")
        return redirect(url_for('p_register'))

    if not re.match(r'^\d{3}[-\s]?\d{3}[-\s]?\d{4}$', ph):
        flash("Invalid phone number format. Please use XXX-XXX-XXXX or XXX.XXX.XXXX")
        return redirect(url_for('p_register'))

    if int(exp) < 0:
        flash("Enter a valid experience")
        return redirect(url_for('p_register'))

    if not pin:
        flash("Please enter a pincode")
        return redirect(url_for('p_register'))

    if not re.match(r'^\d{6}$', pin):
        flash("Invalid pincode format. Please use XXXXXX")
        return redirect(url_for('p_register'))

    if not 100001 <= int(pin) <= 999999:
        flash("Invalid pincode. Please enter a valid Indian pincode")
        return redirect(url_for('p_register'))

    # Check for resume file and validate
    filename = None  # Initialize filename
    if 'resume' in request.files and validate_filename(resume.filename):
        filename = secure_filename(resume.filename)
        resume.save(os.path.join(current_app.root_path, 'static', 'uploads', filename))
    else:
        flash("Invalid file or file extension. Only PDF files are allowed.")
        return redirect(url_for('p_register'))

    user = Professional.query.filter_by(username=username).first()
    if user:
        flash("Username already exists. Please choose a different username.")
        return redirect(url_for('p_register'))

    # Create the Professional object only if all validations pass
    prof = Professional(
        username=username,
        password=generate_password_hash(pw),
        email=em,
        gender=gen,
        phone=ph,
        experience=exp,
        service_type=service,
        resume=filename,
        name=name,
        location=loc,
        pincode=pin
    )
    
    db.session.add(prof)
    db.session.commit()

    flash(f'Thanks for registration {name}, Please login to continue.', category="success")
    return redirect(url_for('login',username='',password=''))
# profile
@app.route('/pprofile')
@login_required
@blocked_user_check
def pprofile():
    id1=session['id']
    prof=Professional.query.filter_by(id=id1).first()
    return render_template('/professional/pprofile.html',professional=prof)

# update profile
@app.route('/edit_profile/<int:id>', methods=['POST'])
@login_required
@blocked_user_check
def edit_profile(id):
    professional = Professional.query.get(id)
    if not professional:
        flash('Professional not found', category='error')
        return redirect(url_for('pprofile'))  # Redirect if professional not found

    if request.method == 'POST':
        # Access the form data safely using get()
        professional.name = request.form.get('name')
        professional.username = request.form.get('username')
        professional.email = request.form.get('email')
        professional.phone = request.form.get('phone')
        professional.location = request.form.get('location')
        professional.pincode = request.form.get('pincode')
        professional.experience = request.form.get('experience')

        # Check for None values before committing
        if None in [professional.name, professional.username, professional.email, professional.phone, 
                    professional.location, professional.pincode, professional.experience, ]:
            flash('All fields are required and cannot be empty.', category='error')
            return redirect(url_for('edit_profile', id=id))  # Redirect back if fields are missing
        if 'resume' in request.files:
            resume_file = request.files['resume']
            if resume_file and validate_filename(resume_file.filename):  # Ensure filename is valid
                filename = secure_filename(resume_file.filename)
                resume_file.save(os.path.join(current_app.root_path, 'static', 'uploads', filename))
                professional.resume = filename  # Assuming you have a field for the resume filename

        # Commit the changes to the database
        db.session.commit()
        flash('Profile updated successfully', category='success')
        return redirect(url_for('pprofile'))  # Redirect to profile page after update

    # Render the edit profile form with existing professional data
    return render_template('professional/edit_profile.html', professional=professional)
# Customer register
        
@app.route('/c_register')
def c_register():
    return render_template('customer/c_register.html')


@app.route('/c_register',methods=['POST']) 
def customer_post():       
        username = request.form.get('username')
        name = request.form.get('name')
        em= request.form.get('email')
        pw = request.form.get('password')
        gen = request.form.get('gender')
        ph = request.form.get('phone')
        ad =request.form.get('address')
        pin = request.form.get('pincode')
        if not username or not pw:
            flash("please fill all the mandatory fields")
            return redirect(url_for('c_register'))
        if not ph or 10 <len(ph) >10 :
            flash("Please enter a phone number")
            return redirect(url_for('c_register'))    
        if not re.match(r'^\d{3}[-\s]?\d{3}[-\s]?\d{4}$', ph):
            flash("Invalid phone number format. Please use XXX-XXX-XXXX or XXX.XXX.XXXX")
            return redirect(url_for('c_register'))
        if not pin:
            flash("Please enter a pincode")
            return redirect(url_for('c_register'))
        if not re.match(r'^\d{6}$', pin):
            flash("Invalid pincode format. Please use XXXXXX")
            return redirect(url_for('c_register'))
        if not 100001 <= int(pin) <= 999999:
            flash("Invalid pincode. Please enter a valid Indian pincode")
            return redirect(url_for('c_register'))    
        user=Customer.query.filter_by(username=username).first()
        if user:
            flash("Username already exists. Please choose a different username.")
            return redirect(url_for('c_register'))
        cust = Customer(username=username,password=generate_password_hash(pw),email=em,gender=gen,name=name,phone=ph,address=ad,pincode=pin)  
        db.session.add(cust)
        db.session.commit()
        flash(f'Thanks for registration {name},Please login to continue.',category="success")
        return redirect (url_for('login'))

@app.route('/cprofile')
@login_required
@blocked_user_check
def cprofile():
    id1=session['id']
    cust=Customer.query.filter_by(id=id1).first()
    return render_template('/customer/cprofile.html',customer=cust)

# customer update profile
@app.route('/edit_customer/<int:id>', methods=['GET', 'POST'])
@login_required
@blocked_user_check
def edit_customer(id):
    customer = Customer.query.get(id)
    if not customer:
        flash('Customer not found', category='error')
        return redirect(url_for('customer_profile'))  # Redirect if customer not found

    if request.method == 'POST':
        # Update customer profile
        customer.name = request.form.get('name')
        customer.username = request.form.get('username')
        customer.email = request.form.get('email')
        customer.phone = request.form.get('phone')
        customer.address = request.form.get('address')
        customer.pincode = request.form.get('pincode')

        # Check for None values before committing
        if None in [customer.name, customer.username, customer.email, customer.phone, customer.address, customer.pincode]:
            flash('All fields are required and cannot be empty.', category='error')
            return redirect(url_for('edit_customer', id=id))  # Redirect back if fields are missing

        # Commit the changes to the database
        db.session.commit()
        flash('Profile updated successfully', category='success')
        return redirect(url_for('cprofile'))  # Redirect to customer profile page after update

    # Render the edit customer form (GET request)
    return render_template('edit_customer.html', customer=customer)  # Assuming you have a template for editing customer
# customer view packages
@app.route('/c_view_pac/<int:id>')
@login_required
@blocked_user_check
def c_view_pac(id):
    service = Service.query.get(id)
    packages = Package.query.filter_by(service_id=id).all()
    # Fetch all unflagged and approved professionals for the particular service directly
    profs = Professional.query.filter(
        Professional.is_flag == False,  # Check for unflagged professionals first
        func.replace(func.lower(Professional.service_type), ' ', '') == func.replace(func.lower(service.name), ' ', ''),  # Remove spaces and convert to lower case
        Professional.status == 'approved'  # Then check for approved status
    ).all()
    return render_template('customer/c_view_pac.html', packages=packages, service=service, profs=profs)
# Booking a package
@app.route('/book_package/<int:package_id>', methods=['POST'])
@login_required
def book_package(package_id):
    id = session['id']
    package = Package.query.get(package_id)
    if package is None:
        flash("Package not found")
        return redirect(url_for('chome'))

    existing_booking = Booking.query.filter_by(package_id=package_id, customer_id=id).first()
    if existing_booking:
        flash("You have already booked this package")
        return redirect(url_for('chome'))

    professional_id = request.form.get('professional_id')
    professional = Professional.query.get(professional_id)
    if professional is None:
        flash("Invalid professional selected.")
        return redirect(url_for('chome'))

    start_date = request.form.get('start_date')
    if not start_date:
        flash("Start date is required for booking.")
        return redirect(url_for('chome'))

    # Convert start_date to a datetime object
    start_date = datetime.strptime(start_date, '%Y-%m-%dT%H:%M')  # Adjust the format as necessary

    # Update package status to 'booked'
    package.status = 'booked'
    db.session.commit()

    # Create a new booking with the start date
    booking = Booking(
        package_id=package_id,
        customer_id=id,
        professional_id=professional_id,
        start_date=start_date,  # Include the start date
        is_book=True
    )
    db.session.add(booking)
    db.session.commit()

    flash('Package booked successfully.', category='success')
    
    return redirect(url_for('chome'))

# edit a package
@app.route('/edit_booking/<int:booking_id>', methods=['GET', 'POST'])
@login_required
@blocked_user_check
def edit_booking(booking_id):
    booking = Booking.query.get(booking_id)

    # Ensure the user is the owner of the booking and the status is pending
    if booking.customer_id != session['id'] or booking.status != 'pending':
        flash("You cannot edit this booking request.", "warning")
        return redirect(url_for('chome'))

    if request.method == 'POST':
        # Update the booking fields based on the form input
        start_date = request.form.get('start_date')  # Get new start date from form
        
        if not start_date:  # Ensure start_date is provided
            flash("Start date is required.", "danger")
            return redirect(url_for('edit_booking', booking_id=booking.id))
        
        booking.start_date = datetime.strptime(start_date, '%Y-%m-%dT%H:%M')  # Update start date
        booking.updated_at = datetime.now(pytz.utc)  # Update the updated_at timestamp
        
        db.session.commit()
        flash("Booking updated successfully.", "success")
        return redirect(url_for('chome'))

    return render_template('customer/edit_booking.html', booking=booking)
# cancel a request 
@app.route('/cancel_booking/<int:booking_id>', methods=['POST'])
@login_required
def cancel_booking(booking_id):
    booking = Booking.query.get(booking_id)
    if booking is None:
        flash("Booking not found.")
        return redirect(url_for('chome'))

    if booking.customer_id != session['id']:
        flash("You are not authorized to cancel this booking.")
        return redirect(url_for('chome'))

    if booking.status != 'pending':
        flash("You can only cancel bookings that are pending.")
        return redirect(url_for('chome'))

    # Update the booking status to 'canceled'
    booking.status = 'canceled'
    db.session.commit()

    flash('Booking canceled successfully.', category='success')
    
    return redirect(url_for('chome'))

# dashboards
# Admin
@app.route('/ahome')
@login_required
def ahome():
    id=session['id']
    ad=Admin.query.filter_by(id=id).first()
    customers=Customer.query.all()
    
    services=Service.query.all()
    profs= Professional.query.all()
    service_requests = db.session.query(Booking).join(
        Package, Booking.package_id == Package.id
    ).join(
        Professional, Booking.professional_id == Professional.id
    ).add_columns(
        Booking.id,  # Add Booking ID
        Package.name.label('package_name'),  # Package name
        Professional.name.label('professional_name'),  # Professional name
        Booking.start_date,  # Start date
        Booking.status  # Booking status
    ).all()


    return render_template('admin/ahome.html',professionals=profs,services=services,service_requests=service_requests,customers=customers)

# Customer
# Customer dashboard chome()
@app.route('/chome')
@login_required
@blocked_user_check
def chome():
    customer_id = session['id']
    cust = Customer.query.filter_by(id=customer_id).first()
    
    services = Service.query.all()

    # Fetch all bookings for the customer
    bookings = Booking.query.filter_by(customer_id=customer_id).all()
    service_request=Servicerequest.query.filter_by(customer_id=customer_id).first()
    # Prepare lists for different request statuses
    completed_requests = []
    rejected_requests = []
    pending_requests = []
    accepted_requests = []
    closed_requests = []  # New list for closed requests
    cancelled_requests=[]
    
    for booking in bookings:
        if booking.status == 'completed' and booking.view_status == 'accepted':
            completed_requests.append(booking)
        elif booking.status == 'rejected':
            rejected_requests.append(booking)
        elif booking.status == 'pending':
            pending_requests.append(booking)
        elif booking.status == 'completed' and booking.view_status == 'closed':
            closed_requests.append(booking)
        elif booking.is_accepted and booking.status == 'accepted':
            accepted_requests.append(booking)
        elif booking.status=='cancelled':
            cancelled_requests.append(booking)
    cancelled_request_details = []
    for request in cancelled_requests:
        professional = Professional.query.filter_by(id=request.professional_id).first()
        package = Package.query.get(request.package_id)

        cancelled_request_detail = {
            'request_id': request.id,
            'professional_name': professional.name if professional else 'Unknown',
            'professional_phone': professional.phone if professional else 'N/A',  # Added phone number
            'professional_location': professional.location if professional else 'N/A',  # Added location
            'package_name': package.name if package else 'N/A',
            'status': request.status,
            'professional_id': professional.id if professional else None,
            'package_id': package.id if package else None,
            'request_date': request.start_date
        }
        cancelled_request_details.append(cancelled_request_detail)
    # Prepare data for rendering accepted requests
    accepted_request_details = []
    for request in accepted_requests:
        professional = Professional.query.filter_by(id=request.professional_id).first()
        package = Package.query.get(request.package_id)

        accepted_request_detail = {
            'request_id': request.id,
            'professional_name': professional.name if professional else 'Unknown',
            'professional_phone': professional.phone if professional else 'N/A',  # Added phone number
            'professional_location': professional.location if professional else 'N/A',  # Added location
            'package_name': package.name if package else 'N/A',
            'status': request.status,
            'view_status': request.view_status,  # Include view_status
            'package_id': package.id if package else None,
        }
        accepted_request_details.append(accepted_request_detail)

    # Prepare data for rendering pending requests
    pending_request_details = []
    for request in pending_requests:
        professional = Professional.query.filter_by(id=request.professional_id).first()
        package = Package.query.get(request.package_id)

        request_detail = {
            'request_id': request.id,
            'professional_name': professional.name if professional else 'Unknown',
            'professional_phone': professional.phone if professional else 'N/A',  # Added phone number
            'professional_location': professional.location if professional else 'N/A',  # Added location
            'package_name': package.name if package else 'N/A',
            'status': request.status,
            'professional_id': professional.id if professional else None,
            'package_id': package.id if package else None,
        }
        pending_request_details.append(request_detail)

    # Prepare data for rendering completed requests
    completed_request_details = []
    for request in completed_requests:
        professional = Professional.query.filter_by(id=request.professional_id).first()
        package = Package.query.get(request.package_id)

        completed_request_detail = {
            'request_id': request.id,
            'professional_name': professional.name if professional else 'Unknown',
            'professional_phone': professional.phone if professional else 'N/A',  # Added phone number
            'professional_location': professional.location if professional else 'N/A',  # Added location
            'package_name': package.name if package else 'N/A',
            'status': request.status,
            'view_status': request.view_status,  # Include view_status

        }
        completed_request_details.append(completed_request_detail)

    # Prepare data for rendering rejected requests
    rejected_request_details = []
    for request in rejected_requests:
        if request.status == 'rejected':

            professional = Professional.query.filter_by(id=request.professional_id).first()
            package = Package.query.get(request.package_id)

            rejected_request_detail = {
                'request_id': request.id,
                'professional_name': professional.name if professional else 'Unknown',
                'professional_phone': professional.phone if professional else 'N/A',  # Added phone number
                'professional_location': professional.location if professional else 'N/A',  # Added location
                'package_name': package.name if package else 'N/A',
                'status': request.status,
                'package_id': package.id if package else 'N/A'
            }
            rejected_request_details.append(rejected_request_detail)
    closed_request_details = []
    for request in closed_requests:
        if booking.status == 'completed' and booking.view_status == 'closed':
            professional = Professional.query.filter_by(id=booking.professional_id).first()
            package = Package.query.get(booking.package_id)
            closed_request_detail = {
                'request_id': booking.id,
                'professional_name': professional.name if professional else 'Unknown',
                'professional_phone': professional.phone if professional else 'N/A',
                'professional_location': professional.location if professional else 'N/A',  # Added location
                'package_name': package.name if package else 'N/A',
                'status': request.status,
                'view_status': request.view_status, 
            } # Include view_status
            closed_request_details.append(closed_request_detail)
    cust = Customer.query.filter_by(id=customer_id).first()

    return render_template('customer/chome.html', 
                           services=services,
                           cancelled_requests=cancelled_request_details,
                           accepted_requests=accepted_request_details,  
                           pending_requests=pending_request_details, 
                           completed_requests=completed_request_details,
                           rejected_requests=rejected_request_details,
                           customer=cust.name,
                           service_request=service_request,
                           closed_requests=closed_request_details,
                           customer_id=customer_id)
# request prof
@app.route('/request_prof/<int:package_id>', methods=['GET', 'POST'])
def request_prof(package_id):
    existing_booking = Booking.query.filter_by(package_id=package_id)

    if request.method == 'POST':
        # Handle the form submission

        professional_id = request.form.get('professional_id')

        # Create a new booking/request
        existing_booking.professional_id = professional_id
        existing_booking.status = 'pending' 
        existing_booking.view_status = '' 

         # Set the status to pending
        db.session.commit()


        flash('Your request for a new professional has been submitted successfully.', 'success')
        return redirect(url_for('chome'))  # Redirect to the home page or wherever appropriate

    # Handle the GET request
    package = Package.query.get(package_id)

    if package:
        # Fetch the service based on the package
        service = Service.query.get(package.service_id)

        # Fetch approved professionals for the particular service
        professionals = Professional.query.filter(
            Professional.service_type == service.name,
            Professional.status == 'approved'
        ).all()

        # Assuming you also want to pass a service_request object
        service_request = Servicerequest.query.filter_by(package_id=package_id).first()

        return render_template('customer/request_prof.html', 
                               package=package, 
                               professionals=professionals, 
                               existing_booking=existing_booking, 
                               service_request=service_request)  # Pass service_request to the template

    flash('Package not found', 'error')
    return redirect(url_for('chome'))  # Redirect to a suitable page
# professional dashboard
@app.route('/phome')
@login_required
@blocked_user_check
def phome():
    id=session['id']
    professional = Professional.query.filter_by(id=id).first()
    # professional_name = professional.name  # Accessing the name from the Professional model
    if professional:
    # Accessing columns from the Professional model
        professional_name = professional.name
    print(professional)
    # Fetch new requests (bookings that are accepted and pending)
    new_requests = Booking.query.filter(
        Booking.professional_id == id,
        Booking.is_accepted == False,
        Booking.status == 'pending'
    ).all()
    # Prepare data for rendering new requests
    new_request_details = []
    for request in new_requests:
        # Get the customer using the customer_id from the booking
        customer = Customer.query.filter_by(id=request.customer_id).first()  # Querying Customer by user_id

        # Get package information
        package = Package.query.get(request.package_id)

        # Prepare new request detail with customer information
        request_detail = {
            'customer_name': customer.name if customer else 'Unknown',  # Use 'Unknown' if customer is None
            'customer_phone': customer.phone if customer else 'N/A',  # Use 'N/A' if customer is None
            'customer_address': customer.address if customer else 'N/A',  # Add customer address
            'package_name': package.name if package else 'N/A',  # Handle case where package might be None
            'request_id': request.id,  # Include request ID for actions
            'status': request.status,  # Include status for display
        }
        new_request_details.append(request_detail)

    # Fetch accepted requests
    accepted_requests = Booking.query.filter(
        Booking.professional_id == professional.id,
        Booking.is_accepted == True,
        Booking.status=='accepted'
    ).all()

    # Prepare data for rendering accepted requests
    accepted_request_details = []
    for request in accepted_requests:
        customer = Customer.query.filter_by(id=request.customer_id).first()  # Querying Customer by user_id
        package = Package.query.get(request.package_id)

        accepted_request_detail = {
            'customer_name': customer.name if customer else 'Unknown',
            'customer_phone': customer.phone if customer else 'N/A',
            'customer_address': customer.address if customer else 'N/A',
            'package_name': package.name if package else 'N/A',
            'request_id': request.id,  # Include request ID for actions
            'status': request.status,
        }
        accepted_request_details.append(accepted_request_detail)

    # Fetch rejected requests
    rejected_requests = Booking.query.filter(
        Booking.professional_id == professional.id,
        Booking.is_accepted == False,
        Booking.status == 'rejected'
    ).all()
    rejected_request_details = []
    for request in rejected_requests:
        customer = Customer.query.filter_by(id=request.customer_id).first()
        package = Package.query.get(request.package_id)

        rejected_request_detail = {
            'customer_name': customer.name if customer else 'Unknown',
            'customer_phone': customer.phone if customer else 'N/A',
            'customer_address': customer.address if customer else 'N/A',
            'package_name': package.name if package else 'N/A',
            'request_id': request.id,
            'status': request.status,
        }
        rejected_request_details.append(rejected_request_detail)

     # Fetch closed requests (completed bookings)
    closed_requests = Booking.query.filter(
        Booking.status == 'completed',
        Booking.view_status=='closed',
            Booking.professional_id == professional.id  # Filter by the professional ID

    ).all()

    # Prepare data for rendering closed requests
    closed_request_details = []
    for request in closed_requests:
        customer = Customer.query.filter_by(id=request.customer_id).first()
        package = Package.query.get(request.package_id)

        closed_request_detail = {
            'customer_name': customer.name if customer else 'Unknown',
            'customer_phone': customer.phone if customer else 'N/A',
            'customer_address': customer.address if customer else 'N/A',
            'package_name': package.name if package else 'N/A',
            'request_id': request.id,
            'status': request.status,
        }
        closed_request_details.append(closed_request_detail)


    return render_template('/professional/phome.html', 
                           new_requests=new_request_details,  # Pass new request details
                           accepted_requests=accepted_request_details,  # Pass accepted request details
                           rejected_requests=rejected_request_details,
                           closed_requests=closed_request_details,  # Pass closed request details
                           Professional=professional_name)

# Accept  a request
@app.route('/accept_booking/<int:request_id>', methods=['POST'])
@login_required
@blocked_user_check
def accept_booking(request_id):
    # Your code to accept the booking goes here
    booking = Booking.query.get(request_id)
    if booking:
        # Update the booking status to 'accepted'
        booking.is_accepted = True
        booking.status = 'accepted'
        booking.view_status = 'accepted'
        professional_id = session.get('id')

        booking.professional_id=professional_id
       
         # Create a new ServiceRequest based on the accepted booking
        service_request = Servicerequest(
            package_id=booking.package_id,
            customer_id=booking.customer_id,
            professional_id=professional_id,
            start_date=datetime.now(),  # Set the start date to now or as needed
            service_status='accepted'  # Initial status for the service request
        )
        
        # Add the new service request to the session
        db.session.add(service_request)
        
        # Commit all changes to the database
        db.session.commit()
        
        flash('Request Accepted and Service Request created successfully', category='success')
    else:
        flash('Booking not found', category='error')
    
    return redirect(url_for('phome'))

# reject a request
@app.route('/reject_booking/<int:request_id>', methods=['POST'])
@login_required
@blocked_user_check
def reject_booking(request_id):
    # Your code to accept the booking goes here
    booking = Booking.query.get(request_id)
    if booking:
        # Update the booking status to 'accepted'
        booking.is_accepted = False
        booking.status = 'rejected'
        booking.view_status = 'rejected'
        professional_id = session.get('id')

        booking.professional_id=professional_id
       
         # Create a new ServiceRequest based on the accepted booking
        service_request = Servicerequest(
            package_id=booking.package_id,
            customer_id=booking.customer_id,
            professional_id=professional_id,
            start_date=datetime.now(),  # Set the start date to now or as needed
            service_status='rejected'  # Initial status for the service request
        )
        
        # Add the new service request to the session
        db.session.add(service_request)
        
        # Commit all changes to the database
        db.session.commit()
        
        flash('Request rejected and Service Request updated successfully', category='success')
    else:
        flash('Booking not found', category='error')
    
    return redirect(url_for('phome'))

# Complete a request
@app.route('/complete_request/<int:request_id>', methods=['POST'])
@login_required
@blocked_user_check
def complete_request(request_id):
    # Retrieve customer_id from the session
    print(f"Request ID received: {request_id}")

    customer_id = session.get('id')

    # Check if the confirmation field is present and set to 'yes'
    if request.form.get('confirm') == 'yes':
        # Retrieve the booking using the provided request_id
        booking = Booking.query.filter_by(package_id=request_id).first()
        
        # Check if the booking exists
        if booking:
            print(booking.status)
            professional_id = booking.professional_id
            package_id = booking.package_id

            print(professional_id, package_id, customer_id)
            
            # Fetch the corresponding service request based on customer_id, package_id, and professional_id
            service_request = Servicerequest.query.filter_by(customer_id=customer_id, package_id=package_id, professional_id=professional_id).first()
            
            # Check if both booking and service request exist
            if service_request:
                print(service_request.service_status)

                # Check if the request is already completed
                if booking.status == 'accepted' and service_request.service_status == 'accepted':
                    # Update the booking and service request statuses
                    booking.status = 'completed'
                    service_request.service_status = 'completed'  # Mark service request as completed

                    # Commit the changes to the database
                    try:
                        db.session.commit()
                        flash('Booking and service request status updated to completed.', 'success')
                    except Exception as e:
                        db.session.rollback()  # Rollback in case of error
                        flash(f'An error occurred while updating: {str(e)}', 'error')
                else:
                    flash('Booking or service request is not in accepted status.', 'warning')
            else:
                flash('No service request found matching the criteria.', 'error')
    # Redirect back to the customer home page
    return redirect(url_for('chome'))
# close a request
@app.route('/close_request/<int:service_request_id>', methods=['POST'])
@login_required
@blocked_user_check
def close_request(service_request_id):
    print(f"Request ID received: {service_request_id}")

    booking = Booking.query.filter_by(id=service_request_id).first()
    if booking:
        service_request=Servicerequest.query.filter_by(package_id=booking.package_id).first()
        # Check if the service request exists
        print(service_request)
        # if service_request is None:
        #     flash('Service request not found.', 'error')
        #     return redirect(url_for('chome'))

    # Check if the service request is completed
        if service_request.service_status != 'completed':
            flash('You can only close a service that has been completed.', 'error')
            return redirect(url_for('chome'))

    try:
        # If the service request is completed, redirect to the add_rating route
        return redirect(url_for('add_rating', 
                                service_request_id=service_request.id, 
                                package_id=service_request.package_id, 
                                professional_id=service_request.professional_id))

    except Exception as e:
        flash(f'Error processing request: {str(e)}', 'error')
        return redirect(url_for('chome'))
# @app.route('/submit_rating', methods=['POST'])
# def submit_rating():
#     id=session['id']
#     cust=service_request.query.filter_by(customer_id=id).first()  # Assuming you have the user ID from the session or form
#     service_request_id = request.form.get('service_request_id')
#     rating = request.form.get('rating')
#     review_description = request.form.get('review_description')

#     # Find the service request
#     service_request = Servicerequest.query.get(service_request_id)

#     if service_request and service_request.service_status == 'completed':  # Check if the service request is completed
#         # Create a new rating
#         new_rating = Rating(
#             user_id=user_id,
#             rating=rating,
#             review_description=review_description,
#             service_request_id=service_request.id,
#             professional_id=service_request.professional_id  # Link to the professional
#         )
        
#         db.session.add(new_rating)
#         db.session.commit()
#         flash("Thank you for your rating!")
#     else:
#         flash("Service request is not completed or does not exist.")

#     return redirect(url_for('some_view'))  # Redirect to an appropriate view
@app.route('/add_rating/<int:service_request_id>/<int:package_id>/<int:professional_id>', methods=['GET', 'POST'])
@login_required
@blocked_user_check
def add_rating(service_request_id, package_id, professional_id):
    print(f"Request ID received: {service_request_id, package_id, professional_id}")
    customer_id = session['id']
    customer = Customer.query.filter_by(id=customer_id).first()  # Fetch the customer
    service_request = Servicerequest.query.filter_by(id=service_request_id).first()
    
    if service_request is None:
        return "Service request not found", 404
    
    if service_request.service_status != 'completed':
        flash('You can only rate a service that has been completed.', 'error')
        return redirect(url_for('chome'))  # Redirect if service not completed

    if request.method == 'POST':
        try:
            # Parse form data
            service_rating = int(request.form['package_rating'])
            professional_rating = int(request.form['professional_rating'])
            review_description = request.form.get('review_description', '')

            # Create a new rating entry
            new_rating = Rating(
                customer_id=customer_id,
                service_request_id=service_request_id,
                package_rating=service_rating,
                professional_rating=professional_rating,
                review_description=review_description,
                professional_id=professional_id,
                package_id=package_id
            )
            
            # Add the new rating to the session

            # Update the professional's average rating
            Professional.update_professional_rating(professional_id)

            # Update the package rating
            Package.update_package_rating(package_id)

            # Change the service request status to 'closed'
            service_request.service_status = 'closed'

            # Fetch the booking for the customer
            booking = Booking.query.filter_by(customer_id=customer_id).first()  # Use .first() to get a single result
            if booking:
                booking.view_status = 'closed'

            # Commit all changes in one go
            db.session.commit()

            # Use flash for feedback
            flash('Rating submitted successfully!', 'success')
            return redirect(url_for('chome'))  # Redirect to the customer home page

        except Exception as e:
            db.session.rollback()  # Rollback in case of error
            flash(f'Error submitting rating: {str(e)}', 'error')
            return redirect(url_for('add_rating', service_request_id=service_request_id, package_id=package_id, professional_id=professional_id))  # Redirect back to the form

    # If GET request, retrieve the service request details
    # Fetch the associated package and professional details
    package = Package.query.get(package_id)
    professional = Professional.query.get(professional_id)

    # Pass the service request, package, and professional details to the template
    return render_template('customer/add_rating.html', 
                           service_request=service_request,
                           package=package,
                           professional=professional)

@app.route('/asearch', methods=['GET', 'POST'])
@login_required
def asearch():
    results = {
        'services': [],
        'customers': [],
        'professionals': [],
        'service_requests': []
    }

    # Initialize search terms
    search_type = ''
    search_term = ''

    if request.method == 'POST':
        search_type = request.form.get('search_type', '').strip()
        search_term = request.form.get('search_term', '').strip()

        # Search based on the selected type
        if search_type == 'service' and search_term:
            normalized_search_term = search_term.lower().replace(" ", "")

            # Find the services that match the normalized search term
            services = Service.query.all()  # Get all services to filter in Python
            
            for service in services:
                # Normalize the service name: lowercase and remove spaces
                normalized_service_name = service.name.lower().replace(" ", "")
                
                # Check if the normalized service name contains the normalized search term
                if normalized_search_term in normalized_service_name:
                    packages = Package.query.filter(Package.service_id == service.id).all()
                    results['services'].append({
                        'service': service,
                        'packages': packages
                    })
        elif search_type == 'customer' and search_term:
            results['customers'] = Customer.query.filter(Customer.name.ilike(f'%{search_term}%')).all()

        elif search_type == 'professional' and search_term:
            results['professionals'] = Professional.query.filter(Professional.name.ilike(f'%{search_term}%')).all()

        elif search_type == 'service_request' and search_term:
            results['service_requests'] = db.session.query(Booking).filter(
                Booking.view_status == search_term
            ).join(Package, Booking.package_id == Package.id).join(
                Professional, Booking.professional_id == Professional.id
            ).add_columns(
                Package.name.label('package_name'),
                Professional.name.label('professional_name'),
                Booking.start_date,
                Booking.view_status  # Include view_status in the query

            ).all()

    return render_template('admin/asearch.html', results=results,
                           search_type=search_type,
                           search_term=search_term)
@app.route('/block/<int:id>/<string:type>', methods=['POST'])
@login_required
def block(id, type):
    if type == 'professional':
        professional = Professional.query.get(id)
        if professional:
            professional.is_flag = True  # Assuming you have a field `is_flag` in your Professional model
            db.session.commit()
            flash('Professional has been blocked successfully.', 'success')
        else:
            flash('Professional not found.', 'danger')
    
    elif type == 'customer':
        customer = Customer.query.get(id)
        if customer:
            customer.is_flag = True  # Assuming you have a field `is_flag` in your Customer model
            db.session.commit()
            flash('Customer has been blocked successfully.', 'success')
        else:
            flash('Customer not found.', 'danger')
    
    return redirect(url_for('ahome'))

@app.route('/unblock/<int:id>/<string:type>', methods=['POST'])
@login_required
def unblock(id, type):
    if type == 'professional':
        professional = Professional.query.get(id)
        if professional:
            professional.is_flag = False  # Assuming you have a field `is_flag` in your Professional model
            db.session.commit()
            flash('Professional has been unblocked successfully.', 'success')
        else:
            flash('Professional not found.', 'danger')
    
    elif type == 'customer':
        customer = Customer.query.get(id)
        if customer:
            customer.is_flag = False  # Assuming you have a field `is_flag` in your Customer model
            db.session.commit()
            flash('Customer has been unblocked successfully.', 'success')
        else:
            flash('Customer not found.', 'danger')
    
    return redirect(url_for('asearch'))

@app.route('/asummary')
@login_required
@blocked_user_check
def asummary():
    services = db.session.query(
        Service,
        func.count(Package.id).label('sub_package_count')
    ).outerjoin(Package, Service.id == Package.service_id).group_by(Service.id).all()
    # Fetch all bookings and their statuses
    bookings = Booking.query.all()
    accepted_count = sum(1 for booking in bookings if booking.status == 'accepted')
    rejected_count = sum(1 for booking in bookings if booking.status == 'rejected')
    canceled_count = sum(1 for booking in bookings if booking.status == 'canceled')
    closed_count = sum(1 for booking in bookings if booking.status == 'completed')

    # Fetch approved professionals count
    approved_professionals_count = Professional.query.filter_by(status='approved').count()

    # Fetch flagged users count
    flagged_professionals_count = Professional.query.filter_by(is_flag=True).count()
    flagged_customers_count = Customer.query.filter_by(is_flag=True).count()

    # Fetch total service requests
    service_requests_count = Servicerequest.query.count()

    return render_template('admin/asummary.html',
                           services=services,
                           booking_data={
                               'accepted': accepted_count,
                               'rejected': rejected_count,
                               'canceled': canceled_count,
                               'closed': closed_count
                           },
                           approved_professionals_count=approved_professionals_count,
                           flagged_professionals_count=flagged_professionals_count,
                           flagged_customers_count=flagged_customers_count,
                           service_requests_count=service_requests_count)







@app.route('/csearch', methods=['GET', 'POST'])
@login_required
@blocked_user_check
def csearch():
    services_with_packages = []
    search_term=''
    if request.method == 'POST':
        search_term = request.form.get('search_term', '').strip()
        
        # Normalize the search term: lowercase and remove spaces
        normalized_search_term = search_term.lower().replace(" ", "")
        
        if search_term:
            # Find the services that match the normalized search term
            services = Service.query.all()  # Get all services to filter in Python
            
            for service in services:
                # Normalize the service name: lowercase and remove spaces
                normalized_service_name = service.name.lower().replace(" ", "")
                
                # Check if the normalized service name contains the normalized search term
                if normalized_search_term in normalized_service_name:
                    packages = Package.query.filter(Package.service_id == service.id).all()
                    services_with_packages.append({
                        'service': service,
                        'packages': packages
                    })

    return render_template('customer/csearch.html', services_with_packages=services_with_packages, search_term=search_term)
# customer summary
@app.route('/csummary')
@login_required
@blocked_user_check
def csummary():
    id = session['id']
    cust = Customer.query.filter_by(id=id).first()

    # Fetch bookings and their statuses
    bookings = Booking.query.filter_by(customer_id=id).all()
    completed_count = sum(1 for booking in bookings if booking.status == 'completed')
    pending_count = sum(1 for booking in bookings if booking.status == 'pending')
    cancelled_count = sum(1 for booking in bookings if booking.status == 'cancelled')
    rejected_count = sum(1 for booking in bookings if booking.status == 'rejected')

    # Fetch ratings
    
    ratings = Rating.query.filter_by(customer_id=id).all()
    total_ratings = len(ratings)
    average_rating = sum(rating.package_rating for rating in ratings) / total_ratings if total_ratings > 0 else 0

    return render_template('customer/csummary.html',
                           customer=cust,
                           completed_count=completed_count,
                           pending_count=pending_count,
                           cancelled_count=cancelled_count,
                           rejected_count=rejected_count,
                           average_rating=average_rating,
                           total_ratings=total_ratings)



@app.route('/psearch', methods=['GET', 'POST'])
@login_required
@blocked_user_check
def psearch():
    professional_id = session['id']  # Get the professional ID from the session
    booking_details = []  # Initialize an empty list for booking details
    search_date = None  # Initialize search_date as None

    if request.method == 'POST':
        search_date = request.form.get('search_date')  # Get the date from the form

        # Check if search_date is None or empty
        if not search_date:
            flash("Please select a date to search.", "error")
            return redirect(url_for('psearch'))  # Redirect back to the search page

        # Convert the date string to a datetime object (assuming the date is in YYYY-MM-DD format)
        search_date = datetime.strptime(search_date, '%Y-%m-%d').date()

        # Fetch bookings for the professional on the specified date
        bookings = Booking.query.filter(
            Booking.professional_id == professional_id,
            func.date(Booking.start_date) == search_date  # Use func.date() to compare only the date part
        ).all()

        # Prepare booking details for rendering
        for booking in bookings:
            customer = Customer.query.filter_by(id=booking.customer_id).first()
            package = Package.query.get(booking.package_id)
            
            booking_detail = {
                'customer_name': customer.name if customer else 'Unknown',
                'customer_phone': customer.phone if customer else 'N/A',
                'package_name': package.name if package else 'N/A',
                'request_id': booking.id,
                'status': booking.status,
                'start_date': booking.start_date
            }
            booking_details.append(booking_detail)

    # Render the search page with the booking details (if any)
    return render_template('professional/psearch.html', 
                           bookings=booking_details, 
                           search_date=search_date)

@app.route('/psummary')
@login_required
@blocked_user_check
def psummary():
    professional_id = session['id']  # Get the professional ID from the session
    professional=Professional.query.filter_by(id=professional_id).first()
    # Fetch bookings for the professional
    bookings = Booking.query.filter_by(professional_id=professional_id).all()

    # Initialize counters for booking statuses
    accepted_count = sum(1 for booking in bookings if booking.status == 'accepted')
    rejected_count = sum(1 for booking in bookings if booking.status == 'rejected')
    canceled_count = sum(1 for booking in bookings if booking.status == 'canceled')
    closed_count = sum(1 for booking in bookings if booking.status == 'completed' and booking.view_status == 'closed')

    # Fetch ratings for the professional
    
    # Prepare data for rendering
    booking_data = {
        'accepted': accepted_count,
        'rejected': rejected_count,
        'canceled': canceled_count,
        'closed': closed_count
    }

    return render_template('professional/psummary.html', 
                           booking_data=booking_data, 
                         
                           professional=professional)


@app.route('/logout')
def logout():
    session.pop('username', None)  # Clear the username from the session
    session.pop('id',None)
    return redirect(url_for('login',username='',password=''))
        
if  __name__ == '__main__':
    app.debug=True
    app.run()
