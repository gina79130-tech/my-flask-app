from flask import Flask, render_template, redirect, url_for, flash, request, send_from_directory
from flask_sqlalchemy import SQLAlchemy
from flask_login import LoginManager, UserMixin, login_user, logout_user, current_user, login_required
from werkzeug.security import generate_password_hash, check_password_hash
from werkzeug.utils import secure_filename
import os
import uuid

from flask_auction_app.forms import ProductForm, ShippingAddressForm, OrderForm

app = Flask(__name__)
app.config['SECRET_KEY'] = os.environ.get('SECRET_KEY', 'your_secret_key') # Load from environment variable
app.config['SQLALCHEMY_DATABASE_URI'] = os.environ.get('DATABASE_URL', 'sqlite:///site.db') # Load from environment variable
app.config['UPLOAD_FOLDER'] = 'static/uploads'
app.config['MAX_CONTENT_LENGTH'] = 16 * 1024 * 1024  # 16MB max upload size
db = SQLAlchemy(app)
login_manager = LoginManager(app)
login_manager.login_view = 'login'

ALLOWED_EXTENSIONS = {'png', 'jpg', 'jpeg', 'gif'}

def allowed_file(filename):
    return '.' in filename and \
           filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

@login_manager.user_loader
def load_user(user_id):
    return User.query.get(int(user_id))

class User(db.Model, UserMixin):
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(20), unique=True, nullable=False)
    email = db.Column(db.String(120), unique=True, nullable=False)
    password_hash = db.Column(db.String(128), nullable=False)
    role = db.Column(db.String(10), nullable=False, default='buyer') # 'buyer' or 'seller'

    def set_password(self, password):
        self.password_hash = generate_password_hash(password)

    def check_password(self, password):
        return check_password_hash(self.password_hash, password)

    def __repr__(self):
        return f"User('{self.username}', '{self.email}', '{self.role}')"

class Product(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False)
    description = db.Column(db.Text, nullable=False)
    specifications = db.Column(db.Text, nullable=True)
    condition = db.Column(db.String(50), nullable=False)
    price = db.Column(db.Float, nullable=False)
    image_filename = db.Column(db.String(100), nullable=False, default='default.jpg')
    seller_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    seller = db.relationship('User', backref='products')

    def __repr__(self):
        return f"Product('{self.name}', '{self.price}', '{self.condition}')"

class ShippingAddress(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    recipient_name = db.Column(db.String(100), nullable=False)
    phone_number = db.Column(db.String(20), nullable=False)
    address_line1 = db.Column(db.String(200), nullable=False)
    address_line2 = db.Column(db.String(200), nullable=True)
    city = db.Column(db.String(100), nullable=False)
    state = db.Column(db.String(100), nullable=False)
    zip_code = db.Column(db.String(20), nullable=False)
    country = db.Column(db.String(100), nullable=False, default='Taiwan')

    user = db.relationship('User', backref='shipping_addresses')

    def __repr__(self):
        return f"ShippingAddress('{self.recipient_name}', '{self.address_line1}', '{self.city}')"

class Order(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    product_id = db.Column(db.Integer, db.ForeignKey('product.id'), nullable=False)
    buyer_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    order_date = db.Column(db.DateTime, nullable=False, default=db.func.now())
    status = db.Column(db.String(50), nullable=False, default='pending') # pending, confirmed, shipped, delivered, cancelled
    shipping_method = db.Column(db.String(100), nullable=False)
    shipping_address_id = db.Column(db.Integer, db.ForeignKey('shipping_address.id'), nullable=False)
    total_price = db.Column(db.Float, nullable=False)

    product = db.relationship('Product', backref='orders')
    buyer = db.relationship('User', backref='orders')
    shipping_address = db.relationship('ShippingAddress', backref='orders')

    def __repr__(self):
        return f"Order('{self.buyer_id}', '{self.product_id}', '{self.status}', '{self.order_date}')"

@app.route('/')
def home():
    products = Product.query.all()
    return render_template('products.html', products=products)

@app.route('/product/new', methods=['GET', 'POST'])
@login_required
def create_product():
    if current_user.role != 'seller':
        flash('只有賣家才能上架商品', 'danger')
        return redirect(url_for('home'))
    form = ProductForm()
    if form.validate_on_submit():
        if form.image.data:
            picture_file = save_picture(form.image.data)
        else:
            picture_file = 'default.jpg' # Or handle no image case

        product = Product(
            name=form.name.data,
            description=form.description.data,
            specifications=form.specifications.data,
            condition=form.condition.data,
            price=form.price.data,
            image_filename=picture_file,
            seller=current_user
        )
        db.session.add(product)
        db.session.commit()
        flash('商品已成功上架！', 'success')
        return redirect(url_for('home')) # Redirect to seller's product list later
    return render_template('create_product.html', title='上架新商品', form=form)

@app.route('/product/<int:product_id>')
def product_detail(product_id):
    product = Product.query.get_or_404(product_id)
    return render_template('product_detail.html', title=product.name, product=product)

def save_picture(image_file):
    random_hex = uuid.uuid4().hex
    _, f_ext = os.path.splitext(image_file.filename)
    picture_fn = random_hex + f_ext
    picture_path = os.path.join(app.root_path, app.config['UPLOAD_FOLDER'], picture_fn)
    image_file.save(picture_path)
    return picture_fn

@app.route('/register', methods=['GET', 'POST'])
def register():
    if current_user.is_authenticated:
        return redirect(url_for('home'))
    if request.method == 'POST':
        username = request.form.get('username')
        email = request.form.get('email')
        password = request.form.get('password')
        role = request.form.get('role', 'buyer') # Default role is buyer

        user = User.query.filter_by(username=username).first()
        if user:
            flash('Username already exists. Please choose a different one.', 'danger')
            return redirect(url_for('register'))

        user = User.query.filter_by(email=email).first()
        if user:
            flash('Email already registered. Please use a different email.', 'danger')
            return redirect(url_for('register'))

        new_user = User(username=username, email=email, role=role)
        new_user.set_password(password)
        db.session.add(new_user)
        db.session.commit()
        flash('Your account has been created! You are now able to log in.', 'success')
        return redirect(url_for('login'))
    return render_template('register.html')

@app.route('/product/<int:product_id>/update', methods=['GET', 'POST'])
@login_required
def update_product(product_id):
    product = Product.query.get_or_404(product_id)
    if product.seller != current_user:
        flash('您無權編輯此商品', 'danger')
        return redirect(url_for('home')) # 將來可以導向商品列表頁面
    form = ProductForm()
    if form.validate_on_submit():
        if form.image.data:
            # 刪除舊圖片
            if product.image_filename != 'default.jpg':
                old_picture_path = os.path.join(app.root_path, app.config['UPLOAD_FOLDER'], product.image_filename)
                if os.path.exists(old_picture_path):
                    os.remove(old_picture_path)
            picture_file = save_picture(form.image.data)
            product.image_filename = picture_file
        
        product.name = form.name.data
        product.description = form.description.data
        product.specifications = form.specifications.data
        product.condition = form.condition.data
        product.price = form.price.data
        db.session.commit()
        flash('您的商品已更新!', 'success')
        return redirect(url_for('home')) # 將來可以導向商品詳情頁面或賣家商品列表
    elif request.method == 'GET':
        form.name.data = product.name
        form.description.data = product.description
        form.specifications.data = product.specifications
        form.condition.data = product.condition
        form.price.data = product.price
    return render_template('create_product.html', title='編輯商品', form=form, product=product) # 使用同一個模板，但標題不同

@app.route('/product/<int:product_id>/delete', methods=['POST'])
@login_required
def delete_product(product_id):
    product = Product.query.get_or_404(product_id)
    if product.seller != current_user:
        flash('您無權刪除此商品', 'danger')
        return redirect(url_for('home'))
    if product.image_filename != 'default.jpg':
        picture_path = os.path.join(app.root_path, app.config['UPLOAD_FOLDER'], product.image_filename)
        if os.path.exists(picture_path):
            os.remove(picture_path)
    db.session.delete(product)
    db.session.commit()
    flash('您的商品已成功刪除！', 'success')
    return redirect(url_for('home')) # 將來可以導向賣家商品列表

@app.route('/seller_products')
@login_required
def seller_products():
    if current_user.role != 'seller':
        flash('您沒有權限查看此頁面', 'danger')
        return redirect(url_for('home'))
    products = Product.query.filter_by(seller=current_user).all()
    return render_template('seller_products.html', products=products)

@app.route('/login', methods=['GET', 'POST'])
def login():
    if current_user.is_authenticated:
        return redirect(url_for('home'))
    if request.method == 'POST':
        username = request.form.get('username')
        password = request.form.get('password')
        user = User.query.filter_by(username=username).first()
        if user and user.check_password(password):
            login_user(user)
            flash('Login successful!', 'success')
            next_page = request.args.get('next')
            return redirect(next_page or url_for('home'))
        else:
            flash('Login Unsuccessful. Please check username and password', 'danger')
    return render_template('login.html')

@app.route('/logout')
@login_required
def logout():
    logout_user()
    flash('You have been logged out.', 'info')
    return redirect(url_for('home'))

@app.route('/create_order/<int:product_id>', methods=['POST'])
@login_required
def create_order(product_id):
    product = Product.query.get_or_404(product_id)
    if current_user.role != 'buyer' or current_user.id == product.seller.id:
        flash('您無權購買此商品', 'danger')
        return redirect(url_for('home'))

    # 在這裡先不實際創建訂單，而是導向填寫出貨資訊的頁面
    # 可以將 product_id 傳遞給下一個頁面
    return redirect(url_for('shipping_address', product_id=product.id))

@app.route('/shipping_address/<int:product_id>', methods=['GET', 'POST'])
@login_required
def shipping_address(product_id):
    product = Product.query.get_or_404(product_id)
    if current_user.role != 'buyer' or current_user.id == product.seller.id:
        flash('您無權購買此商品', 'danger')
        return redirect(url_for('home'))

    form = ShippingAddressForm()
    # 獲取用戶已儲存的地址
    existing_addresses = ShippingAddress.query.filter_by(user_id=current_user.id).all()

    if form.validate_on_submit():
        # 處理新的地址
        new_address = ShippingAddress(
            user_id=current_user.id,
            recipient_name=form.recipient_name.data,
            phone_number=form.phone_number.data,
            address_line1=form.address_line1.data,
            address_line2=form.address_line2.data,
            city=form.city.data,
            state=form.state.data,
            zip_code=form.zip_code.data,
            country=form.country.data
        )
        db.session.add(new_address)
        db.session.commit()
        flash('新收件地址已儲存！', 'success')
        return redirect(url_for('confirm_order', product_id=product.id, shipping_address_id=new_address.id))

    return render_template('shipping_address.html', title='填寫出貨資訊', form=form, product=product, existing_addresses=existing_addresses)

@app.route('/confirm_order/<int:product_id>/<int:shipping_address_id>', methods=['GET', 'POST'])
@login_required
def confirm_order(product_id, shipping_address_id):
    product = Product.query.get_or_404(product_id)
    shipping_address = ShippingAddress.query.get_or_404(shipping_address_id)

    if current_user.role != 'buyer' or current_user.id == product.seller.id:
        flash('您無權購買此商品', 'danger')
        return redirect(url_for('home'))
    if shipping_address.user_id != current_user.id:
        flash('無權使用此收件地址', 'danger')
        return redirect(url_for('shipping_address', product_id=product.id))

    form = OrderForm()
    if form.validate_on_submit():
        new_order = Order(
            product_id=product.id,
            buyer_id=current_user.id,
            total_price=product.price,
            shipping_method=form.shipping_method.data,
            shipping_address_id=shipping_address.id
        )
        db.session.add(new_order)
        db.session.commit()
        flash('訂單已成功建立！', 'success')
        return redirect(url_for('my_orders')) # Redirect to user's order list

    return render_template('confirm_order.html', title='確認訂單', product=product, shipping_address=shipping_address, form=form)

@app.route('/select_shipping_address/<int:product_id>/<int:shipping_address_id>', methods=['POST'])
@login_required
def select_shipping_address(product_id, shipping_address_id):
    product = Product.query.get_or_404(product_id)
    shipping_address = ShippingAddress.query.get_or_404(shipping_address_id)

    if current_user.role != 'buyer' or current_user.id == product.seller.id:
        flash('您無權購買此商品', 'danger')
        return redirect(url_for('home'))
    if shipping_address.user_id != current_user.id:
        flash('無權使用此收件地址', 'danger')
        return redirect(url_for('shipping_address', product_id=product.id))
    
    return redirect(url_for('confirm_order', product_id=product.id, shipping_address_id=shipping_address.id))

@app.route('/my_orders')
@login_required
def my_orders():
    if current_user.role != 'buyer':
        flash('您沒有權限查看此頁面', 'danger')
        return redirect(url_for('home'))
    orders = Order.query.filter_by(buyer_id=current_user.id).order_by(Order.order_date.desc()).all()
    return render_template('my_orders.html', title='我的訂單', orders=orders)


if __name__ == '__main__':
    # 確保上傳目錄存在
    uploads_dir = os.path.join(app.root_path, app.config['UPLOAD_FOLDER'])
    if not os.path.exists(uploads_dir):
        os.makedirs(uploads_dir)

    with app.app_context():
        db.create_all()

    app.run(debug=False) # Changed to False for production