from flask import Flask, render_template, request, redirect, url_for, flash
from flask_login import LoginManager, login_user, login_required, logout_user, current_user
from werkzeug.security import generate_password_hash, check_password_hash
import stripe, os
from config import Config
from models import db, User, Product, CartItem, Order, OrderItem

app = Flask(__name__)
app.config.from_object(Config)
db.init_app(app)

login_manager = LoginManager(app)
login_manager.login_view = 'login'
stripe.api_key = app.config.get('STRIPE_SECRET_KEY','')

@login_manager.user_loader
def load_user(user_id):
    return User.query.get(int(user_id))

@app.context_processor
def inject_globals():
    return {'STRIPE_PUBLISHABLE_KEY': app.config.get('STRIPE_PUBLISHABLE_KEY',''), 'current_user': current_user}

@app.route('/')
def index():
    q = request.args.get('q','').strip()
    if q:
        products = Product.query.filter((Product.title.ilike(f'%{q}%')) | (Product.description.ilike(f'%{q}%'))).all()
    else:
        products = Product.query.all()
    # pick first 3 as featured
    featured = products[:3]
    return render_template('index.html', products=products, featured=featured, query=q)

@app.route('/product/<int:product_id>')
def product_detail(product_id):
    p = Product.query.get(product_id)
    if not p:
        flash('Product not found','error'); return redirect(url_for('index'))
    return render_template('product_detail.html', product=p)

@app.route('/register', methods=['GET','POST'])
def register():
    if request.method == 'POST':
        name = request.form.get('name','').strip(); email = request.form.get('email','').lower().strip(); password = request.form.get('password','')
        if not (name and email and password):
            flash('All fields required','error'); return redirect(url_for('register'))
        if User.query.filter_by(email=email).first():
            flash('Email already registered','error'); return redirect(url_for('register'))
        u = User(name=name, email=email, password_hash=generate_password_hash(password))
        db.session.add(u); db.session.commit()
        flash('Registered. Please log in.','success'); return redirect(url_for('login'))
    return render_template('register.html')

@app.route('/login', methods=['GET','POST'])
def login():
    if request.method == 'POST':
        email = request.form.get('email','').lower().strip(); password = request.form.get('password','')
        u = User.query.filter_by(email=email).first()
        if u and check_password_hash(u.password_hash, password):
            login_user(u); flash('Welcome back','success'); return redirect(url_for('index'))
        flash('Invalid credentials','error')
    return render_template('login.html')

@app.route('/logout')
@login_required
def logout():
    logout_user(); flash('Logged out','info'); return redirect(url_for('index'))

@app.route('/cart')
@login_required
def cart():
    items = CartItem.query.filter_by(user_id=current_user.id).all()
    total = sum(i.quantity * i.product.price for i in items)
    return render_template('cart.html', items=items, total=total)

@app.route('/cart/add/<int:product_id>', methods=['POST'])
@login_required
def add_to_cart(product_id):
    qty = int(request.form.get('quantity',1))
    if qty < 1: qty = 1
    p = Product.query.get(product_id)
    if not p:
        flash('Product not found','error'); return redirect(url_for('index'))
    item = CartItem.query.filter_by(user_id=current_user.id, product_id=product_id).first()
    if item:
        item.quantity += qty
    else:
        item = CartItem(user_id=current_user.id, product_id=product_id, quantity=qty)
        db.session.add(item)
    db.session.commit()
    flash('Added to cart','success')
    return redirect(url_for('cart'))

@app.route('/cart/update/<int:item_id>', methods=['POST'])
@login_required
def update_cart(item_id):
    qty = int(request.form.get('quantity',1))
    item = CartItem.query.get(item_id)
    if item and item.user_id == current_user.id:
        if qty <= 0:
            db.session.delete(item)
        else:
            item.quantity = qty
        db.session.commit()
    return redirect(url_for('cart'))

@app.route('/checkout')
@login_required
def checkout():
    cart_items = CartItem.query.filter_by(user_id=current_user.id).all()

    if not cart_items:
        flash("Your cart is empty", "warning")
        return redirect(url_for('cart'))

    line_items = []

    for it in cart_items:
        line_items.append({
            "price_data": {
                "currency": "inr",   # ✅ REQUIRED
                "product_data": {
                    "name": it.product.title
                },
                "unit_amount": int(it.product.price * 100)
            },
            "quantity": int(it.quantity)
        })

    try:
        session = stripe.checkout.Session.create(
            payment_method_types=["card"],
            mode="payment",
            line_items=line_items,
            success_url=url_for("payment_success", _external=True),
            cancel_url=url_for("cart", _external=True)
        )

        return redirect(session.url, code=303)

    except Exception as e:
        print("Stripe error:", e)
        flash("Payment session error. Check Stripe keys and internet connection.", "error")
        return redirect(url_for("cart"))

@app.route('/payment-success')
@login_required
def payment_success():
    items = CartItem.query.filter_by(user_id=current_user.id).all()
    if not items:
        flash('No items to place order.','info'); return redirect(url_for('index'))
    total = sum(i.quantity * i.product.price for i in items)
    order = Order(user_id=current_user.id, status='paid', total_amount=total)
    db.session.add(order); db.session.flush()
    for it in items:
        oi = OrderItem(order_id=order.id, product_id=it.product_id, quantity=it.quantity, unit_price=it.product.price)
        db.session.add(oi)
        db.session.delete(it)
    db.session.commit()
    flash('Payment successful! Order placed.','success')
    return redirect(url_for('orders'))

@app.route('/orders')
@login_required
def orders():
    user_orders = Order.query.filter_by(user_id=current_user.id).all()
    return render_template('orders.html', orders=user_orders)

def seed_if_needed():
    from models import Product, User
    # Create default admin and products only if no products exist
    if Product.query.count() == 0:
        admin_email = 'admin@petmart.com'
        if not User.query.filter_by(email=admin_email).first():
            admin = User(name='Admin', email=admin_email, password_hash=generate_password_hash('admin123'))
            db.session.add(admin)
        products = [
            Product(title='Organic Dog Food', description='Grain-free, premium chicken recipe.', price=1299.00, image='/static/images/dog_food.jpg'),
            Product(title='Cat Scratching Post', description='Sisal rope post to save your sofa.', price=899.00, image='/static/images/cat_toy.jpg'),
            Product(title='Dog Leash', description='Strong nylon leash for daily walks.', price=499.00, image='/static/images/dog_leash.jpg'),
            Product(title='Pet Bed', description='Cozy memory-foam pet bed.', price=2499.00, image='/static/images/pet_bed.jpg'),
            Product(title='Grooming Kit', description='Brush, nail clippers, comb.', price=599.00, image='/static/images/pet_accessory.jpg'),
            Product(title='Premium Salmon Dog Food', description='High-protein salmon recipe for active dogs.', price=1899.00, image='/static/images/premium_dog_food.jpg'),
            Product(title='Cat Scratcher Lounge', description='Comfortable lounge with scratching surface.', price=1299.00, image='/static/images/scratching_post.jpg'),
            Product(title='Bird Cage - Medium', description='Durable cage for small to medium birds.', price=3499.00, image='/static/images/bird_cage.jpg'),
            Product(title='Fish Tank Starter Kit', description='Tank + filter + decor, perfect for beginners.', price=3999.00, image='/static/images/fish_tank.jpg'),
            Product(title='Rabbit Hutch', description='Outdoor hutch for rabbits and small pets.', price=4599.00, image='/static/images/rabbit_hutch.jpg'),
        ]
        db.session.add_all(products)
        db.session.commit()
        print('Seeded default admin + products.')

if __name__ == '__main__':
    # create DB and seed if needed, then run
    with app.app_context():
        db.create_all()
        try:
            seed_if_needed()
        except Exception as e:
            print('Seeding error:', e)
    app.run(debug=True)
    # ================= ADMIN DASHBOARD =================

@app.route("/admin")
@login_required
def admin_dashboard():
    if not current_user.is_admin:
        return "❌ Access Denied - Admin Only"

    users = User.query.all()
    products = Product.query.all()
    carts = CartItem.query.all()
    orders = Order.query.all()

    return render_template("admin_dashboard.html", users=users, products=products, carts=carts, orders=orders)
