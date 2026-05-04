import os
# AM ADĂUGAT render_template AICI
from flask import Flask, request, url_for, session, redirect, render_template 
import spotipy
from spotipy.oauth2 import SpotifyOAuth
from dotenv import load_dotenv

load_dotenv()

app = Flask(__name__)

app.secret_key = "cheie_secreta_pentru_proiect_connectify"
app.config['SESSION_COOKIE_NAME'] = 'Connectify_Session'

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
    # DOAR ASTA RĂMÂNE: trimite la index.html
    return render_template('index.html', auth_url=auth_url)

# 2. RUTA CALLBACK
@app.route('/callback')
def callback():
    sp_oauth = create_spotify_oauth()
    session.clear()
    code = request.args.get('code')
    token_info = sp_oauth.get_access_token(code)
    session["token_info"] = token_info
    return redirect(url_for("get_tracks", _external=True))

# 3. RUTA PROFIL (fosta get_tracks)
@app.route('/get_tracks')
def get_tracks():
    token_info = session.get('token_info', None)
    if not token_info:
        return redirect('/')
    
    sp = spotipy.Spotify(auth=token_info['access_token'])
    results = sp.current_user_top_tracks(limit=5, time_range='short_term')
    
    # Aici, în loc de output += ..., trimitem datele către profil.html
    tracks = results['items']
    return render_template('profile.html', tracks=tracks)

if __name__ == '__main__':
    app.run(debug=True)