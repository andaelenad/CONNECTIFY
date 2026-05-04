import os
# AM ADAUGAT render_template AICI
from flask import Flask, request, url_for, session, redirect, render_template 
import spotipy
from spotipy.oauth2 import SpotifyOAuth
from dotenv import load_dotenv
from flask_sqlalchemy import SQLAlchemy # pt baza de date

load_dotenv()

app = Flask(__name__)

app.secret_key = "cheie_secreta_pentru_proiect_connectify"
app.config['SESSION_COOKIE_NAME'] = 'Connectify_Session'

# configurări pt baza de date
basedir = os.path.abspath(os.path.dirname(__file__))
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///' + os.path.join(basedir, 'connectify.db')
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

db = SQLAlchemy(app)

# clase pt db
class User(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    spotify_id = db.Column(db.String(100), unique=True, nullable=False)
    display_name = db.Column(db.String(100))
    # legatura cu rating-uri
    ratings = db.relationship('Rating', backref='user', lazy=True)

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

# 1. RUTA PRINCIPALĂ
@app.route('/')
def login():
    sp_oauth = create_spotify_oauth()
    auth_url = sp_oauth.get_authorize_url()
    # trimite la index.html
    return render_template('index.html', auth_url=auth_url)

# 2. RUTA CALLBACK
@app.route('/callback')
def callback():
    sp_oauth = create_spotify_oauth()
    session.clear()
    code = request.args.get('code')
    token_info = sp_oauth.get_access_token(code)
    session["token_info"] = token_info

    # aici salvam userul in baza noastra cand se logheaza
    sp = spotipy.Spotify(auth=token_info['access_token'])
    spotify_user = sp.current_user()

    # verificam daca il avem deja in tabel
    existing_user = User.query.filter_by(spotify_id=spotify_user['id']).first()
    if not existing_user:
        # daca e nou, il adaugam acum
        new_user = User(spotify_id=spotify_user['id'], display_name=spotify_user['display_name'])
        db.session.add(new_user)
        db.session.commit()
        print("Am salvat un user nou!")

    return redirect(url_for("get_tracks", _external=True))

# 3. RUTA PROFIL 
@app.route('/get_tracks')
def get_tracks():
    token_info = session.get('token_info', None)
    if not token_info:
        return redirect('/')
    
    sp = spotipy.Spotify(auth=token_info['access_token'])
    results = sp.current_user_top_tracks(limit=5, time_range='short_term')
    
    # trimitem datele catre profil.html
    tracks = results['items']
    return render_template('profile.html', tracks=tracks)

if __name__ == '__main__':
    with app.app_context():
        db.create_all() # Asta fortează crearea tabelelor la pornire
    app.run(debug=True)