import os
from flask import Flask, request, url_for, session, redirect, render_template 
import spotipy
from spotipy.oauth2 import SpotifyOAuth
from dotenv import load_dotenv
from flask_sqlalchemy import SQLAlchemy 

load_dotenv()

app = Flask(__name__)

app.secret_key = "cheie_secreta_pentru_proiect_connectify"
app.config['SESSION_COOKIE_NAME'] = 'Connectify_Session'

# --- CONFIGURARE BAZĂ DE DATE (AIVEN) ---
# Aici înlocuiești cu Service URI-ul tău de pe Aiven
# Am adăugat "postgresql" în loc de "postgres" pentru compatibilitate
app.config['SQLALCHEMY_DATABASE_URI'] = "postgresql://avnadmin:AVNS_dlwEpYk7NtFpIKxzuWF@pg-6647a18-rurig.d.aivencloud.com:26923/defaultdb?sslmode=require"
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

db = SQLAlchemy(app)

# clase pt db
class User(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    spotify_id = db.Column(db.String(100), unique=True, nullable=False)
    display_name = db.Column(db.String(100))
    ratings = db.relationship('Rating', backref='user', lazy=True)

class SongCache(db.Model):
    spotify_id = db.Column(db.String(100), primary_key=True) 
    name = db.Column(db.String(200), nullable=False)
    artist = db.Column(db.String(200))
    image_url = db.Column(db.String(500))
    ratings = db.relationship('Rating', backref='song', lazy=True)

class Rating(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    score = db.Column(db.Integer, nullable=False) 
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    spotify_item_id = db.Column(db.String(100), db.ForeignKey('song_cache.spotify_id'), nullable=False)

class Friendship(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    friend_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    status = db.Column(db.String(20), default='pending')

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

# 1. RUTA PRINCIPALĂ
@app.route('/')
def login():
    sp_oauth = create_spotify_oauth()
    auth_url = sp_oauth.get_authorize_url()
    return render_template('index.html', auth_url=auth_url)

# 2. RUTA CALLBACK
@app.route('/callback')
def callback():
    sp_oauth = create_spotify_oauth()
    session.clear()
    code = request.args.get('code')
    token_info = sp_oauth.get_access_token(code)
    session["token_info"] = token_info

    sp = spotipy.Spotify(auth=token_info['access_token'])
    spotify_user = sp.current_user()

    existing_user = User.query.filter_by(spotify_id=spotify_user['id']).first()
    if not existing_user:
        new_user = User(spotify_id=spotify_user['id'], display_name=spotify_user['display_name'])
        db.session.add(new_user)
        db.session.commit()
        print("Am salvat un user nou!")

    return redirect(url_for("get_tracks", _external=True))

# 3. RUTA PROFIL 
@app.route('/get_tracks')
def get_tracks():
    token_info = get_token()
    if not token_info:
        return redirect('/')
    
    sp = spotipy.Spotify(auth=token_info['access_token'])
    results = sp.current_user_top_tracks(limit=5, time_range='short_term')
    
    tracks = results['items']
    return render_template('profile.html', tracks=tracks)

@app.route('/search_users', methods=['GET', 'POST'])
def search_users():
    query = request.args.get('query')
    users = []
    if query:
        token_info = get_token()
        if not token_info: return redirect('/')
        
        sp = spotipy.Spotify(auth=token_info['access_token'])
        me = sp.current_user()
        
        users = User.query.filter(User.display_name.contains(query), User.spotify_id != me['id']).all()
    
    return render_template('search_users.html', users=users)

@app.route('/add_friend/<int:friend_id>')
def add_friend(friend_id):
    token_info = get_token()
    if not token_info: return redirect('/')
    
    sp = spotipy.Spotify(auth=token_info['access_token'])
    me_spotify = sp.current_user()
    me_db = User.query.filter_by(spotify_id=me_spotify['id']).first()

    if not me_db: return redirect('/')

    exists = Friendship.query.filter_by(user_id=me_db.id, friend_id=friend_id).first()
    if not exists:
        new_friendship = Friendship(user_id=me_db.id, friend_id=friend_id, status='pending')
        db.session.add(new_friendship)
        db.session.commit()
    
    return redirect(url_for('search_users'))

@app.route('/requests')
def view_requests():
    token_info = get_token()
    if not token_info: return redirect('/')

    sp = spotipy.Spotify(auth=token_info['access_token'])
    me_spotify = sp.current_user()
    me_db = User.query.filter_by(spotify_id=me_spotify['id']).first()

    if not me_db: return redirect('/')

    pending_requests = Friendship.query.filter_by(friend_id=me_db.id, status='pending').all()
    requesters = [User.query.get(req.user_id) for req in pending_requests]
    
    return render_template('requests.html', requesters=requesters)

@app.route('/accept_friend/<int:requester_id>')
def accept_friend(requester_id):
    token_info = get_token()
    if not token_info: return redirect('/')

    sp = spotipy.Spotify(auth=token_info['access_token'])
    me_spotify = sp.current_user()
    me_db = User.query.filter_by(spotify_id=me_spotify['id']).first()

    friendship = Friendship.query.filter_by(user_id=requester_id, friend_id=me_db.id, status='pending').first()
    if friendship:
        friendship.status = 'accepted'
        db.session.commit()
    
    return redirect(url_for('view_requests'))

if __name__ == '__main__':
    with app.app_context():
        # Această linie va crea tabelele pe Aiven automat la pornire
        db.create_all() 
    app.run(debug=True)