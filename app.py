from flask import Flask, render_template, request,Response, redirect, url_for, flash, session
from flask_mysql_connector import MySQL


from datetime import datetime  
date = datetime.now()  


from werkzeug.utils import secure_filename
import os
from fpdf import FPDF
import re


app = Flask(__name__)
app.secret_key = 'your_secret_key'

# MySQL Configuration
app.config['MYSQL_HOST'] = 'localhost'
app.config['MYSQL_USER'] = 'root'
app.config['MYSQL_PASSWORD'] = 'mysql'
app.config['MYSQL_DB'] = 'website'
app.config['UPLOAD_FOLDER'] = 'static/img/'  # Image Upload Folder


mysql = MySQL(app)


@app.route("/dashboard")
def dashboard():
    return render_template("admindashboard.html") 

                        
@app.route('/admin')
def admin_dashboard():
    if 'loggedin' not in session or 'Email' not in session:
        flash('Please log in first', 'danger')
        return redirect(url_for('adminlogin'))

    cursor = mysql.connection.cursor()

    # ✅ Fetch admin's name from `website.admin`, not `website.user`
    if 'admin_name' not in session:
        cursor.execute("SELECT Name FROM website.admin WHERE Email = %s", (session['Email'],))
        admin = cursor.fetchone()
        if admin:
            session['admin_name'] = admin[0]

    # ✅ Fetch dashboard statistics
    cursor.execute("SELECT COUNT(*) FROM website.orders WHERE DATE(order_date) = CURDATE()")
    new_orders_count = cursor.fetchone()[0] or 0  

    cursor.execute("SELECT COUNT(*) FROM website.orders WHERE status = 'Pending'")
    pending_orders_count = cursor.fetchone()[0] or 0

    cursor.execute("SELECT COUNT(*) FROM website.product WHERE Stock_quantity <= 5")
    low_stock_count = cursor.fetchone()[0] or 0

    cursor.execute("SELECT COUNT(*) FROM website.user")
    total_users = cursor.fetchone()[0] or 0

    cursor.execute("SELECT COUNT(*) FROM website.product")
    total_products = cursor.fetchone()[0] or 0

    cursor.execute("SELECT COALESCE(SUM(total_amount), 0) FROM website.orders WHERE status != 'Cancelled'")
    total_sales = cursor.fetchone()[0] or 0

    # ✅ Fetch recent 5 orders
    cursor.execute("""
        SELECT o.order_id, CONCAT(u.First_Name, ' ', u.Last_Name) AS customer_name, 
               o.total_amount, o.status, o.order_date 
        FROM website.orders o
        JOIN website.user u ON o.user_id = u.user_id
        ORDER BY o.order_date DESC
        LIMIT 5
    """)
    recent_orders = cursor.fetchall()

    cursor.close()
    print("Pending Orders Count:", pending_orders_count)


    return render_template('admindashboard.html', 
                           total_users=total_users,
                           total_products=total_products,
                           total_sales=total_sales,
                           recent_orders=recent_orders,
                           new_orders_count=new_orders_count,
                           pending_orders_count=pending_orders_count,
                           low_stock_count=low_stock_count)  

@app.route('/admin/orders')
def admin_orders():
    cursor = mysql.connection.cursor()  # Use dictionary cursor
    cursor.execute("""
        SELECT o.order_id,  u.First_Name,u.Last_Name, o.total_amount, o.status, o.order_date
        FROM website.orders o
        JOIN website.user u ON o.user_id = u.user_id
    """)
    orders = cursor.fetchall()
    cursor.close()
    print(orders)
    return render_template('admin_order.html', orders=orders)
@app.route('/admin/update_order_status/<int:order_id>', methods=['POST'])
def update_order_status(order_id):
    new_status = request.form.get('status')

    # Check if status is empty or None
    if not new_status:
        flash('Invalid order status! Please select a valid status.', 'danger')
        return redirect(url_for('admin_orders'))

    cursor = mysql.connection.cursor()
    cursor.execute("UPDATE website.orders SET status = %s WHERE order_id = %s", (new_status, order_id))
    mysql.connection.commit()
    cursor.close()

    flash('Order status updated successfully!', 'success')
    return redirect(url_for('admin_orders'))

    


@app.route('/admin/profile')
def admin_profile():
    print("Session Data:", session)  # Debugging - Check session data
    if 'loggedin' not in session:
        return redirect(url_for('admin_login'))
    return render_template('admin_profile.html')


@app.route('/adminlogout')
def admin_logout():
    session.pop('loggedin', None)
    session.pop('admin_id', None)
    session.pop('admin_name', None)
    session.pop('Email', None)
    session.pop('Phone_No', None)

    flash('Logged out successfully!', 'info')
    return redirect(url_for('adminlogin'))  # Redirect to login page




@app.route('/admin/payments')
def admin_payments():
    cursor = mysql.connection.cursor()
    query = """
        SELECT p.payment_id, u.First_Name, u.Last_Name, p.payment_date, 
               p.amount, p.payment_method, p.payment_status
        FROM website.payment p
        JOIN website.user u ON p.user_id = u.user_id
    """
    cursor.execute(query)
    payments = cursor.fetchall()
    cursor.close()
    
    print(payments)  # Debugging: Print fetched data
    
    return render_template('adminpayment.html', payments=payments)


@app.route('/admin/register')
def admin_register():

    cursor=mysql.connection.cursor()
    cursor.execute("SELECT * FROM website.user")
    users = cursor.fetchall()
    cursor.close()

    return render_template('adminuser.html', users=users)

 # User Management
@app.route('/users')
def users():
    cursor = mysql.connection.cursor()
    query = "SELECT * FROM website.User"
    cursor.execute(query)
    data = cursor.fetchall()
    cursor.close()
    return render_template('webindex.html', user=data)


# @app.route('/add_users', methods=['POST'])
# def add_users():
#     if request.method == 'POST':
#         First_Name = request.form['First_Name']
#         Last_Name = request.form['Last_Name']
#         Email = request.form['Email']
#         Password = request.form['Password']
#         Address = request.form['Address']
#         Phone_No = request.form['Phone_No']
        
#         cursor = mysql.connection.cursor()
#         query = 'INSERT INTO website.User (First_Name, Last_Name, Email, Password, Address, Phone_No) VALUES (%s, %s, %s, %s, %s, %s)'
#         cursor.execute(query, (First_Name, Last_Name, Email, Password, Address, Phone_No))
#         mysql.connection.commit()
#         flash('User added successfully', 'success')


#     return redirect(url_for('users'))

@app.route('/add_users', methods=['POST'])
def add_users():
    if request.method == 'POST':
        First_Name = request.form['First_Name']
        Last_Name = request.form['Last_Name']
        Email = request.form['Email']
        Password = request.form['Password']
        Address = request.form['Address']
        Phone_No = request.form['Phone_No']

        cursor = mysql.connection.cursor()

        # Check if the email already exists
        cursor.execute("SELECT * FROM website.User WHERE Email = %s", (Email,))
        existing_user = cursor.fetchone()

        if existing_user:
            flash('Email already exists', 'danger')
        else:
            query = 'INSERT INTO website.User (First_Name, Last_Name, Email, Password, Address, Phone_No) VALUES (%s, %s, %s, %s, %s, %s)'
            cursor.execute(query, (First_Name, Last_Name, Email, Password, Address, Phone_No))
            mysql.connection.commit()
            flash('User added successfully', 'success')

    return redirect(url_for('users'))

@app.route('/edit/<int:User_id>', methods=['GET'])
def get_users(User_id):
    cursor = mysql.connection.cursor()
    query = 'SELECT * FROM website.User WHERE User_id = %s'
    cursor.execute(query, (User_id,))
    data = cursor.fetchone()
    cursor.close()
    return render_template('webupdate.html', user=data)


@app.route('/update/<int:User_id>', methods=['POST'])
def update_user(User_id):
    if request.method == 'POST':
        First_Name = request.form['First_Name']
        Last_Name = request.form['Last_Name']
        Email = request.form['Email']
        Password = request.form['Password']
        Address = request.form['Address']
        Phone_No = request.form['Phone_No']

        cursor = mysql.connection.cursor()
        query = 'UPDATE website.User SET First_Name=%s, Last_Name=%s, Email=%s, Password=%s, Address=%s, Phone_No=%s WHERE User_id=%s'
        cursor.execute(query, (First_Name, Last_Name, Email, Password, Address, Phone_No, User_id))
        mysql.connection.commit()
        flash('User updated successfully')

    return redirect(url_for('users'))

@app.route('/delete/<int:User_id>', methods=['POST'])
def delete_user(User_id):
    if request.form.get("confirm") == "yes":  # Ensure it's a confirmed deletion
        cursor = mysql.connection.cursor()
        cursor.execute('DELETE FROM website.User WHERE User_id = %s', (User_id,))
        mysql.connection.commit()
        flash('User deleted successfully!', 'success')

    return redirect(url_for('users'))

@app.route('/')
def home():
    cursor = mysql.connection.cursor(dictionary=True)
    cursor.execute("SELECT * FROM website.product LIMIT 8")  
    data = cursor.fetchall()
    cursor.close()
    return render_template('index.html', data=data)


@app.route('/product')
def product():
     cursor=mysql.connection.cursor()
     cursor.execute("SELECT * FROM website.product")
     img=cursor.fetchall()
     cursor.close()
     return render_template("shop.html",img=img)






#Managing Products
@app.route('/adminindex')
def adminindex():
    cur = mysql.connection.cursor()
    cur.execute("SELECT * FROM website.product")
    products = cur.fetchall()
    cur.execute("SELECT * FROM website.category")
    categories = cur.fetchall()
    cur.close()
    return render_template('prodindex.html', products=products, cat=categories)

@app.route('/prodindex')
def prodindex():
    return redirect(url_for('adminindex'))

@app.route('/editpro/<int:pid>', methods=['POST', 'GET'])
def edit(pid):
    cur = mysql.connection.cursor()
    cur.execute('SELECT * FROM website.product WHERE Product_id=%s', (pid,))
    pro = cur.fetchone()
    cur.close()

    if not pro:
        flash('Product not found!', 'danger')
        return redirect(url_for('adminindex'))

    return render_template('produpdate.html', pro=pro)

@app.route('/add_product', methods=['POST'])
def add_product():
    product_name = request.form['Product_Name']
    category_id = request.form['category_id']
    description = request.form['Description']
    price = float(request.form['Price'])
    stock_quantity = request.form['Stock_quantity']
    size = request.form['size']
    image_file = request.files['Product_image']

    if image_file and image_file.filename != '':
        filename = secure_filename(image_file.filename)
        relative_path = f"img/products/{filename}"
        image_path = os.path.join(app.config['UPLOAD_FOLDER'], filename)
        image_file.save(image_path)
    else:
        relative_path = ''

    cur = mysql.connection.cursor()
    cur.execute('INSERT INTO website.product (Product_Name, category_id, Description, Price, Stock_quantity, Product_image, size) VALUES (%s, %s, %s, %s, %s, %s, %s)',
                (product_name, category_id, description, price, stock_quantity, relative_path, size))
    mysql.connection.commit()
    cur.close()

    flash('Product added successfully!', 'success')
    return redirect(url_for('adminindex'))

@app.route('/update_product/<int:product_id>', methods=['POST', 'GET'])
def update_product(product_id):
    cur = mysql.connection.cursor()

    if request.method == 'POST':
        Product_Name = request.form.get('Product_Name', '')
        description = request.form.get('Description', '')
        stock_quantity = request.form.get('Stock_quantity', '')
        size = request.form.get('size', '')

        try:
            price = float(request.form.get('Price', 0))
        except ValueError:
            flash('Invalid price entered. Please enter a numeric value.', 'danger')
            return redirect(url_for('update_product', product_id=product_id))

        cur.execute('SELECT Product_image FROM website.product WHERE Product_id = %s', (product_id,))
        product = cur.fetchone()
        existing_image = product[0] if product else ''

        image_file = request.files.get('Product_image')

        if image_file and image_file.filename:
            filename = secure_filename(image_file.filename)
            relative_path = f"img/products/{filename}"
            image_path = os.path.join(app.config['UPLOAD_FOLDER'], filename)
            image_file.save(image_path)
        else:
            relative_path = existing_image  

        cur.execute('''
            UPDATE website.product 
            SET Product_Name=%s, Description=%s, Price=%s, Stock_quantity=%s, Product_image=%s, size=%s 
            WHERE Product_id=%s
        ''', (Product_Name, description, price, stock_quantity, relative_path, size, product_id))

        mysql.connection.commit()
        cur.close()

        flash('Product updated successfully!', 'success')
        return redirect(url_for('adminindex'))

    cur.execute('SELECT * FROM website.product WHERE Product_id = %s', (product_id,))
    product = cur.fetchone()
    cur.close()

    return render_template('produpdate.html', pro=product)

@app.route('/delete_product/<int:product_id>', methods=['POST'])
def delete_product(product_id):
    cur = mysql.connection.cursor()
    cur.execute('SELECT Product_image FROM website.product WHERE Product_id = %s', (product_id,))
    product = cur.fetchone()

    if product and product[0]:
        image_path = os.path.join(app.config['UPLOAD_FOLDER'], product[0].replace("img/products/", ""))
        if os.path.exists(image_path):
            os.remove(image_path)

    cur.execute('DELETE FROM website.product WHERE Product_id = %s', (product_id,))
    mysql.connection.commit()
    cur.close()

    flash('Product deleted successfully!', 'danger')
    return redirect(url_for('adminindex'))

#Managing Categories
@app.route('/category')
def category():
    cursor = mysql.connection.cursor()
    query = "SELECT * FROM website.category"
    cursor.execute(query)
    data=cursor.fetchall()
    #return str(data)
    #cursor.close()
    
    return render_template('categoryindex.html', category=data)
    

# @app.route('/add_category', methods =['POST'])
# def add_category():
#     if request.method=='POST':
#         #category_id = request.form['category_id']
#         category_name = request.form['category_name']
#         cursor = mysql.connection.cursor()
#         query='INSERT INTO website.category (category_name) VALUES (%s)'
#         val=(category_name, )
#         cursor.execute(query,val)
#         mysql.connection.commit()
#         flash('category added successufully')
#         return redirect(url_for('index'))
 
@app.route('/add_category', methods=['POST'])
def add_category():
    if request.method == 'POST':
        category_name = request.form['category_name']

        cursor = mysql.connection.cursor()
        
        # Check if the category already exists
        cursor.execute('SELECT * FROM website.category WHERE category_name = %s', (category_name,))
        existing_category = cursor.fetchone()

        if existing_category:
            flash('Category already exists. Please enter a different name.')
        else:
            cursor.execute('INSERT INTO website.category (category_name) VALUES (%s)', (category_name,))
            mysql.connection.commit()
            flash('Category added successfully')

        cursor.close()
        return redirect(url_for('category'))  

        
@app.route('/edittt/<category_id>', methods = ['POST', 'GET'])
def get_category(category_id):
    cursor = mysql.connection.cursor()
    query='SELECT * FROM website.category WHERE category_id = %s'
    cursor.execute(query,(category_id,))
    #cursor.execute('SELECT * FROM db.student1 WHERE sid = %s', (sid))
    data = cursor.fetchall()
    cursor.close()
    print(data[0])
    return render_template('category_update.html', category= data[0])

 
@app.route('/updateee/<nid>', methods=['POST'])
def update_category(nid):
    if request.method == 'POST':
        #sid = request.form['sid']
        #category_id= request.form['category_id']
        category_name = request.form['category_name']
        cursor = mysql.connection.cursor()
        query='UPDATE website.category SET category_name=%s where category_id=%s'
        cursor.execute(query,(category_name,nid))
        flash('category Updated Successfully')
        mysql.connection.commit()
        return redirect(url_for('category'))


# @app.route('/deleteee/<nid>', methods=['POST', 'GET'])
# def delete_category(nid):
#     try:
#         cursor = mysql.connection.cursor()
#         cursor.execute('DELETE FROM website.category WHERE category_id = %s', (nid,))
#         mysql.connection.commit()
#         flash('Category Removed Successfully', 'success')
#     except mysql.connector.errors.IntegrityError:
#         flash('Cannot delete this category because it is linked to products.', 'danger')  # ❌ Show message
#     return redirect(url_for('category'))

@app.route('/deleteee/<nid>', methods=['POST', 'GET'])
def delete_category(nid):
    cursor = mysql.connection.cursor()
    cursor.execute('DELETE FROM website.category WHERE category_id = %s', (nid,))
    mysql.connection.commit()
    cursor.close()

    flash('Category Removed Successfully', 'success')

    return redirect(url_for('category'))  # Ensure 'category' is the correct function name

    

@app.route('/index')
def index():
    return redirect(url_for('home'))

@app.route('/about')
def about():
    return render_template('about.html')

import re  # Import for validation

@app.route('/adminregister', methods=['GET', 'POST'])
def adminregister():
    msg = ''
    if request.method == 'POST' and 'Name' in request.form and 'Email' in request.form and 'Password' in request.form and 'Phone_No' in request.form:
        Name = request.form['Name']
        Email = request.form['Email']
        Password = request.form['Password']
        Phone_No = request.form['Phone_No']
        
        cursor = mysql.connection.cursor()
        cursor.execute('SELECT * FROM website.admin WHERE Email = %s', (Email,))
        account = cursor.fetchone()

        if account:
            msg = 'Account already exists!'
        elif not re.match(r'[^@]+@[^@]+\.[^@]+', Email):
            msg = 'Invalid email address!'
        elif not re.match(r'[A-Za-z]+', Name):
            msg = 'Name must contain only letters!'
        elif not re.match(r'\d{10}', Phone_No):  # Ensure 10-digit phone number
            msg = 'Invalid phone number!'
        elif not Name or not Email or not Password or not Phone_No:
            msg = 'Please fill out all fields!'
        else:
            cursor.execute('INSERT INTO website.admin (Name, Email, Password, Phone_No) VALUES (%s, %s, %s, %s)',
                           (Name, Email, Password, Phone_No))
            mysql.connection.commit()
            cursor.close()
            flash('Account created successfully! Please log in.', 'success')
            return redirect(url_for('adminlogin'))  # Redirect to login

    return render_template('create-account.html', msg=msg)

@app.route('/adminlogin', methods=['GET', 'POST'])
def adminlogin():
    if request.method == 'POST' and 'Email' in request.form and 'Password' in request.form:
        Email = request.form['Email']
        Password = request.form['Password']

        cursor = mysql.connection.cursor()
        cursor.execute('SELECT * FROM website.admin WHERE Email = %s', (Email,))
        admin = cursor.fetchone()
        cursor.close()

        print("🔍 Debug: Admin Data from DB:", admin)  

        if admin:
            if admin[3] == Password:  
                session['loggedin'] = True
                session['admin_id'] = admin[0]
                session['admin_name'] = admin[1]
                session['Email'] = admin[2]
                session['Phone_No'] = admin[4] 

                print("✅ Debug: Session Data:", session) 
                
                flash('Logged in successfully!', 'success')
                return redirect(url_for('admin_dashboard'))  
            else:
                print("Debug: Password Incorrect")  
                flash('Incorrect password!', 'danger')
        else:
            print("Debug: Email Not Found")  
            flash('Incorrect email!', 'danger')

    return render_template('adminlogin.html')




@app.route('/forgotpassword')
def forgotpassword():
    return render_template('forgot-password.html')

@app.errorhandler(404)
def not_found(error):
    return render_template('404.html'), 404
    
@app.route('/404')
def not_found_page():
    return render_template('404.html')



# from werkzeug.security import check_password_hash
@app.route('/register', methods=['GET', 'POST'])
def register():
    msg = ''
    if request.method == 'POST':
        First_Name = request.form['First_Name']
        Last_Name = request.form['Last_Name']
        Email = request.form['Email']
        Password = request.form['Password']
        Address = request.form['Address']
        Phone_No = request.form['Phone_No']

        cursor = mysql.connection.cursor()
        cursor.execute('SELECT * FROM website.user WHERE Email = %s', (Email,))
        account = cursor.fetchone()

        if account:
            msg = 'Account already exists!'
        elif not re.match(r'^[A-Za-z]+$', First_Name):
            msg = 'First name must contain only letters!'
        elif not re.match(r'^[A-Za-z]+$', Last_Name):
            msg = 'Last name must contain only letters!'
        elif not re.match(r'^[^@]+@[^@]+\.[^@]+$', Email):
            msg = 'Invalid email address!'
        elif not re.match(r'^[0-9]{10}$', Phone_No):
            msg = 'Phone number must be 10 digits!'
        elif not re.match(r'^(?=.*[A-Z])(?=.*[a-z])(?=.*\d)(?=.*[@$!%*?&])[A-Za-z\d@$!%*?&]{8,}$', Password):
            msg = 'Password must have uppercase, lowercase, number, and special character!'
        else:
            cursor.execute('INSERT INTO website.user (First_Name, Last_Name, Email, Password, Address, Phone_No) VALUES (%s, %s, %s, %s, %s, %s)',
                           (First_Name, Last_Name, Email, Password, Address, Phone_No))
            mysql.connection.commit()

            session['loggedin'] = True
            session['User_id'] = cursor.lastrowid
            session['First_Name'] = First_Name
            session['Email'] = Email

            flash('You have successfully registered!', 'success')
            return redirect(url_for('login'))

        cursor.close()

    return render_template('createnew_acc.html', msg=msg)

@app.route('/login', methods=['GET', 'POST'])
def login():
    msg = ''
    if request.method == 'POST':
        Email = request.form['Email']
        Password = request.form['Password']
        
        cursor = mysql.connection.cursor()
        cursor.execute('SELECT * FROM website.user WHERE Email = %s AND Password = %s', (Email, Password))
        account = cursor.fetchone()
        cursor.close()

        if account:
            session['loggedin'] = True
            session['User_id'] = account[0]
            session['Email'] = account[3]  
            flash('Logged in successfully!', 'success')
            return redirect(url_for('profile'))
        else:
            msg = 'Incorrect email or password!'

    return render_template('login.html', msg=msg)

@app.route('/logout')
def logout():
    session.clear()
    return redirect(url_for('login'))

@app.route('/profile')
def profile():
    if 'loggedin' in session and 'User_id' in session:
        cursor = mysql.connection.cursor()

        # ✅ Fetch user details
        cursor.execute(
            'SELECT First_Name, Last_Name, Email FROM website.user WHERE User_id = %s', 
            (session['User_id'],)
        )
        user = cursor.fetchone()

        # ✅ Fetch recent order (latest order by date)
        cursor.execute(
            'SELECT order_id, order_date, total_amount, status FROM website.orders '
            'WHERE user_id = %s ORDER BY order_date DESC LIMIT 1', 
            (session['User_id'],)
        )
        recent_order = cursor.fetchone()

        # ✅ Fetch all past orders
        cursor.execute(
            'SELECT order_id, order_date, total_amount, status FROM website.orders '
            'WHERE user_id = %s ORDER BY order_date DESC', 
            (session['User_id'],)
        )
        orders = cursor.fetchall()

        cursor.close()

        if user:
            return render_template('profile.html', user=user, recent_order=recent_order, orders=orders)

    flash("Please log in to access your profile.", "warning")
    return redirect(url_for('login'))  # Redirect to login if not logged in


@app.route('/viewprofile',methods=['POST','GET'])
def viewprofile():
    return render_template('profile.html')



@app.route('/shop')
@app.route('/shop/<category_id>')
def shop(category_id='all'):
    cursor = mysql.connection.cursor(dictionary=True)

    #  Fetch all categories
    cursor.execute("SELECT * FROM website.category")
    categories = cursor.fetchall()

    #  Fetch products based on category
    if category_id == 'all':
        cursor.execute("SELECT * FROM website.product")
    else:
        cursor.execute("SELECT * FROM website.product WHERE category_id = %s", (category_id,))

    products = cursor.fetchall()
    cursor.close()

    return render_template("shop.html", products=products, categories=categories, category_id=category_id)

# 
 
@app.route('/cat', methods=['POST'])
def cat():
    cid = request.form['cat']  # Corrected request.form syntax
    cursor1 = mysql.connection.cursor()
    cursor1.execute("SELECT * FROM product WHERE category_id=%s", (cid,))
    products = cursor1.fetchall()  # Fetch all products of the selected category
    cursor1.close()

    return render_template('shop.html', products=products, category_id=cid)

   
    
@app.route('/productview', methods=['GET', 'POST'])
def productview():
    msg = ''
    if request.method == 'POST':
        Product_id = request.form['Product_id']
        Product_Name = request.form['Product_Name']
        Category_id = request.form['Category_id']
        Description = request.form['Description']
        Price= request.form['Price']
        Stock_quantity= request.form['Stock_quantity']
        Product_image = request.form['Product_image']
        cursor = mysql.connection.cursor()
        query='INSERT INTO website.product (Product_id,Product_Name,Category_id,Description,Price,Stock_quantity,Product_image) VALUES (%s, %s,%s, %s,%s,%s,%s)'
        val=(Product_id,Product_Name,Category_id,Description,Price,Stock_quantity,Product_image )
        cursor.execute(query,val)
        mysql.connection.commit()
       # flash('product added successufully')
        #return redirect(url_for('index'))
 
        cursor = mysql.connection.cursor()
        query = "SELECT * FROM website.product WHERE category_id==101"
        cursor.execute(query)
        data=cursor.fetchall()
        #return str(data)
        #cursor.close()
        return render_template('shop.html', data=data)


@app.route('/single-product/<Product_id>')
def single_product(Product_id):

    cursor = mysql.connection.cursor(dictionary=True)
    cursor.execute("SELECT category.category_name,product.* FROM website.category,website.product WHERE category.category_id=product.category_id and Product_id = %s", (Product_id,))
    product = cursor.fetchone()
    cursor.close()
    

    if not product:
        return "Product not found", 404

    return render_template("single-product.html", product=product)


   

@app.route('/contact', methods=['GET', 'POST'])
def contact():
    if request.method == 'POST':
        name = request.form.get('name')
        email = request.form.get('email')
        phone = request.form.get('phone')  
        subject = request.form.get('subject')
        message_content = request.form.get('message')

        cursor = mysql.connection.cursor()
        query = 'INSERT INTO contact (name, email, phone, subject, message) VALUES (%s, %s, %s, %s, %s)'
        val = (name, email, phone, subject, message_content)
        cursor.execute(query, val)
        mysql.connection.commit()
        cursor.close()

        flash("Your message has been sent successfully!", "success")  
        return redirect(url_for('contact'))  # Redirects back to the contact page

    return render_template("contact.html")


@app.route('/quote', methods=['GET', 'POST'])
def quote():
    if request.method == 'POST':
        name=request.form.get('name')
        email=request.form.get('email')
        mobile=request.form.get('mobile')
        service=request.form.get('service')
        note=request.form.get('note')
        cursor = mysql.connection.cursor()
        query='INSERT INTO quote(name,email,mobile,service,note) VALUES (%s,%s,%s,%s,%s)'
        val=(name,email,mobile,service,note)
        cursor.execute(query,val)
        mysql.connection.commit()
    return render_template("quote.html")

@app.route('/cart', methods=['GET'])
def view_cart():
    user_id = session.get('User_id')
    if not user_id:
        flash("Please log in to view your cart!", "warning")
        return redirect(url_for("login"))

    cart_items = session.get("cart", {})

    # ✅ Convert values to float before calculations
    subtotal = sum(float(item["total_price"]) for item in cart_items.values())
    total = subtotal + 50  # ₹50 shipping

    return render_template("cart.html", user_id=user_id, subtotal=subtotal, total=total)

@app.route('/update_cart/<int:Product_id>', methods=['POST'])
def update_cart(Product_id):
    user_id = session.get("User_id")

    if user_id is None:
        flash("Please log in to update your cart.", "warning")
        return redirect(url_for("login"))

    if "cart" in session and str(Product_id) in session["cart"]:
        new_quantity = request.form.get("quantity")

        try:
            new_quantity = int(new_quantity)  # ✅ Convert quantity to integer
            if new_quantity < 1:
                flash("Quantity must be at least 1.", "warning")
                return redirect(url_for("view_cart"))

            product_price = float(session["cart"][str(Product_id)]["Price"])  # ✅ Convert price to float
            new_total_price = new_quantity * product_price  # ✅ Correct total calculation

            # ✅ Update session cart
            session["cart"][str(Product_id)]["quantity"] = new_quantity
            session["cart"][str(Product_id)]["total_price"] = new_total_price
            session.modified = True

            # ✅ Update database with correct values
            cursor = mysql.connection.cursor()
            cursor.execute("""
                UPDATE website.cart 
                SET quantity = %s, total = %s 
                WHERE Product_id = %s AND User_id = %s
            """, (new_quantity, new_total_price, Product_id, user_id))
            mysql.connection.commit()
            cursor.close()

            flash("Cart updated successfully!", "success")

        except ValueError:
            flash("Invalid quantity. Please enter a valid number.", "danger")

    return redirect(url_for("view_cart"))



@app.route('/add_to_cart/<Product_id>', methods=['POST','GET'])
def add_to_cart(Product_id):
    User_id = session.get('User_id')  # Check if user is logged in

    if User_id is None:
        flash("Please log in to add products to the cart.", "warning")
        return redirect(url_for("login"))

    cursor = mysql.connection.cursor()
    cursor.execute("SELECT * FROM website.product WHERE Product_id = %s", (Product_id,))
    Product = cursor.fetchone()
    cursor.close()

    if Product is None:
        flash("Product not found!", "danger")
        return redirect(url_for("index"))

    Product_Name = Product[1]  
    Product_image = Product[6]  
    Price = Product[4]  
    quantity = int(request.form.get("quantity", 1))
    total_price = Price * quantity  
    Product_key = str(Product_id)

    if "cart" not in session:
        session["cart"] = {}

    if Product_key in session["cart"]:
        session["cart"][Product_key]["quantity"] += quantity
        session["cart"][Product_key]["total_price"] = session["cart"][Product_key]["quantity"] * Price
    else:
        session["cart"][Product_key] = {
            "User_id": User_id,
            "Product_id": Product_id,
            "Product_Name": Product_Name,
            "Product_image": Product_image,
            "Price": Price,
            "quantity": quantity,
            "total_price": total_price
        }

    session.modified = True

    # Insert or Update in Database
    cursor1 = mysql.connection.cursor()
    cursor1.execute('''
        INSERT INTO website.cart (User_id, Product_id, quantity, total)
        VALUES (%s, %s, %s, %s)
        ON DUPLICATE KEY UPDATE quantity = quantity + %s, total = total + %s
    ''', (User_id, Product_id, quantity, total_price, quantity, total_price))
    
    mysql.connection.commit()
    cursor1.close()

    flash(f"{Product_Name} added to cart!", "success")
    return redirect(url_for("view_cart"))

@app.route('/remove_from_cart/<Product_id>', methods=['POST'])
def remove_from_cart(Product_id):
    User_id = session.get("User_id")

    if User_id is None:
        flash("Please log in to manage your cart.", "warning")
        return redirect(url_for("login"))

    Product_key = str(Product_id)

    if "cart" in session and Product_key in session["cart"]:
        del session["cart"][Product_key]
        session.modified = True

        # Remove from database
        cursor = mysql.connection.cursor()
        cursor.execute("DELETE FROM website.cart WHERE Product_id = %s AND User_id = %s", (Product_id, User_id))
        mysql.connection.commit()
        cursor.close()

        flash("Item removed from cart!", "info")

    return redirect(url_for("view_cart"))

@app.route('/checkout/<int:user_id>')
def checkout(user_id):
    if not user_id:
        flash("Invalid session. Please log in again.", "warning")
        return redirect(url_for("login"))

    cursor = mysql.connection.cursor(dictionary=True)

    # ✅ Fetch user details with correct column names
    cursor.execute("""
        SELECT First_Name AS first_name, Last_Name AS last_name, 
               Email AS email, Address AS address, Phone_No AS phone 
        FROM website.user WHERE User_id = %s
    """, (user_id,))
    user_data = cursor.fetchone()

    if not user_data:
        # ✅ Provide default empty values if no user data exists
        user_data = {
            "first_name": "",
            "last_name": "",
            "email": "",
            "phone": "",
            "address": ""
        }

    # ✅ Fetch cart items
    cursor.execute("""
    SELECT cart.Product_id, product.product_name, product.Product_image, cart.quantity, product.price 
    FROM website.cart 
    JOIN website.product ON cart.Product_id = product.Product_id 
    WHERE cart.user_id = %s
    """, (user_id,))
    
    cart_items = cursor.fetchall()
    cursor.close()

    if not cart_items:
        flash("Your cart is empty!", "warning")
        return redirect(url_for("view_cart"))

    subtotal = sum(item["quantity"] * item["price"] for item in cart_items)
    shipping = 50
    total = subtotal + shipping

    return render_template('checkout.html', user_id=user_id, cart_items=cart_items, subtotal=subtotal, shipping=shipping, total=total, user_data=user_data)
@app.route('/place_order/<user_id>', methods=['POST'])
def place_order(user_id):
    first_name = request.form['first_name']
    last_name = request.form['last_name']
    email = request.form['email']
    phone = request.form['phone']
    address = request.form['address']
    city = request.form['city']
    state = request.form['state']
    zip_code = request.form['zip_code']
    payment_method = request.form['payment_method']

    cursor = mysql.connection.cursor()

    # Get cart items
    cursor.execute("""
        SELECT cart.Product_id, cart.quantity, product.price 
        FROM website.cart 
        JOIN website.product ON cart.Product_id = product.Product_id 
        WHERE cart.user_id = %s
    """, (user_id,))
    
    cart_items = cursor.fetchall()

    if not cart_items:
        flash("Your cart is empty! Please add items before placing an order.", "warning")
        return redirect(url_for("checkout", user_id=user_id))

    # Calculate total amount
    subtotal = sum(item[1] * item[2] for item in cart_items)
    shipping = 50
    total = subtotal + shipping
    order_date = date.today()
    status = "Pending"

    # Insert order details into `orders` table
    cursor.execute("""
        INSERT INTO website.orders 
        (user_id, order_date, quantity, rate, total_amount, status, 
         first_name, last_name, email, phone, address, city, state, zip_code, payment_method) 
        VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
    """, (user_id, order_date, 0, 0, total, status, 
          first_name, last_name, email, phone, address, city, state, zip_code, payment_method))

    # Get the last inserted order_id
    order_id = cursor.lastrowid

    # Insert each item into `order_items` table
    for item in cart_items:
        product_id, quantity, price = item
        total_amount = quantity * price
        cursor.execute("""
            INSERT INTO website.order_items (order_id, product_id, quantity, price, total) 
            VALUES (%s, %s, %s, %s, %s)
        """, (order_id, product_id, quantity, price, total_amount))

    # ✅ **Insert Payment Record (New Fix)**
    # ✅ Ensure Payment Record is Always Created
    cursor.execute("""
    INSERT INTO website.payment (order_id, user_id, payment_date, amount, payment_method, payment_status) 
    VALUES (%s, %s, %s, %s, %s, %s)
    """, (order_id, user_id, order_date, total, payment_method, "Pending"))

    # Clear the cart after placing the order
    cursor.execute("DELETE FROM website.cart WHERE user_id = %s", (user_id,))
    
    mysql.connection.commit()
    cursor.close()

    flash("Your order has been placed successfully!", "success")
    
    return redirect(url_for('billing_summary', user_id=user_id, order_id=order_id))



@app.route('/bill/<order_id>')
def display_bill(order_id):
    cursor = mysql.connection.cursor()

    # Fetch order details
    cursor.execute("SELECT * FROM website.orders WHERE order_id = %s", (order_id,))
    order = cursor.fetchone()

    # Fetch billing details
    cursor.execute("SELECT * FROM website.billing WHERE order_id = %s", (order_id,))
    billing = cursor.fetchone()

    # Fetch ordered items
    cursor.execute("""
        SELECT oi.Product_id, p.name, oi.quantity, oi.rate, oi.total_amount 
        FROM website.order_items oi
        JOIN website.product p ON oi.Product_id = p.Product_id
        WHERE oi.order_id = %s
    """, (order_id,))
    
    order_items = cursor.fetchall()
    cursor.close()

    return render_template('bill.html', order=order, billing=billing, order_items=order_items)

@app.route('/billing_summary/<user_id>/<order_id>')
def billing_summary(user_id, order_id):
    cursor = mysql.connection.cursor()

    # Fetch order details including billing info
    cursor.execute("""
        SELECT * FROM website.orders WHERE order_id = %s
    """, (order_id,))
    order = cursor.fetchone()

    # Fetch order items
    cursor.execute("""
        SELECT p.product_name, oi.quantity, oi.price, oi.total
        FROM website.order_items oi
        JOIN website.product p ON oi.product_id = p.Product_id
        WHERE oi.order_id = %s
    """, (order_id,))
    order_items = cursor.fetchall()

    cursor.close()

    return render_template("billing.html", order=order, order_items=order_items)

@app.route('/reports')
def reports():
    cursor = mysql.connection.cursor()
    cursor.execute("SELECT category_id, category_name FROM website.category")
    catreport = cursor.fetchall()
    print("Cat : ",catreport)
    cursor.close()

    cursor1 = mysql.connection.cursor()
    cursor1.execute("SELECT size FROM website.product")  # Fetch category names too
    size = cursor1.fetchall()
    print('Size : ',size)
    cursor1.close()
    
    return render_template("report.html", catreport=catreport,size=size)  
   
   
#User report
@app.route('/user_report')
def user_report():
    now=date.today()
    cursor = mysql.connection.cursor()
   
    cursor.execute("SELECT First_Name,Last_Name,Email FROM website.user ")
    result = cursor.fetchall()
    print(result)  
       
    pdf = FPDF("L")
    pdf.add_page()
    page_width = pdf.w - 2 * pdf.l_margin
       
    pdf.set_font('Times','B',14.0)
    pdf.cell(page_width, 0.0, "Sparsh Maticha", align='C')
    pdf.ln(10)
    pdf.cell(page_width, 0.0, "Bapat Camp, Kolhapur", align='C')
    pdf.ln(15)
    pdf.cell(page_width, 0.0, "Users Report", align='C')
    pdf.ln(10)
    pdf.set_font('Times','B',12.0)
    # pdf.cell(page_width, 0.0, 'Date :- '+str(date.strftime("%d / %m / %y")), align='L')

    now = date.today()  # Get today's date

    pdf.cell(page_width, 0.0, 'Date :- ' + now.strftime("%d / %m / %Y"), align='L')  
    pdf.ln(5)  
    pdf.cell(page_width, 0.0, 'Time :- ' + datetime.now().strftime("%H:%M:%S"), align='L')  

    

    pdf.ln(10)


    pdf.set_font('Courier','',12)
       
    col_width = page_width/5
    pdf.ln(1)

    th = pdf.font_size
    i=1
    pdf.cell(20,th,"Sr.No",border=1,align="C")
    # pdf.cell(20,th,"User ID",border=1,align="C")
    pdf.cell(35,th,"First Name",border=1,align="C")
    pdf.cell(40,th,"Last Name",border=1,align="C")
    pdf.cell(80,th,"Email",border=1,align="C")

    pdf.ln(th)
   
    for col in result:
        pdf.cell(20, th, str(i), border=1, align="C")  # Sr. No
        pdf.cell(35, th, col[0].encode('latin-1', 'ignore').decode('latin-1'), border=1, align="C")  # First Name
        pdf.cell(40, th, col[1].encode('latin-1', 'ignore').decode('latin-1'), border=1, align="C")  # Last Name
        pdf.cell(80, th, col[2].encode('latin-1', 'ignore').decode('latin-1'), border=1, align="C")  # Email
        # print("Total users fetched from DB:", len(result))  

        # print(f"Printing user {i}: {col[0]} {col[1]} - {col[2]}")

        i += 1
        pdf.ln(th)


    pdf.ln(10)
    pdf.set_font('Times', '', 10.0)
    pdf.cell(page_width, 0.0, '- end of report -', align='C')


    cursor.close()

    return Response(pdf.output(dest='S').encode('latin-1'), mimetype='application/pdf',headers={'Content-Disposition': 'attachment; filename=users_report.pdf'})


#product report
@app.route('/products_report')
def products_report():
    cursor = mysql.connection.cursor()
    query = """
    SELECT p.Product_Name, c.category_name, p.Description, 
           p.Price, p.Stock_quantity, p.size 
    FROM website.product p 
    JOIN website.category c ON p.category_id = c.category_id
    """
    cursor.execute(query)
    result = cursor.fetchall()

    pdf = FPDF(orientation="L", unit="mm", format="A4")
    pdf.add_page()
    page_width = pdf.w - 2 * pdf.l_margin

    pdf.set_font('Times', 'B', 16)
    pdf.cell(page_width, 10, "Sparsh Maticha", align='C', ln=True)
    pdf.cell(page_width, 10, "Bapat Camp, Kolhapur", align='C', ln=True)
    pdf.ln(5)
    pdf.cell(page_width, 10, "Products Report", align='C', ln=True)
    pdf.ln(5)
    pdf.set_font('Times', 'B', 12)
    pdf.cell(page_width, 6, 'Date: ' + datetime.now().strftime("%d / %m / %Y"), align='L', ln=True)
    pdf.cell(page_width, 6, 'Time: ' + datetime.now().strftime("%H:%M:%S"), align='L', ln=True)
    pdf.ln(5)

    pdf.set_font('Courier', 'B', 11)
    th = 8  # Row height

    # Adjusted column widths after removing Product ID
    column_widths = [12, 50, 45, 90, 25, 25, 30]  

    headers = ["Sr.No", "Product Name", "Category Name", "Description",
               "Price", "Stock Qty", "Size"]

    for i, header in enumerate(headers):
        pdf.cell(column_widths[i], th, header, border=1, align="C")
    pdf.ln(th)

    pdf.set_font('Courier', '', 10)

    def safe_encode(value):
        """ Ensure value is a string before encoding. """
        if isinstance(value, str):
            return value.encode('latin-1', 'ignore').decode('latin-1')
        return str(value)

    for i, col in enumerate(result, start=1):
        description_lines = pdf.multi_cell(column_widths[3], th, safe_encode(col[2]), border=0, align="L", split_only=True)
        row_height = max(len(description_lines) * th, th)  

        pdf.cell(column_widths[0], row_height, str(i), border=1, align="C")
        pdf.cell(column_widths[1], row_height, safe_encode(col[0]), border=1, align="L")
        pdf.cell(column_widths[2], row_height, safe_encode(col[1]), border=1, align="L")

        x, y = pdf.get_x(), pdf.get_y()
        pdf.multi_cell(column_widths[3], th, safe_encode(col[2]), border=1, align="L")
        pdf.set_xy(x + column_widths[3], y)

        pdf.cell(column_widths[4], row_height, str(col[3]), border=1, align="R")
        pdf.cell(column_widths[5], row_height, str(col[4]), border=1, align="C")
        pdf.cell(column_widths[6], row_height, safe_encode(col[5]), border=1, align="L")

        pdf.ln(row_height)

    pdf.ln(10)
    pdf.set_font('Times', 'I', 10)
    pdf.cell(page_width, 6, '- End of Report -', align='C')

    cursor.close()

    return Response(pdf.output(dest='S').encode('latin-1'), mimetype='application/pdf',
                    headers={'Content-Disposition': 'attachment; filename=products_report.pdf'})

@app.route('/download', methods=['GET', 'POST'])
def summary_report():
    if request.method == 'POST':
        now = date.today()
        # Get the category ID (as string) from the form:
        category_id = request.form.get('catreport', '').strip()

        cursor = mysql.connection.cursor()
        
        # Retrieve the category name using the category ID
        cursor.execute("SELECT category_name FROM website.category WHERE category_id = %s", (category_id,))
        category_row = cursor.fetchone()
        
        if category_row:
            catreport = category_row[0]  # Use the category name for display
        else:
            cursor.close()
            return "Invalid Category", 400
        
        # Use the category ID in the product query
        cursor.execute("""
            SELECT p.Product_Name, p.Stock_quantity, p.Price, c.category_name 
            FROM website.product p 
            JOIN website.category c ON p.category_id = c.category_id 
            WHERE p.category_id = %s
        """, (category_id,))
        result = cursor.fetchall()

        pdf = FPDF(orientation="L", unit="mm", format="A4")
        pdf.add_page()
        page_width = pdf.w - 2 * pdf.l_margin

        pdf.set_font('Times', 'B', 14)
        pdf.cell(page_width, 10, "Sparsh Maticha", align='C', ln=True)
        pdf.cell(page_width, 10, "Bapat Camp, Kolhapur", align='C', ln=True)
        pdf.ln(15)
        pdf.cell(page_width, 10, "Products in " + catreport + " Category", align='C', ln=True)
        pdf.ln(10)

        pdf.set_font('Times', 'B', 12)
        pdf.cell(page_width/2, 6, 'Date: ' + now.strftime("%d/%m/%Y"), align='L')
        pdf.cell(page_width/2, 6, 'Time: ' + datetime.now().strftime("%H:%M:%S"), align='R', ln=True)
        pdf.ln(5)

        pdf.set_font('Courier', 'B', 12)
        th = pdf.font_size + 2

        pdf.cell(15, th, "Sr.No", border=1, align="C")
        pdf.cell(55, th, "Product Name", border=1, align="C")
        pdf.cell(40, th, "Stock Quantity", border=1, align="C")
        pdf.cell(40, th, "Rate", border=1, align="C")
        pdf.ln(th)

        pdf.set_font('Courier', '', 12)

        def safe_encode(value):
            """Ensure value is a string before encoding."""
            if isinstance(value, str):
                return value.encode('latin-1', 'ignore').decode('latin-1')
            return str(value)

        for i, col in enumerate(result, start=1):
            pdf.cell(15, th, str(i), border=1, align="C")
            pdf.cell(55, th, safe_encode(col[0]), border=1, align="C")
            pdf.cell(40, th, str(col[1]), border=1, align="C")
            pdf.cell(40, th, str(col[2]), border=1, align="C")
            pdf.ln(th)

        pdf.ln(10)
        pdf.set_font('Times', '', 10)
        pdf.cell(page_width, 6, '- end of report -', align='C')

        cursor.close()

        return Response(pdf.output(dest='S').encode('latin-1'),
                        mimetype='application/pdf',
                        headers={'Content-Disposition': 'attachment; filename=category_report.pdf'})

#sizewise report
@app.route('/downloadsize', methods=['POST','GET'])
def download_size_report():
    if request.method=='POST':
        size = request.form.get('size')

        cursor = mysql.connection.cursor()
        cursor.execute("""
            SELECT product.Product_Name, category.category_name, 
                product.Stock_quantity, product.Price 
            FROM website.product 
            JOIN website.category 
            ON product.category_id = category.category_id 
            WHERE product.size = %s
        """, (size,))
        result = cursor.fetchall()


        pdf = FPDF(orientation="L")
        pdf.add_page()
        page_width = pdf.w - 2 * pdf.l_margin

        pdf.set_font('Times', 'B', 14.0)
        pdf.cell(page_width, 0.0, "Sparsh Maticha", align='C')
        pdf.ln(10)
        pdf.cell(page_width, 0.0, "Bapat Camp, Kolhapur", align='C')
        pdf.ln(15)
        pdf.cell(page_width, 0.0, "Products Report", align='C')
        pdf.ln(10)

        pdf.set_font('Times', 'B', 12.0)
        pdf.cell(page_width, 0.0, 'Date :- ' + datetime.now().strftime("%d / %m / %Y"), align='L')
        pdf.ln(5)
        pdf.cell(page_width, 0.0, 'Time :- ' + datetime.now().strftime("%H:%M:%S"), align='L')
        pdf.ln(10)

        pdf.set_font('Courier', '', 12)
        th = pdf.font_size + 2

        pdf.cell(15, th, "Sr.No", border=1, align="C")
        pdf.cell(40, th, "Product Name", border=1, align="C")
        pdf.cell(40, th, "Category Name", border=1, align="C")
        pdf.cell(40, th, "Stock Quantity", border=1, align="C")
        pdf.cell(40, th, "Rate", border=1, align="C")
        pdf.ln(th)

        def safe_encode(value):
            """ Ensure value is a string before encoding. """
            if isinstance(value, str):
                return value.encode('latin-1', 'ignore').decode('latin-1')
            return str(value)

        for i, col in enumerate(result, start=1):
            pdf.cell(15, th, str(i), border=1, align="C")
            pdf.cell(40, th, col[0], border=1, align="C")  # User Name
            pdf.cell(40, th, safe_encode(col[1]), border=1, align="C")  # Category Name
            pdf.cell(40, th, str(col[2]), border=1, align="C")  # Quantity
            pdf.cell(40, th, str(col[3]), border=1, align="C")  # Rate
            
            pdf.ln(th)

        pdf.ln(10)
        pdf.set_font('Times', '', 10.0)
        pdf.cell(page_width, 0.0, '- end of report -', align='C')

        cursor.close()

        return Response(pdf.output(dest='S').encode('latin-1'), mimetype='application/pdf', headers={'Content-Disposition': 'attachment; filename=size_report.pdf'})

#date-wise report
@app.route('/download/report/pdf', methods=['POST','GET'])
def date_report():
    if request.method == "POST":
        fdate = request.form.get('fdate')
        tdate = request.form.get('tdate')

        # Convert string dates to datetime
        fdate = datetime.strptime(fdate, '%Y-%m-%d')
        tdate = datetime.strptime(tdate, '%Y-%m-%d')

        now = date.today()
        cursor = mysql.connection.cursor()

        


        query = """
        SELECT u.First_Name, u.Last_Name, c.category_name, p.Product_Name,
            oi.quantity, oi.price, oi.total, o.order_date
        FROM website.user AS u
        JOIN website.orders AS o ON u.user_id = o.user_id
        JOIN website.order_items AS oi ON o.order_id = oi.order_id
        JOIN website.product AS p ON oi.product_id = p.Product_id
        JOIN website.category AS c ON p.category_id = c.category_id
        WHERE o.order_date BETWEEN %s AND %s
        ORDER BY o.order_date;
        """


        cursor.execute(query, (fdate, tdate,))
        result = cursor.fetchall()
        cursor.close()

        # Initialize PDF
        # pdf = FPDF()
        # pdf.add_page()
        pdf = FPDF('L', 'mm', 'A4')  # 'L' enables Landscape mode
        pdf.add_page()
        page_width = pdf.w - 2 * pdf.l_margin  # Adjusted for landscape width


        page_width = pdf.w - 2 * pdf.l_margin

        pdf.set_font('Times', 'B', 14.0)
        pdf.cell(page_width, 0.0, "Sparsh Maticha", align='C')
        pdf.ln(10)
        pdf.cell(page_width, 0.0, "Bapat Camp, Kolhapur", align='C')
        pdf.ln(10)
        pdf.cell(page_width, 0.0, "Datewise Report", align='C')
        pdf.ln(10)
        pdf.set_font('Times', 'B', 12.0)
        pdf.cell(page_width, 0.0, 'Date: ' + now.strftime("%d / %m / %Y"), align='')
        pdf.ln(10)
        pdf.cell(page_width, 0.0, f'From: {fdate.strftime("%d / %m / %Y")}  To: {tdate.strftime("%d / %m / %Y")}', align='L')
        pdf.ln(10)

        # Table Headers
        pdf.set_font('Courier', '', 12)
        pdf.cell(15, 8, "Sr.No", border=1, align="C")
        pdf.cell(30, 8, "First Name", border=1, align="C")
        pdf.cell(35, 8, "Last Name", border=1, align="C")   
        pdf.cell(35, 8, "Category", border=1, align="C")    
        pdf.cell(65, 8, "Product", border=1, align="C")     
        pdf.cell(30, 8, "Quantity", border=1, align="C")    
        pdf.cell(30, 8, "Rate", border=1, align="C")        
        pdf.cell(40, 8, "Total Amount", border=1, align="C")  
        pdf.ln()

       

       
       # Table Data
        for i, row in enumerate(result, start=1):
            pdf.cell(15, 8, str(i), border=1, align='C')
            pdf.cell(30, 8, row[0], border=1)  # First Name
            pdf.cell(35, 8, row[1], border=1)  # Last Name
            pdf.cell(35, 8, row[2], border=1)  # Category Name
            # pdf.cell(65, 8, row[3], border=1, align='L')  # Product Name
            pdf.cell(65, 8, row[3].strip(), border=1, align='L')  # Trim and align left

            pdf.cell(30, 8, str(row[4]), border=1, align='C')  # Quantity
            pdf.cell(30, 8, str(row[5]), border=1, align='C')  # Rate
            pdf.cell(40, 8, str(row[6]), border=1, align='C')  # Total Amount
            pdf.ln()

            # pdf.cell(15, 8, str(i), border=1, align='C')
            # pdf.cell(30, 8, row[0], border=1)  # First Name
            # pdf.cell(30, 8, row[1], border=1)  # Last Name
            # pdf.cell(30, 8, row[2], border=1)  # Category Name
            # pdf.cell(60, 8, row[3], border=1)  # Product Name
            # pdf.cell(30, 8, str(row[4]), border=1, align='C')  # Quantity
            # pdf.cell(30, 8, str(row[5]), border=1, align='C')  # Rate
            # pdf.cell(40, 8, str(row[6]), border=1, align='C')  # Total Amount
            # pdf.ln()

        pdf.ln(10)
        pdf.set_font('Times', '', 10.0)
        pdf.cell(page_width, 0.0, '- End of Report -', align='C')

        return Response(pdf.output(dest='S').encode('latin-1'), mimetype='application/pdf',
                        headers={'Content-Disposition': 'attachment; filename=report.pdf'})

if __name__ == '__main__':
    app.run(debug=True)