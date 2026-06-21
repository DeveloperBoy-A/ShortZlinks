from flask import Flask, render_template, request, jsonify, redirect, session, url_for
from mongoengine import connect, Document, StringField, IntField, FloatField, DateTimeField, BooleanField, ReferenceField, ListField, DictField
from werkzeug.security import generate_password_hash, check_password_hash
from functools import wraps
import secrets
import string
import qrcode
import io
import base64
from datetime import datetime, timedelta
from functools import wraps
import requests
import os
from dotenv import load_dotenv
from apscheduler.schedulers.background import BackgroundScheduler
import atexit
import json

load_dotenv()

app = Flask(__name__)
app.config['SECRET_KEY'] = os.environ.get('SECRET_KEY', 'shortzlinks-dev-key-change-in-production')
app.config['MONGODB_URI'] = os.environ.get('MONGODB_URI', 'mongodb://localhost:27017/shortzlinks')

# Connect to MongoDB
try:
    connect(host=os.environ.get('MONGODB_URI', 'mongodb://localhost:27017/shortzlinks'))
    print("✅ Connected to MongoDB!")
except Exception as e:
    print(f"❌ MongoDB Connection Error: {e}")

# ==================== DATABASE MODELS (MongoDB) ====================

class User(Document):
    username = StringField(unique=True, required=True)
    email = StringField(unique=True, required=True)
    password = StringField(required=True)
    api_key = StringField(unique=True)
    brand_name = StringField(default='Shortzlinks')
    domain = StringField(default='short.link')
    balance = FloatField(default=0.0)
    withdrawn = FloatField(default=0.0)
    referral_code = StringField(unique=True)
    referred_by = ReferenceField('self', null=True)
    total_views = IntField(default=0)
    total_earnings = FloatField(default=0.0)
    commission_rate = FloatField(default=25.0)  # 25% commission
    created_at = DateTimeField(default=datetime.utcnow)
    updated_at = DateTimeField(default=datetime.utcnow)
    
    meta = {
        'collection': 'users',
        'indexes': ['username', 'email', 'api_key']
    }

    def set_password(self, password):
        self.password = generate_password_hash(password)

    def check_password(self, password):
        return check_password_hash(self.password, password)

    def generate_api_key(self):
        self.api_key = secrets.token_urlsafe(32)
        return self.api_key

class ShortenedURL(Document):
    short_code = StringField(unique=True, required=True)
    original_url = StringField(required=True)
    custom_alias = StringField(null=True)
    user = ReferenceField(User, required=True)
    clicks = IntField(default=0)
    earnings = FloatField(default=0.0)
    cpm_rate = FloatField(default=5.0)
    country_earnings = DictField()  # {'US': 5.0, 'IN': 0.5, ...}
    created_at = DateTimeField(default=datetime.utcnow)
    expires_at = DateTimeField(null=True)
    is_active = BooleanField(default=True)
    
    meta = {
        'collection': 'shortened_urls',
        'indexes': ['short_code', 'user', 'created_at']
    }

class Click(Document):
    url = ReferenceField(ShortenedURL, required=True)
    clicked_at = DateTimeField(default=datetime.utcnow)
    ip_address = StringField()
    user_agent = StringField()
    referrer = StringField()
    country_code = StringField(default='US')
    country_name = StringField(default='United States')
    earnings = FloatField(default=0.0)
    
    meta = {
        'collection': 'clicks',
        'indexes': ['url', 'country_code', 'clicked_at']
    }

class Withdrawal(Document):
    user = ReferenceField(User, required=True)
    amount = FloatField(required=True)
    status = StringField(default='pending')  # pending, approved, rejected
    method = StringField()  # paypal, bank, stripe, crypto
    requested_at = DateTimeField(default=datetime.utcnow)
    processed_at = DateTimeField(null=True)
    
    meta = {
        'collection': 'withdrawals',
        'indexes': ['user', 'status']
    }

class AdRate(Document):
    country_code = StringField(unique=True, required=True)
    country_name = StringField()
    rate = FloatField()  # CPM rate
    network = StringField()  # adsterra, monetag, etc
    updated_at = DateTimeField(default=datetime.utcnow)
    
    meta = {
        'collection': 'ad_rates',
        'indexes': ['country_code']
    }

# ==================== AD NETWORK INTEGRATION ====================

def fetch_adsterra_rates():
    """Fetch CPM rates from Adsterra"""
    try:
        response = requests.get('https://api.adsterra.com/rates', timeout=10)
        if response.status_code == 200:
            rates = response.json()
            for country_code, rate in rates.items():
                AdRate.objects(country_code=country_code).update_one(
                    set__rate=rate,
                    set__network='adsterra',
                    set__updated_at=datetime.utcnow(),
                    upsert=True
                )
            print("✅ Adsterra rates updated")
            return True
    except Exception as e:
        print(f"❌ Adsterra Error: {e}")
    return False

def fetch_monetag_rates():
    """Fetch CPM rates from Monetag"""
    try:
        response = requests.get('https://api.monetag.com/rates', timeout=10)
        if response.status_code == 200:
            rates = response.json()
            for country_code, rate in rates.items():
                AdRate.objects(country_code=country_code).update_one(
                    set__rate=rate,
                    set__network='monetag',
                    set__updated_at=datetime.utcnow(),
                    upsert=True
                )
            print("✅ Monetag rates updated")
            return True
    except Exception as e:
        print(f"❌ Monetag Error: {e}")
    return False

def update_ad_rates():
    """Auto-update ad rates from networks"""
    print("🔄 Updating ad rates...")
    fetch_adsterra_rates()
    fetch_monetag_rates()

def get_country_cpm_rate(country_code='US'):
    """Get CPM rate for specific country"""
    ad_rate = AdRate.objects(country_code=country_code).first()
    return ad_rate.rate if ad_rate else 5.0  # Default $5 CPM

# ==================== SCHEDULER ====================

scheduler = BackgroundScheduler()
scheduler.add_job(
    func=update_ad_rates,
    trigger="cron",
    hour=0,
    minute=0,
    id='update_ad_rates',
    name='Update ad rates daily',
    replace_existing=True
)
scheduler.start()

atexit.register(lambda: scheduler.shutdown())

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
    """Get country code from IP using free API"""
    try:
        response = requests.get(f'https://ipapi.co/{ip}/json/', timeout=5)
        if response.status_code == 200:
            data = response.json()
            return data.get('country_code', 'US'), data.get('country_name', 'United States')
    except:
        pass
    return 'US', 'United States'

def calculate_user_earnings(base_cpm, user_commission=25):
    """Calculate user earnings after commission"""
    return base_cpm * (1 - user_commission / 100)

def login_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if 'user_id' not in session:
            return redirect(url_for('login'))
        return f(*args, **kwargs)
    return decorated_function

def api_key_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        api_key = request.headers.get('X-API-Key')
        if not api_key:
            return jsonify({'error': 'API key required'}), 401
        
        user = User.objects(api_key=api_key).first()
        if not user:
            return jsonify({'error': 'Invalid API key'}), 401
        
        request.user = user
        return f(*args, **kwargs)
    return decorated_function

# ==================== AUTHENTICATION ROUTES ====================

@app.route('/register', methods=['GET', 'POST'])
def register():
    if request.method == 'POST':
        data = request.get_json()
        username = data.get('username')
        email = data.get('email')
        password = data.get('password')
        
        if not username or not email or not password:
            return jsonify({'error': 'All fields required'}), 400
        
        if User.objects(username=username):
            return jsonify({'error': 'Username already exists'}), 400
        
        if User.objects(email=email):
            return jsonify({'error': 'Email already exists'}), 400
        
        user = User(
            username=username,
            email=email,
            referral_code=generate_referral_code()
        )
        user.set_password(password)
        user.generate_api_key()
        user.save()
        
        return jsonify({'success': 'Registration successful'}), 201
    
    return render_template('register.html')

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        data = request.get_json()
        username = data.get('username')
        password = data.get('password')
        
        user = User.objects(username=username).first()
        
        if not user or not user.check_password(password):
            return jsonify({'error': 'Invalid credentials'}), 401
        
        session['user_id'] = str(user.id)
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
    user = User.objects(id=session['user_id']).first()
    urls = ShortenedURL.objects(user=user).all()
    
    total_clicks = sum(url.clicks for url in urls)
    total_earnings = sum(url.earnings for url in urls)
    avg_cpm = total_earnings / (total_clicks / 1000) if total_clicks > 0 else 0
    
    today_start = datetime.utcnow().replace(hour=0, minute=0, second=0, microsecond=0)
    today_clicks = Click.objects(url__in=urls, clicked_at__gte=today_start).count()
    today_earnings = sum(Click.objects(url__in=urls, clicked_at__gte=today_start).scalar('earnings'))
    
    month_start = datetime.utcnow().replace(day=1, hour=0, minute=0, second=0, microsecond=0)
    month_clicks = Click.objects(url__in=urls, clicked_at__gte=month_start).count()
    month_earnings = sum(Click.objects(url__in=urls, clicked_at__gte=month_start).scalar('earnings'))
    
    return render_template('dashboard_enhanced.html',
                         user=user,
                         urls=urls,
                         total_clicks=total_clicks,
                         total_earnings=round(total_earnings, 2),
                         avg_cpm=round(avg_cpm, 4),
                         total_links=len(urls),
                         today_clicks=today_clicks,
                         today_earnings=round(today_earnings, 2),
                         month_clicks=month_clicks,
                         month_earnings=round(month_earnings, 2))

@app.route('/manage-links')
@login_required
def manage_links():
    user = User.objects(id=session['user_id']).first()
    urls = ShortenedURL.objects(user=user).order_by('-created_at').all()
    return render_template('manage_links.html', user=user, urls=urls)

@app.route('/referrals')
@login_required
def referrals():
    user = User.objects(id=session['user_id']).first()
    refs = User.objects(referred_by=user).all()
    return render_template('referrals_page.html', user=user, referrals=refs)

@app.route('/withdrawal')
@login_required
def withdrawal():
    user = User.objects(id=session['user_id']).first()
    withdrawals = Withdrawal.objects(user=user).order_by('-requested_at').all()
    return render_template('withdrawal_page.html', user=user, withdrawals=withdrawals, min_withdrawal=5.0)

@app.route('/settings')
@login_required
def settings():
    user = User.objects(id=session['user_id']).first()
    return render_template('settings.html', user=user)

@app.route('/analytics')
@login_required
def analytics():
    user = User.objects(id=session['user_id']).first()
    urls = ShortenedURL.objects(user=user).all()
    
    # Country-wise stats
    country_stats = {}
    for url in urls:
        clicks = Click.objects(url=url).all()
        for click in clicks:
            country = click.country_code
            if country not in country_stats:
                country_stats[country] = {
                    'clicks': 0,
                    'earnings': 0.0,
                    'name': click.country_name
                }
            country_stats[country]['clicks'] += 1
            country_stats[country]['earnings'] += click.earnings
    
    return render_template('analytics.html', user=user, country_stats=country_stats)

# ==================== AD WAIT PAGE ====================

@app.route('/ad/<short_code>')
def ad_wait_page(short_code):
    """Show ad wait page before redirect"""
    shortened = ShortenedURL.objects(short_code=short_code).first()
    
    if not shortened or not shortened.is_active:
        return render_template('404.html'), 404
    
    if shortened.expires_at and datetime.utcnow() > shortened.expires_at:
        return render_template('404.html'), 404
    
    return render_template('ad_wait.html', short_code=short_code, title=shortened.original_url[:50])

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
        if ShortenedURL.objects(custom_alias=custom_alias):
            return jsonify({'error': 'Custom alias already taken'}), 400
        short_code = custom_alias
    else:
        while True:
            short_code = generate_short_code()
            if not ShortenedURL.objects(short_code=short_code):
                break
    
    user = User.objects(id=session['user_id']).first()
    
    shortened = ShortenedURL(
        short_code=short_code,
        original_url=original_url,
        custom_alias=custom_alias,
        user=user,
        cpm_rate=5.0
    )
    shortened.save()
    
    short_url = request.host_url.rstrip('/') + 'ad/' + short_code
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
    user = User.objects(id=session['user_id']).first()
    urls = ShortenedURL.objects(user=user).all()
    return jsonify([{
        'id': str(url.id),
        'short_code': url.short_code,
        'original_url': url.original_url,
        'clicks': url.clicks,
        'earnings': round(url.earnings, 4),
        'created_at': url.created_at.strftime('%Y-%m-%d'),
        'is_active': url.is_active
    } for url in urls])

@app.route('/api/url/<url_id>/stats')
@login_required
def get_url_stats(url_id):
    try:
        from bson.objectid import ObjectId
        shortened = ShortenedURL.objects(id=ObjectId(url_id)).first()
    except:
        return jsonify({'error': 'Invalid URL ID'}), 400
    
    user = User.objects(id=session['user_id']).first()
    if not shortened or shortened.user != user:
        return jsonify({'error': 'Not found'}), 404
    
    seven_days_ago = datetime.utcnow() - timedelta(days=7)
    clicks = Click.objects(url=shortened, clicked_at__gte=seven_days_ago).all()
    
    clicks_per_day = {}
    for click in clicks:
        date_key = click.clicked_at.strftime('%Y-%m-%d')
        if date_key not in clicks_per_day:
            clicks_per_day[date_key] = 0
        clicks_per_day[date_key] += 1
    
    return jsonify({
        'id': str(shortened.id),
        'short_code': shortened.short_code,
        'original_url': shortened.original_url,
        'clicks': shortened.clicks,
        'earnings': round(shortened.earnings, 4),
        'cpm': shortened.cpm_rate,
        'created_at': shortened.created_at.strftime('%Y-%m-%d'),
        'clicks_per_day': [{'date': date, 'count': count} for date, count in clicks_per_day.items()]
    })

@app.route('/api/url/<url_id>/delete', methods=['DELETE'])
@login_required
def delete_url(url_id):
    try:
        from bson.objectid import ObjectId
        shortened = ShortenedURL.objects(id=ObjectId(url_id)).first()
    except:
        return jsonify({'error': 'Invalid URL ID'}), 400
    
    user = User.objects(id=session['user_id']).first()
    if not shortened or shortened.user != user:
        return jsonify({'error': 'Not found'}), 404
    
    shortened.delete()
    return jsonify({'success': True})

@app.route('/api/url/<url_id>/toggle', methods=['POST'])
@login_required
def toggle_url(url_id):
    try:
        from bson.objectid import ObjectId
        shortened = ShortenedURL.objects(id=ObjectId(url_id)).first()
    except:
        return jsonify({'error': 'Invalid URL ID'}), 400
    
    user = User.objects(id=session['user_id']).first()
    if not shortened or shortened.user != user:
        return jsonify({'error': 'Not found'}), 404
    
    shortened.is_active = not shortened.is_active
    shortened.save()
    
    return jsonify({'success': True, 'is_active': shortened.is_active})

@app.route('/api/withdrawal/request', methods=['POST'])
@login_required
def request_withdrawal():
    data = request.get_json()
    amount = data.get('amount')
    method = data.get('method')
    
    user = User.objects(id=session['user_id']).first()
    
    if not amount or amount < 5.0:
        return jsonify({'error': 'Minimum withdrawal is $5'}), 400
    
    if amount > user.balance:
        return jsonify({'error': 'Insufficient balance'}), 400
    
    withdrawal = Withdrawal(
        user=user,
        amount=amount,
        method=method,
        status='pending'
    )
    withdrawal.save()
    
    user.balance -= amount
    user.withdrawn += amount
    user.save()
    
    return jsonify({'success': True, 'message': 'Withdrawal requested'})

@app.route('/api/settings/update', methods=['POST'])
@login_required
def update_settings():
    data = request.get_json()
    user = User.objects(id=session['user_id']).first()
    
    if 'brand_name' in data:
        user.brand_name = data['brand_name']
    if 'domain' in data:
        user.domain = data['domain']
    if 'commission_rate' in data:
        user.commission_rate = float(data['commission_rate'])
    
    user.updated_at = datetime.utcnow()
    user.save()
    
    return jsonify({'success': True})

# ==================== DEVELOPER TOOLS API ====================

@app.route('/api/dev/stats', methods=['GET'])
@api_key_required
def dev_stats():
    """Developer API - Get account stats"""
    user = request.user
    urls = ShortenedURL.objects(user=user).all()
    
    total_clicks = sum(url.clicks for url in urls)
    total_earnings = sum(url.earnings for url in urls)
    
    return jsonify({
        'username': user.username,
        'total_links': len(urls),
        'total_clicks': total_clicks,
        'total_earnings': round(total_earnings, 2),
        'balance': round(user.balance, 2),
        'api_key': user.api_key[:10] + '****'
    })

@app.route('/api/dev/create', methods=['POST'])
@api_key_required
def dev_create_link():
    """Developer API - Create shortened link"""
    data = request.get_json()
    url = data.get('url')
    
    if not url:
        return jsonify({'error': 'URL required'}), 400
    
    if not url.startswith(('http://', 'https://')):
        url = 'https://' + url
    
    while True:
        short_code = generate_short_code()
        if not ShortenedURL.objects(short_code=short_code):
            break
    
    shortened = ShortenedURL(
        short_code=short_code,
        original_url=url,
        user=request.user
    )
    shortened.save()
    
    short_url = request.host_url.rstrip('/') + 'ad/' + short_code
    
    return jsonify({
        'success': True,
        'short_code': short_code,
        'short_url': short_url,
        'original_url': url
    }), 201

@app.route('/api/dev/links', methods=['GET'])
@api_key_required
def dev_get_links():
    """Developer API - Get all links"""
    user = request.user
    urls = ShortenedURL.objects(user=user).all()
    
    return jsonify({
        'total': len(urls),
        'links': [{
            'short_code': url.short_code,
            'original_url': url.original_url,
            'clicks': url.clicks,
            'earnings': round(url.earnings, 2),
            'created_at': url.created_at.isoformat()
        } for url in urls]
    })

@app.route('/api/dev/rates', methods=['GET'])
def dev_get_rates():
    """Get current CPM rates by country (Public API)"""
    rates = AdRate.objects.all()
    
    return jsonify({
        'total_countries': len(rates),
        'rates': [{
            'country_code': rate.country_code,
            'country_name': rate.country_name,
            'cpm': rate.rate,
            'network': rate.network,
            'updated_at': rate.updated_at.isoformat()
        } for rate in rates]
    })

@app.route('/api/redirect/<short_code>')
def api_redirect(short_code):
    """API endpoint for redirecting"""
    shortened = ShortenedURL.objects(short_code=short_code).first()
    
    if not shortened or not shortened.is_active:
        return jsonify({'error': 'Not found'}), 404
    
    country_code, country_name = get_country_from_ip(request.remote_addr)
    cpm_rate = get_country_cpm_rate(country_code)
    
    user = shortened.user
    user_earnings = calculate_user_earnings(cpm_rate, user.commission_rate)
    
    click = Click(
        url=shortened,
        ip_address=request.remote_addr,
        user_agent=request.user_agent.string,
        referrer=request.referrer,
        country_code=country_code,
        country_name=country_name,
        earnings=user_earnings / 1000
    )
    click.save()
    
    shortened.clicks += 1
    shortened.earnings += (user_earnings / 1000)
    shortened.save()
    
    user.total_views += 1
    user.total_earnings += (user_earnings / 1000)
    user.balance += (user_earnings / 1000)
    user.save()
    
    return jsonify({
        'success': True,
        'redirect_url': shortened.original_url,
        'earnings': round(user_earnings / 1000, 4)
    })

# ==================== REDIRECT ROUTE ====================

@app.route('/<short_code>')
def redirect_url(short_code):
    """Show ad wait page then redirect"""
    shortened = ShortenedURL.objects(short_code=short_code).first()
    
    if not shortened or not shortened.is_active:
        return render_template('404.html'), 404
    
    if shortened.expires_at and datetime.utcnow() > shortened.expires_at:
        return render_template('404.html'), 404
    
    country_code, country_name = get_country_from_ip(request.remote_addr)
    cpm_rate = get_country_cpm_rate(country_code)
    
    user = shortened.user
    user_earnings = calculate_user_earnings(cpm_rate, user.commission_rate)
    
    click = Click(
        url=shortened,
        ip_address=request.remote_addr,
        user_agent=request.user_agent.string,
        referrer=request.referrer,
        country_code=country_code,
        country_name=country_name,
        earnings=user_earnings / 1000
    )
    click.save()
    
    shortened.clicks += 1
    shortened.earnings += (user_earnings / 1000)
    shortened.save()
    
    user.total_views += 1
    user.total_earnings += (user_earnings / 1000)
    user.balance += (user_earnings / 1000)
    user.save()
    
    return redirect(shortened.original_url)


#_______________________________________________________________________

# Add Admin User Model
class AdminUser(Document):
    username = StringField(unique=True, required=True)
    email = StringField(unique=True, required=True)
    password = StringField(required=True)
    role = StringField(default='admin')  # admin, moderator, support
    permissions = ListField(StringField())
    is_active = BooleanField(default=True)
    created_at = DateTimeField(default=datetime.utcnow)
    last_login = DateTimeField(null=True)
    
    meta = {
        'collection': 'admin_users',
        'indexes': ['username', 'email']
    }

    def set_password(self, password):
        self.password = generate_password_hash(password)

    def check_password(self, password):
        return check_password_hash(self.password, password)

# Admin decorator
def admin_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if 'admin_id' not in session:
            return redirect(url_for('admin_login'))
        admin = AdminUser.objects(id=session['admin_id']).first()
        if not admin or not admin.is_active:
            return redirect(url_for('admin_login'))
        return f(*args, **kwargs)
    return decorated_function

# ==================== ADMIN AUTHENTICATION ====================

@app.route('/admin/login', methods=['GET', 'POST'])
def admin_login():
    if request.method == 'POST':
        data = request.get_json()
        username = data.get('username')
        password = data.get('password')
        
        admin = AdminUser.objects(username=username).first()
        
        if not admin or not admin.check_password(password):
            return jsonify({'error': 'Invalid credentials'}), 401
        
        if not admin.is_active:
            return jsonify({'error': 'Account disabled'}), 403
        
        session['admin_id'] = str(admin.id)
        session['admin_username'] = admin.username
        admin.last_login = datetime.utcnow()
        admin.save()
        
        return jsonify({'success': 'Login successful'}), 200
    
    return render_template('admin/login.html')

@app.route('/admin/logout')
def admin_logout():
    session.clear()
    return redirect(url_for('admin_login'))

# ==================== ADMIN DASHBOARD ====================

@app.route('/admin')
@app.route('/admin/dashboard')
@admin_required
def admin_dashboard():
    # Get statistics
    total_users = User.objects.count()
    total_links = ShortenedURL.objects.count()
    total_clicks = Click.objects.count()
    total_earnings = sum(User.objects.scalar('total_earnings'))
    pending_withdrawals = Withdrawal.objects(status='pending').count()
    total_withdrawn = sum(Withdrawal.objects(status='approved').scalar('amount')) or 0
    
    # Recent users
    recent_users = User.objects.order_by('-created_at').limit(5)
    
    # Recent links
    recent_links = ShortenedURL.objects.order_by('-created_at').limit(5)
    
    # Pending withdrawals
    pending = Withdrawal.objects(status='pending').limit(10)
    
    # Chart data - clicks per day (last 7 days)
    seven_days_ago = datetime.utcnow() - timedelta(days=7)
    clicks_data = {}
    
    for i in range(7):
        date = (datetime.utcnow() - timedelta(days=i)).date()
        clicks = Click.objects(clicked_at__gte=date).count()
        clicks_data[str(date)] = clicks
    
    return render_template('admin/dashboard.html',
                         total_users=total_users,
                         total_links=total_links,
                         total_clicks=total_clicks,
                         total_earnings=round(total_earnings, 2),
                         pending_withdrawals=pending_withdrawals,
                         total_withdrawn=round(total_withdrawn, 2),
                         recent_users=recent_users,
                         recent_links=recent_links,
                         pending_withdrawals_list=pending,
                         clicks_data=clicks_data)

# ==================== USER MANAGEMENT ====================

@app.route('/admin/users')
@admin_required
def admin_users():
    page = request.args.get('page', 1, type=int)
    search = request.args.get('search', '')
    
    if search:
        users = User.objects(username__icontains=search).order_by('-created_at').paginate(page=page, per_page=20)
    else:
        users = User.objects.order_by('-created_at').paginate(page=page, per_page=20)
    
    return render_template('admin/users.html', users=users.items, page=page, total=users.total)

@app.route('/admin/user/<user_id>')
@admin_required
def admin_user_detail(user_id):
    try:
        from bson.objectid import ObjectId
        user = User.objects(id=ObjectId(user_id)).first()
    except:
        return redirect(url_for('admin_users'))
    
    if not user:
        return redirect(url_for('admin_users'))
    
    urls = ShortenedURL.objects(user=user)
    withdrawals = Withdrawal.objects(user=user)
    
    return render_template('admin/user_detail.html',
                         user=user,
                         urls=urls,
                         withdrawals=withdrawals)

@app.route('/admin/api/user/<user_id>/ban', methods=['POST'])
@admin_required
def ban_user(user_id):
    try:
        from bson.objectid import ObjectId
        user = User.objects(id=ObjectId(user_id)).first()
    except:
        return jsonify({'error': 'User not found'}), 404
    
    if not user:
        return jsonify({'error': 'User not found'}), 404
    
    user.is_banned = True
    user.save()
    
    return jsonify({'success': True, 'message': 'User banned'})

@app.route('/admin/api/user/<user_id>/unban', methods=['POST'])
@admin_required
def unban_user(user_id):
    try:
        from bson.objectid import ObjectId
        user = User.objects(id=ObjectId(user_id)).first()
    except:
        return jsonify({'error': 'User not found'}), 404
    
    if not user:
        return jsonify({'error': 'User not found'}), 404
    
    user.is_banned = False
    user.save()
    
    return jsonify({'success': True, 'message': 'User unbanned'})

@app.route('/admin/api/user/<user_id>/delete', methods=['DELETE'])
@admin_required
def admin_delete_user(user_id):
    try:
        from bson.objectid import ObjectId
        user = User.objects(id=ObjectId(user_id)).first()
    except:
        return jsonify({'error': 'User not found'}), 404
    
    if not user:
        return jsonify({'error': 'User not found'}), 404
    
    # Delete all user data
    ShortenedURL.objects(user=user).delete()
    Click.objects(url__in=ShortenedURL.objects(user=user)).delete()
    Withdrawal.objects(user=user).delete()
    user.delete()
    
    return jsonify({'success': True, 'message': 'User deleted'})

# ==================== LINK MANAGEMENT ====================

@app.route('/admin/links')
@admin_required
def admin_links():
    page = request.args.get('page', 1, type=int)
    search = request.args.get('search', '')
    
    if search:
        links = ShortenedURL.objects(short_code__icontains=search).order_by('-created_at').paginate(page=page, per_page=20)
    else:
        links = ShortenedURL.objects.order_by('-created_at').paginate(page=page, per_page=20)
    
    return render_template('admin/links.html', links=links.items, page=page, total=links.total)

@app.route('/admin/api/link/<link_id>/delete', methods=['DELETE'])
@admin_required
def admin_delete_link(link_id):
    try:
        from bson.objectid import ObjectId
        link = ShortenedURL.objects(id=ObjectId(link_id)).first()
    except:
        return jsonify({'error': 'Link not found'}), 404
    
    if not link:
        return jsonify({'error': 'Link not found'}), 404
    
    # Delete clicks
    Click.objects(url=link).delete()
    link.delete()
    
    return jsonify({'success': True, 'message': 'Link deleted'})

@app.route('/admin/api/link/<link_id>/disable', methods=['POST'])
@admin_required
def admin_disable_link(link_id):
    try:
        from bson.objectid import ObjectId
        link = ShortenedURL.objects(id=ObjectId(link_id)).first()
    except:
        return jsonify({'error': 'Link not found'}), 404
    
    if not link:
        return jsonify({'error': 'Link not found'}), 404
    
    link.is_active = False
    link.save()
    
    return jsonify({'success': True, 'message': 'Link disabled'})

# ==================== WITHDRAWAL MANAGEMENT ====================

@app.route('/admin/withdrawals')
@admin_required
def admin_withdrawals():
    status = request.args.get('status', 'pending')
    
    withdrawals = Withdrawal.objects(status=status).order_by('-requested_at')
    
    return render_template('admin/withdrawals.html',
                         withdrawals=withdrawals,
                         status=status)

@app.route('/admin/api/withdrawal/<withdrawal_id>/approve', methods=['POST'])
@admin_required
def approve_withdrawal(withdrawal_id):
    try:
        from bson.objectid import ObjectId
        withdrawal = Withdrawal.objects(id=ObjectId(withdrawal_id)).first()
    except:
        return jsonify({'error': 'Withdrawal not found'}), 404
    
    if not withdrawal:
        return jsonify({'error': 'Withdrawal not found'}), 404
    
    withdrawal.status = 'approved'
    withdrawal.processed_at = datetime.utcnow()
    withdrawal.save()
    
    user = withdrawal.user
    user.withdrawn += withdrawal.amount
    user.save()
    
    return jsonify({'success': True, 'message': 'Withdrawal approved'})

@app.route('/admin/api/withdrawal/<withdrawal_id>/reject', methods=['POST'])
@admin_required
def reject_withdrawal(withdrawal_id):
    try:
        from bson.objectid import ObjectId
        withdrawal = Withdrawal.objects(id=ObjectId(withdrawal_id)).first()
    except:
        return jsonify({'error': 'Withdrawal not found'}), 404
    
    if not withdrawal:
        return jsonify({'error': 'Withdrawal not found'}), 404
    
    withdrawal.status = 'rejected'
    withdrawal.processed_at = datetime.utcnow()
    withdrawal.save()
    
    # Refund balance
    user = withdrawal.user
    user.balance += withdrawal.amount
    user.save()
    
    return jsonify({'success': True, 'message': 'Withdrawal rejected and balance refunded'})

# ==================== AD RATES MANAGEMENT ====================

@app.route('/admin/ad-rates')
@admin_required
def admin_ad_rates():
    rates = AdRate.objects.order_by('-updated_at')
    
    return render_template('admin/ad_rates.html', rates=rates)

@app.route('/admin/api/rate/<rate_id>/update', methods=['POST'])
@admin_required
def update_ad_rate(rate_id):
    try:
        from bson.objectid import ObjectId
        rate = AdRate.objects(id=ObjectId(rate_id)).first()
    except:
        return jsonify({'error': 'Rate not found'}), 404
    
    data = request.get_json()
    
    if not rate:
        return jsonify({'error': 'Rate not found'}), 404
    
    rate.rate = float(data.get('rate', rate.rate))
    rate.updated_at = datetime.utcnow()
    rate.save()
    
    return jsonify({'success': True, 'message': 'Rate updated'})

# ==================== REPORTS & ANALYTICS ====================

@app.route('/admin/reports')
@admin_required
def admin_reports():
    # User registration trend (last 30 days)
    thirty_days_ago = datetime.utcnow() - timedelta(days=30)
    user_registrations = {}
    
    for i in range(30):
        date = (datetime.utcnow() - timedelta(days=i)).date()
        count = User.objects(created_at__gte=datetime.combine(date, datetime.min.time())).count()
        user_registrations[str(date)] = count
    
    # Revenue data
    total_platform_revenue = sum(User.objects.scalar('total_earnings')) or 0
    total_user_paid = sum(User.objects.scalar('withdrawn')) or 0
    platform_commission = total_platform_revenue - total_user_paid
    
    # Top users by earnings
    top_users = User.objects.order_by('-total_earnings').limit(10)
    
    # Top links by clicks
    top_links = ShortenedURL.objects.order_by('-clicks').limit(10)
    
    return render_template('admin/reports.html',
                         user_registrations=user_registrations,
                         total_platform_revenue=round(total_platform_revenue, 2),
                         total_user_paid=round(total_user_paid, 2),
                         platform_commission=round(platform_commission, 2),
                         top_users=top_users,
                         top_links=top_links)

# ==================== ADMIN SETTINGS ====================

@app.route('/admin/settings')
@admin_required
def admin_settings():
    admin = AdminUser.objects(id=session['admin_id']).first()
    admins = AdminUser.objects.all()
    
    return render_template('admin/settings.html',
                         admin=admin,
                         admins=admins)

@app.route('/admin/api/admin/<admin_id>/delete', methods=['DELETE'])
@admin_required
def delete_admin(admin_id):
    try:
        from bson.objectid import ObjectId
        admin_to_delete = AdminUser.objects(id=ObjectId(admin_id)).first()
    except:
        return jsonify({'error': 'Admin not found'}), 404
    
    if not admin_to_delete:
        return jsonify({'error': 'Admin not found'}), 404
    
    # Don't allow deleting yourself
    if str(admin_to_delete.id) == session.get('admin_id'):
        return jsonify({'error': 'Cannot delete yourself'}), 403
    
    admin_to_delete.delete()
    
    return jsonify({'success': True, 'message': 'Admin deleted'})

@app.route('/admin/api/admin/<admin_id>/toggle', methods=['POST'])
@admin_required
def toggle_admin_status(admin_id):
    try:
        from bson.objectid import ObjectId
        admin_user = AdminUser.objects(id=ObjectId(admin_id)).first()
    except:
        return jsonify({'error': 'Admin not found'}), 404
    
    if not admin_user:
        return jsonify({'error': 'Admin not found'}), 404
    
    admin_user.is_active = not admin_user.is_active
    admin_user.save()
    
    return jsonify({'success': True, 'is_active': admin_user.is_active})

# ==================== SUPPORT TICKETS ====================

class SupportTicket(Document):
    user = ReferenceField(User)
    subject = StringField(required=True)
    message = StringField(required=True)
    status = StringField(default='open')  # open, in_progress, closed
    created_at = DateTimeField(default=datetime.utcnow)
    replies = ListField(DictField())
    
    meta = {
        'collection': 'support_tickets',
        'indexes': ['user', 'status', 'created_at']
    }

@app.route('/admin/support')
@admin_required
def admin_support():
    status = request.args.get('status', 'open')
    
    tickets = SupportTicket.objects(status=status).order_by('-created_at')
    
    return render_template('admin/support.html',
                         tickets=tickets,
                         status=status)

@app.route('/admin/support/<ticket_id>')
@admin_required
def admin_support_detail(ticket_id):
    try:
        from bson.objectid import ObjectId
        ticket = SupportTicket.objects(id=ObjectId(ticket_id)).first()
    except:
        return redirect(url_for('admin_support'))
    
    if not ticket:
        return redirect(url_for('admin_support'))
    
    return render_template('admin/support_detail.html', ticket=ticket)

@app.route('/admin/api/support/<ticket_id>/reply', methods=['POST'])
@admin_required
def support_reply(ticket_id):
    try:
        from bson.objectid import ObjectId
        ticket = SupportTicket.objects(id=ObjectId(ticket_id)).first()
    except:
        return jsonify({'error': 'Ticket not found'}), 404
    
    data = request.get_json()
    admin = AdminUser.objects(id=session['admin_id']).first()
    
    if not ticket:
        return jsonify({'error': 'Ticket not found'}), 404
    
    reply = {
        'from': 'admin',
        'admin_name': admin.username,
        'message': data.get('message'),
        'created_at': datetime.utcnow().isoformat()
    }
    
    if not ticket.replies:
        ticket.replies = []
    
    ticket.replies.append(reply)
    ticket.status = 'in_progress'
    ticket.save()
    
    return jsonify({'success': True, 'message': 'Reply sent'})

@app.route('/admin/api/support/<ticket_id>/close', methods=['POST'])
@admin_required
def close_support_ticket(ticket_id):
    try:
        from bson.objectid import ObjectId
        ticket = SupportTicket.objects(id=ObjectId(ticket_id)).first()
    except:
        return jsonify({'error': 'Ticket not found'}), 404
    
    if not ticket:
        return jsonify({'error': 'Ticket not found'}), 404
    
    ticket.status = 'closed'
    ticket.save()
    
    return jsonify({'success': True, 'message': 'Ticket closed'})


# ==================== ERROR HANDLERS ====================

@app.errorhandler(404)
def not_found(e):
    return render_template('404.html'), 404

@app.errorhandler(500)
def server_error(e):
    return jsonify({'error': 'Server error'}), 500

# ==================== INITIALIZE ====================

if __name__ == '__main__':
    app.run(debug=False, host='0.0.0.0', port=5000)