from flask import Flask, render_template, request, jsonify, redirect, session, url_for
from flask_sqlalchemy import SQLAlchemy
from werkzeug.security import generate_password_hash, check_password_hash
from functools import wraps
import secrets
import string
import qrcode
import io
import base64
from datetime import datetime, timedelta
from sqlalchemy import func
import os
from dotenv import load_dotenv

load_dotenv()

app = Flask(__name__)
app.config['SECRET_KEY'] = os.environ.get('SECRET_KEY', 'shortzlinks-dev-key-change-in-production')
app.config['SQLALCHEMY_DATABASE_URI'] = os.environ.get('SQLALCHEMY_DATABASE_URI', 'sqlite:///shortzlinks.db')
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

db = SQLAlchemy(app)

# ==================== DATABASE MODELS ====================

class User(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(80), unique=True, nullable=False)
    email = db.Column(db.String(120), unique=True, nullable=False)
    password = db.Column(db.String(200), nullable=False)
    brand_name = db.Column(db.String(120), default='Shortzlinks')
    domain = db.Column(db.String(120), default='short.link')
    balance = db.Column(db.Float, default=0.0)
    withdrawn = db.Column(db.Float, default=0.0)
    referral_code = db.Column(db.String(20), unique=True)
    referred_by = db.Column(db.Integer, db.ForeignKey('user.id'))
    total_views = db.Column(db.Integer, default=0)
    total_earnings = db.Column(db.Float, default=0.0)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    
    urls = db.relationship('ShortenedURL', backref='user', lazy=True, cascade='all, delete-orphan')
    referrals = db.relationship('User', remote_side=[referred_by], backref='referrer')

    def set_password(self, password):
        self.password = generate_password_hash(password)

    def check_password(self, password):
        return check_password_hash(self.password, password)

class ShortenedURL(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    short_code = db.Column(db.String(10), unique=True, nullable=False)
    original_url = db.Column(db.String(2000), nullable=False)
    custom_alias = db.Column(db.String(120))
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    clicks = db.Column(db.Integer, default=0)
    earnings = db.Column(db.Float, default=0.0)
    cpm = db.Column(db.Float, default=5.0)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    expires_at = db.Column(db.DateTime, nullable=True)
    is_active = db.Column(db.Boolean, default=True)
    clicks_data = db.relationship('Click', backref='url', lazy=True, cascade='all, delete-orphan')

class Click(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    url_id = db.Column(db.Integer, db.ForeignKey('shortened_url.id'), nullable=False)
    clicked_at = db.Column(db.DateTime, default=datetime.utcnow)
    ip_address = db.Column(db.String(45))
    user_agent = db.Column(db.String(500))
    referrer = db.Column(db.String(500))
    country = db.Column(db.String(2), default='US')

class Withdrawal(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    amount = db.Column(db.Float, nullable=False)
    status = db.Column(db.String(20), default='pending')
    method = db.Column(db.String(50))
    requested_at = db.Column(db.DateTime, default=datetime.utcnow)
    processed_at = db.Column(db.DateTime, nullable=True)

# ==================== HELPER FUNCTIONS ====================

def generate_short_code(length=6):
    characters = string.ascii_letters + string.digits
    return ''.join(secrets.choice(characters) for _ in range(length))

def generate_referral_code():
    return secrets.token_urlsafe(16)[:12]

def generate_qr_code(url):
    qr = qrcode.QRCode(version=1, box_size=10, border=5)
    qr.add_data(url)
    qr.make(fit=True)
    img = qr.make_image(fill_color="black", back_color="white")
    
    buf = io.BytesIO()
    img.save(buf, format='PNG')
    buf.seek(0)
    return base64.b64encode(buf.getvalue()).decode()

def get_country_from_ip(ip):
    return 'US'

def calculate_earnings(clicks, cpm=5.0):
    return (clicks / 1000) * cpm

def login_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if 'user_id' not in session:
            return redirect(url_for('login'))
        return f(*args, **kwargs)
    return decorated_function

# ==================== AUTHENTICATION ==================== 

@app.route('/register', methods=['GET', 'POST'])
def register():
    if request.method == 'POST':
        data = request.get_json()
        username = data.get('username')
        email = data.get('email')
        password = data.get('password')
        
        if not username or not email or not password:
            return jsonify({'error': 'All fields required'}), 400
        
        if User.query.filter_by(username=username).first():
            return jsonify({'error': 'Username already exists'}), 400
        
        if User.query.filter_by(email=email).first():
            return jsonify({'error': 'Email already exists'}), 400
        
        user = User(username=username, email=email, referral_code=generate_referral_code())
        user.set_password(password)
        
        db.session.add(user)
        db.session.commit()
        
        return jsonify({'success': 'Registration successful'}), 201
    
    return render_template('register.html')

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        data = request.get_json()
        username = data.get('username')
        password = data.get('password')
        
        user = User.query.filter_by(username=username).first()
        
        if not user or not user.check_password(password):
            return jsonify({'error': 'Invalid credentials'}), 401
        
        session['user_id'] = user.id
        session['username'] = user.username
        
        return jsonify({'success': 'Login successful'}), 200
    
    return render_template('login.html')

@app.route('/logout')
def logout():
    session.clear()
    return redirect(url_for('index'))

# ==================== MAIN ROUTES ====================

@app.route('/')
def index():
    if 'user_id' in session:
        return redirect(url_for('dashboard'))
    return render_template('index.html')

@app.route('/dashboard')
@login_required
def dashboard():
    user = User.query.get(session['user_id'])
    urls = ShortenedURL.query.filter_by(user_id=session['user_id']).all()
    
    total_clicks = sum(url.clicks for url in urls)
    total_earnings = sum(url.earnings for url in urls)
    avg_cpm = total_earnings / (total_clicks / 1000) if total_clicks > 0 else 0
    
    today_start = datetime.utcnow().replace(hour=0, minute=0, second=0, microsecond=0)
    today_clicks = db.session.query(func.count(Click.id)).filter(
        Click.clicked_at >= today_start,
        Click.url_id.in_([u.id for u in urls])
    ).scalar() or 0
    today_earnings = calculate_earnings(today_clicks, 5.0)
    
    month_start = datetime.utcnow().replace(day=1, hour=0, minute=0, second=0, microsecond=0)
    month_clicks = db.session.query(func.count(Click.id)).filter(
        Click.clicked_at >= month_start,
        Click.url_id.in_([u.id for u in urls])
    ).scalar() or 0
    month_earnings = calculate_earnings(month_clicks, 5.0)
    
    return render_template('dashboard_enhanced.html',
                         user=user,
                         urls=urls,
                         total_clicks=total_clicks,
                         total_earnings=total_earnings,
                         avg_cpm=round(avg_cpm, 4),
                         total_links=len(urls),
                         today_clicks=today_clicks,
                         today_earnings=today_earnings,
                         month_clicks=month_clicks,
                         month_earnings=month_earnings)

@app.route('/manage-links')
@login_required
def manage_links():
    user = User.query.get(session['user_id'])
    urls = ShortenedURL.query.filter_by(user_id=session['user_id']).order_by(ShortenedURL.created_at.desc()).all()
    return render_template('manage_links.html', user=user, urls=urls)

@app.route('/referrals')
@login_required
def referrals():
    user = User.query.get(session['user_id'])
    refs = User.query.filter_by(referred_by=user.id).all()
    return render_template('referrals_page.html', user=user, referrals=refs)

@app.route('/withdrawal')
@login_required
def withdrawal():
    user = User.query.get(session['user_id'])
    withdrawals = Withdrawal.query.filter_by(user_id=user.id).order_by(Withdrawal.requested_at.desc()).all()
    return render_template('withdrawal_page.html', user=user, withdrawals=withdrawals, min_withdrawal=5.0)

@app.route('/settings')
@login_required
def settings():
    user = User.query.get(session['user_id'])
    return render_template('settings.html', user=user)

# ==================== API ROUTES ====================

@app.route('/api/shorten', methods=['POST'])
@login_required
def shorten_url():
    data = request.get_json()
    original_url = data.get('url')
    custom_alias = data.get('custom_alias')
    
    if not original_url:
        return jsonify({'error': 'URL required'}), 400
    
    if not original_url.startswith(('http://', 'https://')):
        original_url = 'https://' + original_url
    
    if custom_alias:
        if ShortenedURL.query.filter_by(custom_alias=custom_alias).first():
            return jsonify({'error': 'Custom alias already taken'}), 400
        short_code = custom_alias
    else:
        while True:
            short_code = generate_short_code()
            if not ShortenedURL.query.filter_by(short_code=short_code).first():
                break
    
    shortened = ShortenedURL(
        short_code=short_code,
        original_url=original_url,
        custom_alias=custom_alias,
        user_id=session['user_id'],
        cpm=5.0
    )
    
    db.session.add(shortened)
    db.session.commit()
    
    short_url = request.host_url.rstrip('/') + '/' + short_code
    qr_code = generate_qr_code(short_url)
    
    return jsonify({
        'success': True,
        'short_code': short_code,
        'short_url': short_url,
        'original_url': original_url,
        'qr_code': qr_code
    }), 201

@app.route('/api/urls')
@login_required
def get_urls():
    urls = ShortenedURL.query.filter_by(user_id=session['user_id']).all()
    return jsonify([{
        'id': url.id,
        'short_code': url.short_code,
        'original_url': url.original_url,
        'clicks': url.clicks,
        'earnings': round(url.earnings, 4),
        'created_at': url.created_at.strftime('%Y-%m-%d'),
        'is_active': url.is_active
    } for url in urls])

@app.route('/api/url/<int:url_id>/stats')
@login_required
def get_url_stats(url_id):
    shortened = ShortenedURL.query.get(url_id)
    
    if not shortened or shortened.user_id != session['user_id']:
        return jsonify({'error': 'Not found'}), 404
    
    seven_days_ago = datetime.utcnow() - timedelta(days=7)
    clicks_per_day = db.session.query(
        func.date(Click.clicked_at).label('date'),
        func.count(Click.id).label('count')
    ).filter(
        Click.url_id == url_id,
        Click.clicked_at >= seven_days_ago
    ).group_by(func.date(Click.clicked_at)).all()
    
    return jsonify({
        'id': shortened.id,
        'short_code': shortened.short_code,
        'original_url': shortened.original_url,
        'clicks': shortened.clicks,
        'earnings': round(shortened.earnings, 4),
        'cpm': shortened.cpm,
        'created_at': shortened.created_at.strftime('%Y-%m-%d'),
        'clicks_per_day': [{'date': str(d[0]), 'count': d[1]} for d in clicks_per_day]
    })

@app.route('/api/url/<int:url_id>/delete', methods=['DELETE'])
@login_required
def delete_url(url_id):
    shortened = ShortenedURL.query.get(url_id)
    
    if not shortened or shortened.user_id != session['user_id']:
        return jsonify({'error': 'Not found'}), 404
    
    db.session.delete(shortened)
    db.session.commit()
    
    return jsonify({'success': True})

@app.route('/api/url/<int:url_id>/toggle', methods=['POST'])
@login_required
def toggle_url(url_id):
    shortened = ShortenedURL.query.get(url_id)
    
    if not shortened or shortened.user_id != session['user_id']:
        return jsonify({'error': 'Not found'}), 404
    
    shortened.is_active = not shortened.is_active
    db.session.commit()
    
    return jsonify({'success': True, 'is_active': shortened.is_active})

@app.route('/api/withdrawal/request', methods=['POST'])
@login_required
def request_withdrawal():
    data = request.get_json()
    amount = data.get('amount')
    method = data.get('method')
    
    user = User.query.get(session['user_id'])
    
    if not amount or amount < 5.0:
        return jsonify({'error': 'Minimum withdrawal is $5'}), 400
    
    if amount > user.balance:
        return jsonify({'error': 'Insufficient balance'}), 400
    
    withdrawal = Withdrawal(
        user_id=user.id,
        amount=amount,
        method=method,
        status='pending'
    )
    
    user.balance -= amount
    
    db.session.add(withdrawal)
    db.session.commit()
    
    return jsonify({'success': True, 'message': 'Withdrawal requested'})

@app.route('/api/settings/update', methods=['POST'])
@login_required
def update_settings():
    data = request.get_json()
    user = User.query.get(session['user_id'])
    
    if 'brand_name' in data:
        user.brand_name = data['brand_name']
    if 'domain' in data:
        user.domain = data['domain']
    
    db.session.commit()
    
    return jsonify({'success': True})

# ==================== REDIRECT ROUTE ====================

@app.route('/<short_code>')
def redirect_url(short_code):
    shortened = ShortenedURL.query.filter_by(short_code=short_code).first()
    
    if not shortened or not shortened.is_active:
        return render_template('404.html'), 404
    
    if shortened.expires_at and datetime.utcnow() > shortened.expires_at:
        return render_template('404.html'), 404
    
    country = get_country_from_ip(request.remote_addr)
    
    click = Click(
        url_id=shortened.id,
        ip_address=request.remote_addr,
        user_agent=request.user_agent.string,
        referrer=request.referrer,
        country=country
    )
    
    shortened.clicks += 1
    shortened.earnings = calculate_earnings(shortened.clicks, shortened.cpm)
    
    user = shortened.user
    user.total_views += 1
    user.total_earnings += (shortened.cpm / 1000)
    user.balance += (shortened.cpm / 1000)
    
    db.session.add(click)
    db.session.commit()
    
    return redirect(shortened.original_url)

# ==================== ERROR HANDLERS ====================

@app.errorhandler(404)
def not_found(e):
    return render_template('404.html'), 404

@app.errorhandler(500)
def server_error(e):
    return jsonify({'error': 'Server error'}), 500

# ==================== INITIALIZE ====================

def init_db():
    with app.app_context():
        db.create_all()
        print("✅ Database initialized!")

if __name__ == '__main__':
    init_db()
    app.run(debug=False, host='0.0.0.0', port=5000)