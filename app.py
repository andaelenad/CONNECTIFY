import os
# AM ADAUGAT render_template AICI
from flask import Flask, request, url_for, session, redirect, render_template 
import spotipy
from spotipy.oauth2 import SpotifyOAuth
from dotenv import load_dotenv
from flask_sqlalchemy import SQLAlchemy # pt baza de date
from werkzeug.security import generate_password_hash, check_password_hash

load_dotenv()

app = Flask(__name__)

app.secret_key = "cheie_secreta_pentru_proiect_connectify"
app.config['SESSION_COOKIE_NAME'] = 'Connectify_Session'

# configurări pt baza de date
# Am actualizat URI-ul pentru Aiven (PostgreSQL)
app.config['SQLALCHEMY_DATABASE_URI'] = "postgresql://avnadmin:AVNS_dlwEpYk7NtFpIKxzuWF@pg-6647a18-rurig.d.aivencloud.com:26923/defaultdb?sslmode=require"
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

db = SQLAlchemy(app)

# clase pt db
class User(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    is_admin = db.Column(db.Boolean, default=False)
    email = db.Column(db.String(120), unique=True, nullable=False)
    password_hash = db.Column(db.String(256), nullable=False)
    spotify_id = db.Column(db.String(100), unique=True, nullable=True)
    display_name = db.Column(db.String(100))
    # legatura cu rating-uri
    ratings = db.relationship('Rating', backref='user', lazy=True)

    def set_password(self, password):
        self.password_hash = generate_password_hash(password)

    def check_password(self, password):
        return check_password_hash(self.password_hash, password)

class SongCache(db.Model):
    spotify_id = db.Column(db.String(100), primary_key=True) # ID-ul unic de la Spotify
    name = db.Column(db.String(200), nullable=False)
    artist = db.Column(db.String(200))
    image_url = db.Column(db.String(500))
    ratings = db.relationship('Rating', backref='song', lazy=True)

class Rating(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    score = db.Column(db.Integer, nullable=False) # nota 1-5
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    spotify_item_id = db.Column(db.String(100), db.ForeignKey('song_cache.spotify_id'), nullable=False)

class Friendship(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    friend_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    status = db.Column(db.String(20), default='pending') # pending, accepted, rejected

# functionalitati app
def create_spotify_oauth():
    return SpotifyOAuth(
        client_id=os.getenv('SPOTIPY_CLIENT_ID'),
        client_secret=os.getenv('SPOTIPY_CLIENT_SECRET'),
        redirect_uri=os.getenv('SPOTIPY_REDIRECT_URI'),
        scope="user-top-read"
    )

def get_token():
    token_info = session.get('token_info', None)
    if not token_info:
        return None
    
    sp_oauth = create_spotify_oauth()
    if sp_oauth.is_token_expired(token_info):
        token_info = sp_oauth.refresh_access_token(token_info['refresh_token'])
        session['token_info'] = token_info
    return token_info

# rute login/signup

@app.route('/signup', methods=['GET', 'POST'])
def signup():
    if request.method == 'POST':
        email = request.form.get('email')
        password = request.form.get('password')
        if User.query.filter_by(email=email).first():
            return "Email-ul există deja!"
        new_user = User(email=email)
        if email == "ruricojocaru@gmail.com": 
            new_user.is_admin = True
        if email == "sabinabrinzei277@gmail.com": 
            new_user.is_admin = True

        new_user.set_password(password)
        db.session.add(new_user)
        db.session.commit()
        return redirect(url_for('login_app'))
    return render_template('signup.html')

@app.route('/login_app', methods=['GET', 'POST'])
def login_app():
    if request.method == 'POST':
        email = request.form.get('email')
        password = request.form.get('password')
        user = User.query.filter_by(email=email).first()
        if user and user.check_password(password):
            session['user_id'] = user.id
            return redirect(url_for('dashboard'))
        return "Login eșuat!"
    return render_template('login.html')

@app.route('/dashboard')
def dashboard():
    if 'user_id' not in session:
        return redirect(url_for('login_app'))
    user = User.query.get(session['user_id'])
    return render_template('dashboard.html', user=user)

@app.route('/logout')
def logout():
    session.clear()
    return redirect(url_for('index'))

# 1. RUTA PRINCIPALĂ
@app.route('/')
def index():
    # trimite la index.html (acum pagina de prezentare)
    return render_template('index.html')

@app.route('/connect_spotify')
def connect_spotify():
    # Pornim fluxul Spotify
    sp_oauth = create_spotify_oauth()
    auth_url = sp_oauth.get_authorize_url()
    return redirect(auth_url)

# 2. RUTA CALLBACK
@app.route('/callback')
def callback():
    if 'user_id' not in session:
        return redirect(url_for('login_app'))

    sp_oauth = create_spotify_oauth()
    code = request.args.get('code')
    token_info = sp_oauth.get_access_token(code)
    session["token_info"] = token_info

    # aici salvam datele Spotify in userul deja logat
    sp = spotipy.Spotify(auth=token_info['access_token'])
    spotify_user = sp.current_user()

    user = User.query.get(session['user_id'])
    user.spotify_id = spotify_user['id']
    user.display_name = spotify_user['display_name']
    db.session.commit()

    return redirect(url_for("dashboard"))

@app.route('/friends')
def view_friends():
    if 'user_id' not in session:
        return redirect(url_for('login_app'))

    # și unde statusul este 'accepted'
    friendships = Friendship.query.filter(
        ((Friendship.user_id == session['user_id']) | (Friendship.friend_id == session['user_id'])),
        (Friendship.status == 'accepted')
    ).all()

    friends_list = []
    for f in friendships:
        # Dacă eu sunt user_id, prietenul este friend_id. Și invers.
        if f.user_id == session['user_id']:
            friend = User.query.get(f.friend_id)
        else:
            friend = User.query.get(f.user_id)
        
        if friend:
            friends_list.append(friend)

    return render_template('friends.html', friends=friends_list)

# 3. RUTA PROFIL 
@app.route('/get_tracks')
def get_tracks():
    token_info = get_token()
    if not token_info:
        return redirect(url_for('connect_spotify'))
    
    sp = spotipy.Spotify(auth=token_info['access_token'])
    results = sp.current_user_top_tracks(limit=5, time_range='short_term')
    
    # trimitem datele catre profil.html
    tracks = results['items']
    return render_template('profile.html', tracks=tracks)

# cautare utilizatori după display_name
@app.route('/search_users', methods=['GET', 'POST'])
def search_users():
    query = request.args.get('query')
    users = []
    if query:
        # Nu ne afișăm pe noi înșine în căutări
        users = User.query.filter(User.display_name.contains(query), User.id != session.get('user_id')).all()
    
    return render_template('search_users.html', users=users)

# send cerere prietenie
@app.route('/add_friend/<int:friend_id>')
def add_friend(friend_id):
    if 'user_id' not in session: return redirect(url_for('login_app'))
    
    # verificare daca exista relatie deja
    exists = Friendship.query.filter_by(user_id=session['user_id'], friend_id=friend_id).first()
    if not exists:
        new_friendship = Friendship(user_id=session['user_id'], friend_id=friend_id, status='pending')
        db.session.add(new_friendship)
        db.session.commit()
    
    return redirect(url_for('search_users'))

@app.route('/requests')
def view_requests():
    if 'user_id' not in session: return redirect(url_for('login_app'))

    # cererile unde ID-ul meu este la "friend_id" (cineva m-a adaugat pe mine)
    pending_requests = Friendship.query.filter_by(friend_id=session['user_id'], status='pending').all()
    # trebuie join manual sau să cautam userii care au trimis cererea
    requesters = [User.query.get(req.user_id) for req in pending_requests]
    
    return render_template('requests.html', requesters=requesters)

# accept cerere prietenie (adaugata pentru functionalitate)
@app.route('/accept_friend/<int:requester_id>')
def accept_friend(requester_id):
    if 'user_id' not in session: return redirect(url_for('login_app'))

    friendship = Friendship.query.filter_by(user_id=requester_id, friend_id=session['user_id'], status='pending').first()
    if friendship:
        friendship.status = 'accepted'
        db.session.commit()
    
    return redirect(url_for('view_requests'))

@app.route('/admin_panel')
def admin_panel():
    # 1. Verificăm dacă user-ul este logat
    if 'user_id' not in session:
        return redirect(url_for('login_app'))
    
    # 2. Verificăm dacă user-ul curent are drepturi de admin
    current_user = User.query.get(session['user_id'])
    if not current_user or not current_user.is_admin:
        return "Acces interzis! Trebuie să fii administrator pentru a vedea această pagină.", 403

    # 3. Luăm toți utilizatorii din baza de date Aiven
    all_users = User.query.all()
    # Numărăm câte melodii avem salvate în total
    total_cached_songs = SongCache.query.count()
    
    return render_template('admin.html', users=all_users, total_songs=total_cached_songs)

@app.route('/admin/delete_user/<int:uid>')
def delete_user(uid):
    # Verificare de securitate (să nu șteargă cineva prin URL fără să fie admin)
    current_user = User.query.get(session.get('user_id'))
    if not current_user or not current_user.is_admin:
        return "Neautorizat", 403

    user_to_delete = User.query.get(uid)
    if user_to_delete:
        # Ștergem și prieteniile/rating-urile asociate dacă e cazul (depinde de setup-ul bazei de date)
        db.session.delete(user_to_delete)
        db.session.commit()
    
    return redirect(url_for('admin_panel'))

@app.route('/delete_my_account', methods=['POST'])
def delete_self():
    if 'user_id' not in session:
        return redirect(url_for('login_app'))

    uid = session['user_id']
    user = User.query.get(uid)

    if user:
        # Curățăm tot ce ține de acest user
        Friendship.query.filter((Friendship.user_id == uid) | (Friendship.friend_id == uid)).delete()
        Rating.query.filter_by(user_id=uid).delete()
        
        db.session.delete(user)
        db.session.commit()
        session.clear() # Foarte important: scoatem user-ul din sesiune
        return render_template('account_deleted.html')
    
    return "Eroare la ștergere", 404

if __name__ == '__main__':
    with app.app_context():
        #db.drop_all() # rulează o dată dacă schimbi structura tabelelor
        db.create_all() # asta forteaza crearea tabelelor la pornire
    app.run(debug=True)