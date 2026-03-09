import os
import json
import uuid
from flask import Flask, render_template, jsonify, send_from_directory, request, redirect, url_for, flash
from flask_sqlalchemy import SQLAlchemy
from flask_login import LoginManager, UserMixin, login_user, login_required, logout_user, current_user
from werkzeug.security import generate_password_hash, check_password_hash
import urllib.request
import json
from datetime import datetime, timedelta

BASE_DIR = os.path.abspath(os.path.dirname(__file__))

app = Flask(__name__, static_folder=os.path.join(BASE_DIR, 'static'))
app.jinja_env.add_extension('jinja2.ext.do')
app.config['SECRET_KEY'] = 'spain_family_trip_2026_jackie'
# 절대 경로로 DB 위치 고정 (스페인 일정과 오디오 가이드 데이터가 모두 이 파일에 저장됩니다)
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///' + os.path.join(BASE_DIR, 'tour_guide.db')
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

db = SQLAlchemy(app)
login_manager = LoginManager(app)
login_manager.login_view = 'admin_login'

# ==========================================
# 🗄️ 데이터베이스 모델 정의
# ==========================================

class AppSetting(db.Model):
    key = db.Column(db.String(50), primary_key=True)
    value = db.Column(db.Text, nullable=True)

    def to_dict(self):
        return {self.key: self.value}

class Admin(UserMixin, db.Model):
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(80), unique=True, nullable=False)
    password_hash = db.Column(db.String(120), nullable=False)

# [1] 스페인 일정 모델
class Itinerary(db.Model):
    id = db.Column(db.String(50), primary_key=True)
    city = db.Column(db.String(100), nullable=False)
    period = db.Column(db.String(50), nullable=False)
    nights = db.Column(db.String(20), nullable=False)
    desc = db.Column(db.Text, nullable=True)
    tips = db.Column(db.Text, nullable=True)
    stay = db.Column(db.Text, nullable=True)
    hasParking = db.Column(db.Boolean, default=False)
    routeText = db.Column(db.Text, nullable=True)
    mapLink = db.Column(db.String(500), nullable=True)
    mapIframe = db.Column(db.Text, nullable=True)
    routeText2 = db.Column(db.Text, nullable=True)
    mapLink2 = db.Column(db.String(500), nullable=True)
    mapIframe2 = db.Column(db.Text, nullable=True)
    parkingInfo = db.Column(db.Text, nullable=True)
    foodRecs = db.Column(db.Text, nullable=True)
    under10 = db.Column(db.Text, nullable=True)
    spotRecs = db.Column(db.Text, nullable=True)
    shoppingRecs = db.Column(db.Text, nullable=True)
    schedule_json = db.Column(db.Text, nullable=True)
    photos_json = db.Column(db.Text, nullable=True)

    def to_dict(self):
        return {
            'id': self.id, 'city': self.city, 'period': self.period, 'nights': self.nights,
            'desc': self.desc, 'tips': self.tips, 'stay': self.stay, 'hasParking': self.hasParking,
            'routeText': self.routeText, 'mapLink': self.mapLink, 'mapIframe': self.mapIframe,
            'routeText2': self.routeText2, 'mapLink2': self.mapLink2, 'mapIframe2': self.mapIframe2,
            'parkingInfo': self.parkingInfo, 'foodRecs': self.foodRecs, 'under10': self.under10,
            'spotRecs': self.spotRecs, 'shoppingRecs': self.shoppingRecs,
            'schedule': json.loads(self.schedule_json) if self.schedule_json else [],
            'photos': json.loads(self.photos_json) if self.photos_json else []
        }

# [2] 오디오 가이드 모델
class Region(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False)
    attractions = db.relationship('Attraction', backref='region', lazy=True, cascade="all, delete-orphan")

class Attraction(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False)
    image_file = db.Column(db.String(100), nullable=True, default='default.jpg')
    region_id = db.Column(db.Integer, db.ForeignKey('region.id'), nullable=False)
    guides = db.relationship('AudioGuide', backref='attraction', lazy=True, cascade="all, delete-orphan")

class AudioGuide(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    title = db.Column(db.String(200), nullable=False)
    content = db.Column(db.Text, nullable=False)
    attraction_id = db.Column(db.Integer, db.ForeignKey('attraction.id'), nullable=False)

class SystemSetting(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    tts_lang = db.Column(db.String(20), default='ko-KR')
    tts_pitch = db.Column(db.Float, default=1.0)
    tts_rate = db.Column(db.Float, default=1.0)
    tts_voice_keyword = db.Column(db.String(100), default='')

@login_manager.user_loader
def load_user(user_id):
    return Admin.query.get(int(user_id))

def save_picture(form_picture):
    random_hex = uuid.uuid4().hex
    _, f_ext = os.path.splitext(form_picture.filename)
    picture_fn = random_hex + f_ext
    picture_path = os.path.join(app.root_path, 'static/uploads', picture_fn)
    if not os.path.exists(os.path.dirname(picture_path)):
        os.makedirs(os.path.dirname(picture_path))
    form_picture.save(picture_path)
    return picture_fn

# [4] 생존 회화 모델 추가
class Phrase(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    category = db.Column(db.String(50), nullable=False) # street, transport, restaurant, attraction, airport
    ko = db.Column(db.String(200), nullable=False)      # 한국어
    es = db.Column(db.String(200), nullable=False)      # 스페인어
    en = db.Column(db.String(200), nullable=True)       # 영어

    def to_dict(self):
        return {
            'id': self.id, 'category': self.category,
            'ko': self.ko, 'es': self.es, 'en': self.en
        }

# ==========================================
# 🌐 라우팅 (PWA & 메인 일정)
# ==========================================
@app.route('/manifest.json')
def serve_manifest(): return send_from_directory('static', 'manifest.json')
@app.route('/sw.js')
def serve_sw(): return send_from_directory('static', 'sw.js')
@app.route('/icon.png')
def serve_favicon(): return send_from_directory('static', 'icon.png')

@app.route('/')
def index():
    # 메인 화면은 스페인 드라이빙 가이드
    return render_template('index.html')

@app.route('/api/itinerary')
def api_itinerary():
    itineraries = Itinerary.query.all()
    return jsonify([item.to_dict() for item in itineraries])

@app.route('/api/itinerary/<string:id>')
@login_required
def get_itinerary_single(id):
    """수정 모달용 개별 일정 데이터 반환"""
    item = Itinerary.query.get_or_404(id)
    return jsonify(item.to_dict())

# ==========================================
# 🎧 라우팅 (오디오 가이드 사용자 화면)
# ==========================================
@app.route('/audio')
def audio_main():
    regions = Region.query.all()
    return render_template('audio_main.html', regions=regions)

@app.route('/region/<int:region_id>')
def region_detail(region_id):
    region = Region.query.get_or_404(region_id)
    return render_template('region.html', region=region)

@app.route('/attraction/<int:attraction_id>')
def attraction_detail(attraction_id):
    attraction = Attraction.query.get_or_404(attraction_id)
    return render_template('attraction.html', attraction=attraction)

@app.route('/guide/<int:guide_id>')
def guide_detail(guide_id):
    guide = AudioGuide.query.get_or_404(guide_id)
    prev_guide = AudioGuide.query.filter(AudioGuide.attraction_id == guide.attraction_id, AudioGuide.id < guide.id).order_by(AudioGuide.id.desc()).first()
    next_guide = AudioGuide.query.filter(AudioGuide.attraction_id == guide.attraction_id, AudioGuide.id > guide.id).order_by(AudioGuide.id.asc()).first()
    setting = SystemSetting.query.first() or SystemSetting()
    return render_template('guide.html', guide=guide, setting=setting, prev_guide=prev_guide, next_guide=next_guide)


# ==========================================
# ⚙️ 라우팅 (관리자 화면 통합)
# ==========================================
@app.route('/admin/login', methods=['GET', 'POST'])
def admin_login():
    if request.method == 'POST':
        admin = Admin.query.filter_by(username=request.form.get('username')).first()
        if admin and check_password_hash(admin.password_hash, request.form.get('password')):
            login_user(admin)
            return redirect(url_for('admin_dashboard'))
        flash('아이디 또는 비밀번호가 올바르지 않습니다.')
    return render_template('admin_login.html')

@app.route('/admin/dashboard')
@login_required
def admin_dashboard():
    # 스페인 일정 관리자 화면
    itineraries = Itinerary.query.all()
    return render_template('admin_dashboard.html', itineraries=itineraries)

@app.route('/admin/logout')
@login_required
def admin_logout():
    logout_user()
    return redirect(url_for('index'))

@app.route('/admin/change_password', methods=['POST'])
@login_required
def change_password():
    current_password = request.form.get('current_password')
    new_password = request.form.get('new_password')
    confirm_password = request.form.get('confirm_password')

    admin = current_user  # 현재 로그인된 관리자 객체

    # 1. 현재 비밀번호 확인
    if not check_password_hash(admin.password_hash, current_password):
        flash('❌ 현재 비밀번호가 일치하지 않습니다.')
        return redirect(url_for('admin_dashboard'))

    # 2. 새 비밀번호 일치 여부 확인
    if new_password != confirm_password:
        flash('❌ 새 비밀번호와 확인 비밀번호가 일치하지 않습니다.')
        return redirect(url_for('admin_dashboard'))

    # 3. 새 비밀번호 길이 제한 (예: 4자리 이상)
    if len(new_password) < 4:
        flash('❌ 새 비밀번호는 4자리 이상으로 설정해 주세요.')
        return redirect(url_for('admin_dashboard'))

    # 4. 비밀번호 업데이트 및 해싱
    admin.password_hash = generate_password_hash(new_password, method='pbkdf2:sha256')
    db.session.commit()

    # 5. 변경 완료 후 강제 로그아웃 처리 (보안)
    logout_user()
    flash('✅ 비밀번호가 성공적으로 변경되었습니다. 새 비밀번호로 다시 로그인해 주세요.')
    return redirect(url_for('admin_login'))
# ==========================================
# 🎧 라우팅 (오디오 가이드 관리자 화면)
# ==========================================

@app.route('/admin/audio')
@login_required
def admin_audio():
    regions = Region.query.all()
    setting = SystemSetting.query.first()
    if not setting:
        setting = SystemSetting()
        db.session.add(setting)
        db.session.commit()
    return render_template('admin_audio.html', regions=regions, setting=setting)

@app.route('/admin/add_region', methods=['POST'])
@login_required
def add_region():
    name = request.form.get('name')
    if name:
        db.session.add(Region(name=name))
        db.session.commit()
        flash(f'✅ 지역 "{name}" 추가 완료')
    return redirect(url_for('admin_audio'))

@app.route('/admin/add_attraction', methods=['POST'])
@login_required
def add_attraction():
    name = request.form.get('name')
    region_id = request.form.get('region_id')
    image_fn = None
    if 'image_file' in request.files and request.files['image_file'].filename != '':
        image_fn = save_picture(request.files['image_file'])
    if name and region_id:
        db.session.add(Attraction(name=name, region_id=region_id, image_file=image_fn))
        db.session.commit()
        flash(f'✅ 관광지 "{name}" 추가 완료')
    return redirect(url_for('admin_audio'))

@app.route('/admin/add_guide', methods=['POST'])
@login_required
def add_guide():
    title = request.form.get('title')
    content = request.form.get('content')
    attraction_id = request.form.get('attraction_id')
    if title and content and attraction_id:
        db.session.add(AudioGuide(title=title, content=content, attraction_id=attraction_id))
        db.session.commit()
        flash(f'✅ 가이드 "{title}" 추가 완료')
    return redirect(url_for('admin_audio'))

@app.route('/admin/update_tts_setting', methods=['POST'])
@login_required
def update_tts_setting():
    setting = SystemSetting.query.first()
    setting.tts_lang = request.form.get('tts_lang', 'ko-KR')
    setting.tts_rate = float(request.form.get('tts_rate', 1.0))
    setting.tts_pitch = float(request.form.get('tts_pitch', 1.0))
    db.session.commit()
    flash('✅ TTS 설정이 업데이트되었습니다.')
    return redirect(url_for('admin_audio'))

@app.route('/admin/delete_region/<int:id>')
@login_required
def delete_region(id):
    region = Region.query.get_or_404(id)
    db.session.delete(region)
    db.session.commit()
    flash('🗑️ 지역이 삭제되었습니다.')
    return redirect(url_for('admin_audio'))

@app.route('/admin/delete_attraction/<int:id>')
@login_required
def delete_attraction(id):
    attraction = Attraction.query.get_or_404(id)
    db.session.delete(attraction)
    db.session.commit()
    flash('🗑️ 관광지가 삭제되었습니다.')
    return redirect(url_for('admin_audio'))

@app.route('/admin/delete_guide/<int:id>')
@login_required
def delete_guide(id):
    guide = AudioGuide.query.get_or_404(id)
    db.session.delete(guide)
    db.session.commit()
    flash('🗑️ 가이드가 삭제되었습니다.')
    return redirect(url_for('admin_audio'))

@app.route('/admin/edit_guide/<int:id>', methods=['POST'])
@login_required
def edit_guide(id):
    guide = AudioGuide.query.get_or_404(id)
    title = request.form.get('title')
    content = request.form.get('content')
    attraction_id = request.form.get('attraction_id')

    if title and content and attraction_id:
        guide.title = title
        guide.content = content
        guide.attraction_id = attraction_id
        db.session.commit()
        flash(f'✅ 가이드 "{title}" 수정 완료')
    else:
        flash('❌ 모든 필드를 입력해주세요.')

    return redirect(url_for('admin_audio'))

@app.route('/admin/add_itinerary', methods=['POST'])
@login_required
def add_itinerary():
    # 체크박스 값 처리 (체크되면 '1', 아니면 None)
    has_parking = True if request.form.get('hasParking') else False

    new_item = Itinerary(
        id=request.form.get('id'),
        city=request.form.get('city'),
        period=request.form.get('period'),
        nights=request.form.get('nights'),
        desc=request.form.get('desc'),
        tips=request.form.get('tips'),
        stay=request.form.get('stay'),
        hasParking=has_parking,
        routeText=request.form.get('routeText'),
        mapLink=request.form.get('mapLink'),
        mapIframe=request.form.get('mapIframe'),
        routeText2=request.form.get('routeText2'),
        mapLink2=request.form.get('mapLink2'),
        mapIframe2=request.form.get('mapIframe2'),
        parkingInfo=request.form.get('parkingInfo'),
        foodRecs=request.form.get('foodRecs'),
        under10=request.form.get('under10'),
        spotRecs=request.form.get('spotRecs'),
        shoppingRecs=request.form.get('shoppingRecs'),
        schedule_json=request.form.get('schedule_json'),
        photos_json=request.form.get('photos_json')
    )

    try:
        db.session.add(new_item)
        db.session.commit()
        flash(f"✅ '{new_item.city}' 일정이 성공적으로 등록되었습니다.")
    except Exception as e:
        db.session.rollback()
        flash(f"❌ 등록 실패 (ID가 중복되었을 수 있습니다): {str(e)}")

    return redirect(url_for('admin_dashboard'))

@app.route('/admin/edit_itinerary/<string:id>', methods=['POST'])
@login_required
def edit_itinerary(id):
    # 기존 일정 객체 가져오기
    item = Itinerary.query.get_or_404(id)

    try:
        # 폼 데이터로 객체 속성 덮어쓰기 (ID는 수정 불가하므로 제외)
        item.city = request.form.get('city')
        item.period = request.form.get('period')
        item.nights = request.form.get('nights')
        item.desc = request.form.get('desc')
        item.tips = request.form.get('tips')
        item.stay = request.form.get('stay')
        item.hasParking = True if request.form.get('hasParking') else False
        item.routeText = request.form.get('routeText')
        item.mapLink = request.form.get('mapLink')
        item.mapIframe = request.form.get('mapIframe')
        item.routeText2 = request.form.get('routeText2')
        item.mapLink2 = request.form.get('mapLink2')
        item.mapIframe2 = request.form.get('mapIframe2')
        item.parkingInfo = request.form.get('parkingInfo')
        item.foodRecs = request.form.get('foodRecs')
        item.under10 = request.form.get('under10')
        item.spotRecs = request.form.get('spotRecs')
        item.shoppingRecs = request.form.get('shoppingRecs')

        # JSON으로 변환된 상세일정 및 갤러리 데이터 업데이트
        item.schedule_json = request.form.get('schedule_json')
        item.photos_json = request.form.get('photos_json')

        db.session.commit()
        flash(f"✅ '{item.city}' 일정이 성공적으로 수정되었습니다.")
    except Exception as e:
        db.session.rollback()
        flash(f"❌ 수정 실패: {str(e)}")

    return redirect(url_for('admin_dashboard'))

@app.route('/admin/delete_itinerary/<string:id>')
@login_required
def delete_itinerary(id):
    # 1. 삭제할 일정 객체를 DB에서 가져옵니다 (없으면 404 에러)
    item = Itinerary.query.get_or_404(id)

    try:
        # 2. DB에서 해당 객체를 삭제하고 저장(commit)합니다.
        db.session.delete(item)
        db.session.commit()
        flash(f"🗑️ '{item.city}' 일정이 성공적으로 삭제되었습니다.")
    except Exception as e:
        # 오류 발생 시 롤백
        db.session.rollback()
        flash(f"❌ 삭제 실패: {str(e)}")

    # 3. 처리가 끝나면 다시 대시보드 화면으로 돌아갑니다.
    return redirect(url_for('admin_dashboard'))

# --- [3] 여행 가계부 모델 추가 ---
class Expense(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    date = db.Column(db.String(10), nullable=False)   # 2026-04-04
    time = db.Column(db.String(5), nullable=True)    # 14:30
    region = db.Column(db.String(50), nullable=True) # 바르셀로나
    place = db.Column(db.String(100), nullable=True) # 보케리아 시장
    category = db.Column(db.String(50), nullable=True) # 식비, 쇼핑 등
    amount = db.Column(db.Float, nullable=False)     # 금액
    currency = db.Column(db.String(10), default='EUR') # EUR, USD, KRW

# --- 💱 전일자 기준 환율 가져오기 함수 ---
exchange_rate_cache = {}

def get_rates_for_date(tx_date_str):
    try:
        # 1. 거래일(tx_date)을 기준으로 하루 전(prev_date) 날짜 계산
        tx_date = datetime.strptime(tx_date_str, '%Y-%m-%d')
        prev_date = tx_date - timedelta(days=1)

        # 2. 만약 전일자가 오늘이나 미래라면 가장 최신(latest) 환율 사용
        if prev_date.date() >= datetime.now().date():
            target_date_str = 'latest'
        else:
            target_date_str = prev_date.strftime('%Y-%m-%d')

        # 3. 캐시에 이미 가져온 환율이 있으면 API 호출 생략 (속도 최적화)
        if target_date_str in exchange_rate_cache:
            return exchange_rate_cache[target_date_str]

        # 4. Frankfurter API 호출 (과거 날짜 환율 지원)
        url = f"https://api.frankfurter.app/{target_date_str}?from=EUR&to=KRW,USD"
        req = urllib.request.Request(url, headers={'User-Agent': 'Mozilla/5.0'})
        with urllib.request.urlopen(req, timeout=3) as response:
            data = json.loads(response.read().decode())
            rate_eur = data['rates']['KRW']
            rate_usd = data['rates']['KRW'] / data['rates']['USD']
            ref_date = data['date'] # API가 반환한 실제 기준일 (주말은 금요일 환율 반환)

            result = {'eur': rate_eur, 'usd': rate_usd, 'date': ref_date}
            exchange_rate_cache[target_date_str] = result
            return result
    except Exception as e:
        print(f"환율 동기화 실패 ({tx_date_str}):", e)
        return {'eur': 1450.0, 'usd': 1350.0, 'date': '기본값'}

# --- 가계부 사용자 화면 라우팅 ---
@app.route('/expenses')
def expense_main():
    # 💡 관리자로 로그인한 경우에만 DB에서 지출 내역을 가져옵니다.
    if current_user.is_authenticated:
        expenses = Expense.query.order_by(Expense.date.desc(), Expense.time.desc()).all()
    else:
        # 로그인하지 않은 경우 빈 리스트를 전달하여 내역이 없는 것처럼 보여줍니다.
        expenses = []

    # 전일자 환율 데이터는 합계 계산 로직을 위해 그대로 유지하거나,
    # 비로그인 시 빈 딕셔너리를 보내도록 처리합니다.
    rates_by_date = {}
    if expenses:
        for ex in expenses:
            if ex.date not in rates_by_date:
                rates_by_date[ex.date] = get_rates_for_date(ex.date)

    return render_template('expense_main.html', expenses=expenses, rates_by_date=rates_by_date)

# --- 가계부 API (저장/삭제) ---
@app.route('/admin/add_expense', methods=['POST'])
@login_required
def add_expense():
    new_ex = Expense(
        date=request.form.get('date'),
        time=request.form.get('time'),
        region=request.form.get('region'),
        place=request.form.get('place'),
        category=request.form.get('category'),
        amount=float(request.form.get('amount', 0)),
        currency=request.form.get('currency', 'EUR')
    )
    db.session.add(new_ex)
    db.session.commit()
    flash('💰 지출 내역이 기록되었습니다.')
    return redirect(url_for('expense_main'))

@app.route('/admin/delete_expense/<int:id>')
@login_required
def delete_expense(id):
    ex = Expense.query.get_or_404(id)
    db.session.delete(ex)
    db.session.commit()
    return redirect(url_for('expense_main'))

@app.route('/admin/edit_expense/<int:id>', methods=['POST'])
@login_required
def edit_expense(id):
    ex = Expense.query.get_or_404(id)
    try:
        ex.date = request.form.get('date')
        ex.time = request.form.get('time')
        ex.region = request.form.get('region')
        ex.place = request.form.get('place')
        ex.category = request.form.get('category')
        ex.amount = float(request.form.get('amount', 0))
        ex.currency = request.form.get('currency')
        db.session.commit()
        flash('✅ 지출 내역이 수정되었습니다.')
    except Exception as e:
        db.session.rollback()
        flash(f'❌ 수정 실패: {str(e)}')
    return redirect(url_for('expense_main'))

# ==========================================
# 🗣️ 라우팅 (생존 회화 관리)
# ==========================================
@app.route('/admin/phrase')
@login_required
def admin_phrase():
    phrases = Phrase.query.all()
    return render_template('admin_phrase.html', phrases=phrases)

@app.route('/api/phrases')
def api_phrases():
    phrases = Phrase.query.all()
    return jsonify([p.to_dict() for p in phrases])

@app.route('/api/phrase/<int:id>')
@login_required
def get_phrase_single(id):
    phrase = Phrase.query.get_or_404(id)
    return jsonify(phrase.to_dict())

@app.route('/admin/add_phrase', methods=['POST'])
@login_required
def add_phrase():
    new_phrase = Phrase(
        category=request.form.get('category'),
        ko=request.form.get('ko'),
        es=request.form.get('es'),
        en=request.form.get('en')
    )
    db.session.add(new_phrase)
    db.session.commit()
    flash('✅ 새 회화가 추가되었습니다.')
    return redirect(url_for('admin_phrase')) # 👈 변경됨

@app.route('/admin/edit_phrase/<int:id>', methods=['POST'])
@login_required
def edit_phrase(id):
    phrase = Phrase.query.get_or_404(id)
    phrase.category = request.form.get('category')
    phrase.ko = request.form.get('ko')
    phrase.es = request.form.get('es')
    phrase.en = request.form.get('en')
    db.session.commit()
    flash('✅ 회화 내용이 수정되었습니다.')
    return redirect(url_for('admin_phrase')) # 👈 변경됨

@app.route('/admin/delete_phrase/<int:id>')
@login_required
def delete_phrase(id):
    phrase = Phrase.query.get_or_404(id)
    db.session.delete(phrase)
    db.session.commit()
    flash('🗑️ 회화가 삭제되었습니다.')
    return redirect(url_for('admin_phrase')) # 👈 변경됨

# ==========================================
# ⚙️ 앱 기본 설정 관리
# ==========================================
@app.route('/api/settings')
def api_settings():
    settings = AppSetting.query.all()
    # Key-Value 형태의 딕셔너리로 변환하여 반환
    return jsonify({s.key: s.value for s in settings})

@app.route('/admin/settings', methods=['GET', 'POST'])
@login_required
def admin_settings():
    if request.method == 'POST':
        # 폼에서 넘어온 모든 데이터를 순회하며 DB 업데이트
        for key, value in request.form.items():
            setting = AppSetting.query.get(key)
            if not setting:
                setting = AppSetting(key=key)
                db.session.add(setting)
            setting.value = value
        db.session.commit()
        flash('✅ 앱 설정이 성공적으로 저장되었습니다.')
        return redirect(url_for('admin_settings'))
    
    # 기존 설정값 불러오기 (없으면 빈 딕셔너리)
    settings = {s.key: s.value for s in AppSetting.query.all()}
    return render_template('admin_settings.html', settings=settings)

# ==========================================
# 🚀 서버 실행
# ==========================================
if __name__ == '__main__':
    with app.app_context():
        # 통합된 모델들(일정 + 오디오가이드)을 모두 생성
        db.create_all()
        if not Admin.query.filter_by(username='admin').first():
            hashed_pw = generate_password_hash('jackie2026', method='pbkdf2:sha256')
            db.session.add(Admin(username='admin', password_hash=hashed_pw))
            db.session.commit()
    app.run(debug=True, host='0.0.0.0', port=5000)
