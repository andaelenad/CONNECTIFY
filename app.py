import os
from flask import Flask, request, url_for, session, redirect
import spotipy
from spotipy.oauth2 import SpotifyOAuth
from dotenv import load_dotenv

# Încărcăm variabilele din fișierul .env (Client ID și Secret)
load_dotenv()

app = Flask(__name__)

# O cheie random pentru a securiza sesiunea (cookie-urile)
app.secret_key = "cheie_secreta_pentru_proiect_connectify"
app.config['SESSION_COOKIE_NAME'] = 'Connectify_Session'

# Configurarea obiectului de autentificare OAuth2
def create_spotify_oauth():
    return SpotifyOAuth(
        client_id=os.getenv('SPOTIPY_CLIENT_ID'),
        client_secret=os.getenv('SPOTIPY_CLIENT_SECRET'),
        redirect_uri=os.getenv('SPOTIPY_REDIRECT_URI'),
        # user-top-read ne dă voie să vedem topul pieselor ascultate
        scope="user-top-read"
    )

# 1. RUTA PRINCIPALĂ: Trimite utilizatorul la pagina de login Spotify
@app.route('/')
def login():
    sp_oauth = create_spotify_oauth()
    auth_url = sp_oauth.get_authorize_url()
    return f'''
        <h1>Bine ai venit la Connectify!</h1>
        <p>Apasă butonul de mai jos pentru a-ți sincroniza gusturile muzicale.</p>
        <a href="{auth_url}" style="padding: 10px 20px; background-color: #1DB954; color: white; text-decoration: none; border-radius: 20px;">
            Loghează-te cu Spotify
        </a>
    '''

# 2. RUTA CALLBACK: Unde se întoarce Spotify cu codul de acces
@app.route('/callback')
def callback():
    sp_oauth = create_spotify_oauth()
    session.clear()
    code = request.args.get('code')
    
    # Transformăm codul primit de la Spotify într-un Token de acces
    token_info = sp_oauth.get_access_token(code)
    session["token_info"] = token_info
    
    return redirect(url_for("get_tracks", _external=True))

# 3. RUTA DE TEST: Afișează top 5 piese ale utilizatorului
@app.route('/get_tracks')
def get_tracks():
    token_info = session.get('token_info', None)
    if not token_info:
        return redirect('/')
    
    sp = spotipy.Spotify(auth=token_info['access_token'])
    
    # Interogăm API-ul Spotify pentru topul personal
    results = sp.current_user_top_tracks(limit=5, time_range='short_term')
    
    output = "<h2>Top 5 piese găsite pe contul tău:</h2><ul>"
    for track in results['items']:
        output += f"<li><strong>{track['name']}</strong> - {track['artists'][0]['name']}</li>"
    output += "</ul><br><a href='/'>Înapoi</a>"
    
    return output

if __name__ == '__main__':
    # Rulăm serverul pe portul 5000 (standard Flask)
    app.run(debug=True)