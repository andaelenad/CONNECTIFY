import os
import json
import ollama
from flask import Flask, request, url_for, session, redirect, render_template, flash
import spotipy
from spotipy.oauth2 import SpotifyOAuth
from dotenv import load_dotenv
from flask_sqlalchemy import SQLAlchemy # pt baza de date
from werkzeug.security import generate_password_hash, check_password_hash
from datetime import timedelta

load_dotenv()

app = Flask(__name__)

app.secret_key = "cheie_secreta_pentru_proiect_connectify"
app.config['SESSION_COOKIE_NAME'] = 'Connectify_Session'

# configurari pt baza de date
# actualizat URI-ul pentru Aiven (PostgreSQL)
app.config['SQLALCHEMY_DATABASE_URI'] = "postgresql://avnadmin:AVNS_dlwEpYk7NtFpIKxzuWF@pg-6647a18-rurig.d.aivencloud.com:26923/defaultdb?sslmode=require"
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

class DatabaseSingleton:
    _instance = None

    def __new__(cls, app=None):
        if cls._instance is None:
            # daca _instance este None, e prima data cand apelam clasa
            cls._instance = SQLAlchemy(app)
        return cls._instance

db = DatabaseSingleton(app)

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
    comment = db.Column(db.String(500), nullable=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    spotify_item_id = db.Column(db.String(100), db.ForeignKey('song_cache.spotify_id'), nullable=False)

class Friendship(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    friend_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    status = db.Column(db.String(20), default='pending') # pending, accepted, rejected

class UserTopSong(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    spotify_id = db.Column(db.String(100), db.ForeignKey('song_cache.spotify_id'), nullable=False)
    
    # relatie pentru a accesa direct detaliile piesei din cache
    song = db.relationship('SongCache', backref='user_tops', lazy=True)

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

        if len(password) < 8:
            flash("Eroare: Parola trebuie să aibă minim 8 caractere!", "danger")
            return render_template('signup.html')
        
        if not any(char.isupper() for char in password):
            flash("Eroare: Parola trebuie să conțină cel puțin o majusculă!", "danger")
            return render_template('signup.html')

        if User.query.filter_by(email=email).first():
            flash("Email-ul există deja!", "warning")
            return render_template('signup.html')

        new_user = User(email=email)
        new_user.set_password(password)
        db.session.add(new_user)
        db.session.commit()
        
        flash("Cont creat cu succes! Te poți loga.", "success")
        if email == "ruricojocaru@gmail.com": 
            new_user.is_admin = True
        if email == "sabinabrinzei277@gmail.com": 
            new_user.is_admin = True

        new_user.set_password(password)
        db.session.add(new_user)
        db.session.commit()
        return redirect(url_for('login_app'))
    return render_template('signup.html')


app.config['PERMANENT_SESSION_LIFETIME'] = timedelta(days=30)
app.config['SESSION_REFRESH_EACH_REQUEST'] = True
app.config['SESSION_COOKIE_SECURE'] = False
app.config['SESSION_COOKIE_SAMESITE'] = 'Lax'

@app.route('/login_app', methods=['GET', 'POST'])
def login_app():
    if request.method == 'POST':
        email = request.form.get('email')
        password = request.form.get('password')
        user = User.query.filter_by(email=email).first()
        if user and user.check_password(password):
            session.permanent = True
            session['user_id'] = user.id
            return redirect(url_for('dashboard'))
        return "Login eșuat!"
    return render_template('login.html')

#dashboard cu top cantece + ratinguri
@app.route('/dashboard')
def dashboard():
    if 'user_id' not in session:
        return redirect(url_for('login_app'))
        
    user = User.query.get(session['user_id'])
    if not user:
        session.clear()
        return redirect(url_for('login_app'))
    
    tracks = []
    token_info = get_token()
    
    # 1. Preluare piese din Spotify live / Cache (Neschimbat)
    if token_info:
        try:
            sp = spotipy.Spotify(auth=token_info['access_token'])
            results = sp.current_user_top_tracks(limit=5, time_range='medium_term')
            tracks = results['items']
            
            if tracks:
                UserTopSong.query.filter_by(user_id=user.id).delete()
                db.session.commit()
                
                for track in tracks:
                    song = SongCache.query.get(track['id'])
                    if not song:
                        song = SongCache(
                            spotify_id=track['id'],
                            name=track['name'],
                            artist=track['artists'][0]['name'],
                            image_url=track['album']['images'][0]['url'] if track['album']['images'] else ''
                        )
                        db.session.add(song)
                        db.session.commit()
                    
                    top_mapping = UserTopSong(user_id=user.id, spotify_id=track['id'])
                    db.session.add(top_mapping)
                db.session.commit()
        except Exception as e:
            print(f"A intervenit o mică eroare la conexiunea live cu Spotify: {e}")

    if not tracks and user.spotify_id:
        top_mappings = UserTopSong.query.filter_by(user_id=user.id).limit(5).all()
        tracks = []
        for m in top_mappings:
            tracks.append({
                'id': m.song.spotify_id,
                'name': m.song.name,
                'artists': [{'name': m.song.artist}],
                'album': {'images': [{'url': m.song.image_url}]}
            })

    ratings = Rating.query.filter_by(user_id=user.id).all()
    user_rated_songs = {r.spotify_item_id: r.score for r in ratings}
    
    ai_tracks_details = []
    tip_sursa = ""
    eroare_ai = None

    high_ratings = Rating.query.filter(Rating.user_id == user.id, Rating.score >= 4).all()
    if high_ratings:
        tip_sursa = "rating-urile tale de top"
        surse_muzica = [f"{r.song.name} - {r.song.artist}" for r in high_ratings if r.song]
    else:
        top_songs = UserTopSong.query.filter_by(user_id=user.id).limit(5).all()
        tip_sursa = "topul tău Spotify"
        surse_muzica = [f"{t.song.name} - {t.song.artist}" for t in top_songs if t.song]

    surse_muzica = list(set(surse_muzica))

    if surse_muzica:
        text_piese = "\n- ".join(surse_muzica)
        
        try:
            # Creăm un client explicit local pentru a evita problemele de mediu virtual
            from ollama import Client
            local_client = Client(host='http://localhost:11434')
            
            response = local_client.chat(
                model='llama3',
                messages=[
                    {
                        'role': 'system',
                        'content': (
                            "Ești un expert muzical genial. Analizează piesele și recomandă exact 3 piese noi, "
                            "diferite ca nume, compatibile ca gen. Returnează doar cele 3 piese, separate prin '|||'. "
                            "Exemplu: Piesă 1 - Artist 1 ||| Piesă 2 - Artist 2 ||| Piesă 3 - Artist 3"
                        )
                    },
                    {
                        'role': 'user',
                        'content': f"Recomandă 3 piese pentru cineva care ascultă:\n{text_piese}"
                    }
                ],
                options={
                    'temperature': 0.8,
                    'top_p': 0.9
                }
            )
            
            text_brut = response['message']['content'].strip()
            
            liste_nume_piese = [piesa.strip() for piesa in text_brut.split('|||') if piesa.strip()]
            
            liste_nume_piese = liste_nume_piese[:3]
            
            if token_info and liste_nume_piese:
                sp = spotipy.Spotify(auth=token_info['access_token'])
                for nume_piesa in liste_nume_piese:
                    # Curățăm eventuale ghilimele rătăcite pe care le mai pune AI-ul
                    nume_curat = nume_piesa.replace('"', '').replace("'", "")
                    search_results = sp.search(q=nume_curat, limit=1, type='track')
                    if search_results['tracks']['items']:
                        ai_tracks_details.append(search_results['tracks']['items'][0])
                        
        except Exception as e:
            print(f"Eroare Ollama Local: {e}")
            eroare_ai = "🤖 Aplicația nu a putut comunica cu modelul AI local. Asigură-te că Ollama rulează în fundal!"

    return render_template('dashboard.html', 
                           user=user, 
                           tracks=tracks, 
                           ratings=ratings, 
                           rated_songs=user_rated_songs, 
                           ai_tracks=ai_tracks_details, 
                           sursa=tip_sursa,
                           eroare_ai=eroare_ai)
    
@app.route('/logout')
def logout():
    session.clear()
    return redirect(url_for('index'))

# 1. RUTA PRINCIPALA
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
    # unde statusul este 'accepted'
    friendships = Friendship.query.filter(
        ((Friendship.user_id == session['user_id']) | (Friendship.friend_id == session['user_id'])),
        (Friendship.status == 'accepted')
    ).all()

    friends_list = []
    for f in friendships:
        if f.user_id == session['user_id']:
            friend = User.query.get(f.friend_id)
        else:
            friend = User.query.get(f.user_id)
        
        if friend:
            friends_list.append(friend)

    return render_template('friends.html', friends=friends_list)

# cautare utilizatori dupa display_name
@app.route('/search_users', methods=['GET', 'POST'])
def search_users():
    query = request.args.get('query')
    users = []
    if query:
        # userul propriu nu apare la cautare
        users = User.query.filter(User.display_name.contains(query), User.id != session.get('user_id')).all()
    
    return render_template('search_users.html', users=users)

# send cerere prietenie
@app.route('/add_friend/<int:friend_id>')
def add_friend(friend_id):
    if 'user_id' not in session: 
        return redirect(url_for('login_app'))
    
   
    if session['user_id'] == friend_id:
        flash("Nu îți poți trimite cerere de prietenie singur!", "danger")
        return redirect(url_for('search_users'))

    
    if 'user_id' not in session: return redirect(url_for('login_app'))
    
    # verificare daca exista relatie deja
    exists = Friendship.query.filter_by(user_id=session['user_id'], friend_id=friend_id).first()
    if not exists:
        new_friendship = Friendship(user_id=session['user_id'], friend_id=friend_id, status='pending')
        db.session.add(new_friendship)
        db.session.commit()
        flash("Cerere de prietenie trimisă!", "success")
    
    return redirect(url_for('search_users'))

@app.route('/requests')
def view_requests():
    if 'user_id' not in session: return redirect(url_for('login_app'))

    # cererile unde ID-ul meu este la "friend_id" (cineva m-a adaugat pe mine)
    pending_requests = Friendship.query.filter_by(friend_id=session['user_id'], status='pending').all()
    # trebuie join manual sau sa cautam userii care au trimis cererea
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
    # verificam daca user-ul este logat
    if 'user_id' not in session:
        return redirect(url_for('login_app'))
    
    # are drept admin?
    current_user = User.query.get(session['user_id'])
    if not current_user or not current_user.is_admin:
        return "Acces interzis! Trebuie să fii administrator pentru a vedea această pagină.", 403

    # toti utilizatorii din baza de date Aiven
    all_users = User.query.all()
    total_cached_songs = SongCache.query.count()
    
    return render_template('admin.html', users=all_users, total_songs=total_cached_songs)

@app.route('/admin/delete_user/<int:uid>')
def delete_user(uid):
    # verificare de securitate (sa nu stearga cineva prin URL fara sa fie admin)
    current_user = User.query.get(session.get('user_id'))
    if not current_user or not current_user.is_admin:
        return "Neautorizat", 403

    user_to_delete = User.query.get(uid)
    if user_to_delete:
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
        # stergem tot ce tine de acest user: prietenii, ratinguri, topuri
        Friendship.query.filter((Friendship.user_id == uid) | (Friendship.friend_id == uid)).delete()
        Rating.query.filter_by(user_id=uid).delete()
        
        db.session.delete(user)
        db.session.commit()
        session.clear() # scoatem user-ul din sesiune
        return render_template('account_deleted.html')
    
    return "Eroare la ștergere", 404

# search cantece
@app.route('/search_songs', methods=['GET'])
def search_songs():
    if 'user_id' not in session:
        return redirect(url_for('login_app'))
    
    query = request.args.get('query')
    tracks = []
    user_rated_songs = {} # dictionar gol implicit

    # extragem rating-urile salvate de utilizatorul curent în baza de date Aiven
    current_user_id = session['user_id']
    ratings = Rating.query.filter_by(user_id=current_user_id).all()
    
    # transformam lista intr-un dictionar pentru cautare rapida în HTML: { id_piesa: nota }
    user_rated_songs = {r.spotify_item_id: r.score for r in ratings}
    
    if query:
        token_info = get_token()
        if not token_info:
            return redirect(url_for('connect_spotify'))
        
        sp = spotipy.Spotify(auth=token_info['access_token'])
        results = sp.search(q=query, limit=10, type='track')
        tracks = results['tracks']['items']
        
    # trimitem si `user_rated_songs` catre template-ul HTML
    return render_template('search_songs.html', tracks=tracks, query=query, rated_songs=user_rated_songs)

# rate la cantece
@app.route('/rate_song', methods=['POST'])
def rate_song():
    if 'user_id' not in session:
        return redirect(url_for('login_app'))
    
    user_id = session['user_id']
    spotify_id = request.form.get('spotify_id')
    name = request.form.get('name')
    artist = request.form.get('artist')
    image_url = request.form.get('image_url')
    score = int(request.form.get('score'))
    comment = request.form.get('comment') 

    # verific/salvez în SongCache
    song = SongCache.query.get(spotify_id)
    if not song:
        song = SongCache(spotify_id=spotify_id, name=name, artist=artist, image_url=image_url)
        db.session.add(song)
        db.session.commit()

    # 2. exista deja review?
    existing_rating = Rating.query.filter_by(user_id=user_id, spotify_item_id=spotify_id).first()
    
    if existing_rating:
        existing_rating.score = score
        existing_rating.comment = comment # update com vechi
        flash(f"Ai actualizat recenzia pentru '{name}'!", "success")
    else:
        # Cream rating nou updatat
        new_rating = Rating(score=score, comment=comment, user_id=user_id, spotify_item_id=spotify_id)
        db.session.add(new_rating)
        flash(f"Ai adăugat o recenzie pentru '{name}'!", "success")
        
    db.session.commit()
    
    query_context = request.form.get('current_query')
    if query_context is not None and query_context != "":
        return redirect(url_for('search_songs', query=query_context))
    else:
        return redirect(url_for('dashboard'))

@app.route('/friend/profile/<int:friend_id>')
def view_friend_profile(friend_id):
    if 'user_id' not in session:
        return redirect(url_for('login_app'))
        
    current_user_id = session['user_id']
    
    # verificare prietenie
    is_friend = Friendship.query.filter(
        ((Friendship.user_id == current_user_id) & (Friendship.friend_id == friend_id)) |
        ((Friendship.user_id == friend_id) & (Friendship.friend_id == current_user_id)),
        Friendship.status == 'accepted'
    ).first()
    
    if not is_friend:
        flash("Nu poți vizualiza profilul unui utilizator care nu îți este prieten!", "danger")
        return redirect(url_for('view_friends'))
         
    friend = User.query.get_or_404(friend_id)
    friend_ratings = Rating.query.filter_by(user_id=friend_id).all()
    friend_comments= Rating.query.filter_by(user_id=friend_id).filter(Rating.comment != None).all()

    # EXTRAGEM STRICT TOPUL SALVAT AL PRIETENULUI
    top_mappings = UserTopSong.query.filter_by(user_id=friend_id).limit(5).all()
    friend_tracks = [m.song for m in top_mappings] # extragem obiectele piese din relatyie

    return render_template('friend_profile.html', friend=friend, ratings=friend_ratings, tracks=friend_tracks)

if __name__ == '__main__':
    with app.app_context():
        #db.drop_all()
        db.create_all()
    app.run(debug=True)