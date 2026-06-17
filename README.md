# CONNECTIFY
# 🎵 Connectify — Platformă Inteligentă de Analiză și Compatibilitate Muzicală

**Connectify** este o aplicație web avansată concepută pentru maparea, compararea și analiza profundă a preferințelor muzicale dintre utilizatori. Prin integrarea directă cu **Spotify API**, platforma extrage în timp real date despre istoricul de ascultare, topurile personale de piese/artiști și permite utilizatorilor să își evalueze melodiile preferate. Punctul forte al aplicației îl reprezintă motorul său analitic bazat pe **Inteligență Artificială (LLMs via OpenRouter)**, acționând prin microservicii deterministe care stabilesc indici de compatibilitate interpersonală și generează recomandări muzicale de înaltă fidelitate, izolate de zgomotul conversațional tradițional.

[![Python](https://img.shields.io/badge/Python-3.10%2B-blue.svg)](https://www.python.org)
[![Flask](https://img.shields.io/badge/Flask-3.0%2B-green.svg)](https://flask.palletsprojects.com/)
[![PostgreSQL](https://img.shields.io/badge/PostgreSQL-Aiven%20Cloud-blue.svg)](https://aiven.io/)
[![CI/CD](https://github.com/workflows/python-tests.yml/badge.svg)](#-6-asigurarea-calității-testare-automată--cicd)



## 🗺️ Cuprins
1. [Arhitectura Sistemului & Stack Tehnologic](#-1-arhitectura-sistemului--stack-tehnologic)
2. [Implementarea Agenților AI & Ingineria Prompt-urilor (Prompt Engineering)](#-2-implementarea-agenților-ai--ingineria-prompt-urilor-prompt-engineering)
3. [Design Patterns & Principii de Proiectare](#-3-design-patterns--principii-de-proiectare)
4. [Metodologia de Dezvoltare & Source Control (Git)](#-4-metodologia-de-dezvoltare--source-control-git)
5. [Modelarea Datelor & Diagrame UML](#-5-modelarea-datelor--diagrame-uml)
6. [Asigurarea Calității: Testare Automată & CI/CD](#-6-asigurarea-calității-testare-automată--cicd)
7. [Managementul Defectelor (Bug Tracking) & Soluționare](#-7-managementul-defectelor-bug-tracking--soluționare)
8. [Ghid Complet de Instalare și Configurare (Setup)](#-8-ghid-complet-de-instalare-și-configurare-setup)
9. [Raport de Integrare a Ecosistemului AI în Ciclul de Viață al Dezvoltării](#-9-raport-de-integrare-a-ecosistemului-ai-în-ciclul-de-viață-al-dezvoltării)

---

## 🏗️ 1. Arhitectura Sistemului & Stack Tehnologic

Aplicația Connectify utilizează o arhitectură decuplată, optimizată pentru a asigura latențe minime și consistență tranzacțională:

* **Backend Framework (Microarhitectură Agilă):** S-a optat pentru **Flask** în detrimentul unor soluții monolitice rigide precum Django. Această alegere strategică a facilitat o implementare curată a rutelor personalizate de interogare, eliminând overhead-ul generat de componente neutilizate și scăzând timpul de răspuns la request-urile asincrone.
* **Stratul de Persistență & ORM:** Maparea obiectual-relațională este realizată prin **Flask-SQLAlchemy**. Datele sunt stocate într-un cluster administrat cloud **PostgreSQL** pe platforma **Aiven**, garantând disponibilitate ridicată. Conectivitatea nativă este asigurată de driverul robust `psycopg2-binary`.
* **Integrarea API Terț (Spotify):** Consumul de date muzicale se realizează prin SDK-ul oficial `spotipy`. Autentificarea și autorizarea utilizatorilor urmează fluxul securizat **OAuth 2.0** (`SpotifyOAuth`), implementând reîmprospătarea automată (*access token refresh*) stocată direct și criptat în sesiunea securizată Flask.
* **Consumul LLM externalizat:** Rutarea interogărilor AI se face prin **OpenRouter client API**, permițând comutarea dinamică între diverse modele LLM (cum ar fi `openrouter/free` sau variante mai dense) fără a modifica codul sursă de bază.

---

## 🤖 2. Implementarea Agenților AI & Ingineria Prompt-urilor (Prompt Engineering)

Pentru modulele inteligente din Connectify, s-au proiectat arhitecturi de prompt-uri de sistem stricte care obligă modelele generative să se comporte ca microservicii deterministe, eliminând complet textul conversațional adiacent (salutări, explicații introductive sau concluzii):

### A. Agentul pentru Recomandări Muzicale (`/recomandari`)
* **Rol:** Generează exact 3 piese noi adaptate profilului utilizatorului.
* **Mecanism:** Analizează datele din cache ale utilizatorului curent (melodii evaluate cu 4 sau 5 stele, corelate cu topurile interne furnizate de Spotify).
* **Prompt Engineering Strategy:** Modelul primește un *System Prompt* restrictiv ce impune returnarea exclusivă a unui string brut delimitat prin token-ul structural `|||`.
    * *Exemplu format așteptat:* `NumePiesa1 - Artist1|||NumePiesa2 - Artist2|||NumePiesa3 - Artist3`
    * *Avantaj:* Permite parsarea sigură, liniară în backend, transformând output-ul generativ direct în instanțe de obiecte Python, fără riscuri de erori sintactice.

### B. Agentul pentru Compatibilitate Interpersonală (`/compatibilitate/<friend_id>`)
* **Rol:** Evaluează intersecția gusturilor muzicale dintre doi utilizatori conectați.
* **Mecanism:** Extrage listele matematice suprapuse ale topurilor de artiști și genuri muzicale stocate pentru ambii utilizatori.
* **Prompt Engineering Strategy:** Forțează modelul LLM să se comporte ca un parser strict de date, constrâns să întoarcă exclusiv un obiect valid **JSON** structurat pe chei fixe.
* **Structura Strictă JSON:**
    ```json
    {
      "procent": 87,
      "titlu_vibe": "Sintetizatoare Melancolice și Cyberpunk",
      "artisti_finali": ["Depeche Mode", "The Weeknd", "Kavinsky"]
    }
    ```
    Această rigoare structurală garantează asimilarea imediată și randarea nativă în front-end-ul aplicației.

---

## 🎨 3. Design Patterns & Principii de Proiectare

Pentru a respecta bunele practici de inginerie software și pentru a preveni degradarea performanței prin scurgeri de resurse, s-a implementat pattern-ul structural **Singleton**:

* **Problema abordată:** În medii web asincrone sau multi-threaded, inițializarea repetată a instanțelor ORM sau deschiderea de conexiuni multiple simultane către clusterul Aiven PostgreSQL poate epuiza pool-ul de conexiuni permis de baza de date cloud.
* **Soluția implementată:** Clasa `DatabaseSingleton` (localizată în nucleul `app.py`) încapsulează instanțierea conexiunii SQLAlchemy. Aceasta verifică existența unei conexiuni active înainte de a genera una nouă, asigurând un punct unic de acces global pe parcursul ciclului de viață al aplicației Flask.

```python
# Model conceptual de implementare Singleton pentru conexiune
class DatabaseSingleton:
    _instance = None

    @classmethod
    def get_instance(cls, app=None):
        if cls._instance is None:
            if app is None:
                raise ValueError("Aplicația Flask trebuie furnizată la prima inițializare.")
            from flask_sqlalchemy import SQLAlchemy
            cls._instance = SQLAlchemy(app)
        return cls._instance

```

---

## 🌿 4. Metodologia de Dezvoltare & Source Control (Git)

Proiectul a fost dezvoltat respectând rigorile metodologiilor agile de dezvoltare iterativă, având la bază un backlog granular de funcționalități (User Stories).

* **Managementul Ramurilor (Branching Policy):** S-a evitat complet lucrul direct pe ramura principală (`main`). Dezvoltarea s-a segmentat pe branch-uri dedicate:
* `feature/autentificare-spotify` — implementarea fluxului securizat OAuth 2.0.
* `feature/integrare-agenti-ai` — definirea prompt-urilor și configurarea OpenRouter.
* `feature/baza-de-date-postgres` — maparea modelelor prin ORM și migrarea pe Aiven Cloud.
* `feature/interfata-utilizator` — scrierea șabloanelor HTML și stilizarea CSS.


* **Integrarea Codului:** Reunirea ramurilor s-a realizat prin **Pull Requests (PRs)** în urma procesului de Code Review. Conflictele au fost rezolvate local prin proceduri curate de `merge` și `rebase`.
* **Contribuție:** Proiectul numără un istoric dens de versiuni, respectând cerința minimă de **5 commit-uri atomice și descriptive per student implicat**.

---

## 📊 5. Modelarea Datelor & Diagrame UML

Toate deciziile de modelare structurală sunt reflectate în diagramele stocate în directorul `/diagrame` (sau sub-directoarele aferente):

1. **Use Case Diagram (`UML diagrame/Use case Connectify (1).png`):** Detaliază granițele sistemului și interacțiunile actorilor principali (Vizitator Web, Utilizator Înregistrat via Spotify, Administrator) cu modulele aplicației.
2. **Entity-Relationship Diagram / ERD (`diagrame/diagrama_erd/diagramaER_updated.png`):** Definește structura bazei de date. Tabelele principale includ:
* `User`: Stochează metadatele unice Spotify ID, token-urile de sesiune și profilul de bază.
* `SongCache`: Memorează temporar metadatele pieselor preluate din API-ul Spotify pentru a reduce numărul de apeluri externe API și a preveni fenomenul de Rate Limiting.
* `Rating`: Asociază utilizatorii cu scorurile acordate pieselor (scara 1-5 stele).
* `Friendship`: Tabel de asociere auto-referențial (*self-referential many-to-many*) ce implementează stările relațiilor de prietenie (Pending, Accepted).


3. **Flowchart & AI Flow:** Documentează vizual fluxul execuției codului din momentul trimiterii cererii de compatibilitate până la obținerea și parsarea răspunsului generativ furnizat de LLM.
### 🏗️ Descrierea Arhitecturii și Diagrame
* **Backend Arhitectură**: Python + Flask. Baza de date este un cluster **PostgreSQL** găzduit pe AivenCloud, mapat prin ORM-ul SQLAlchemy.
* **Componente API**: `Spotipy` pentru integrarea fluxului de date muzicale și `OpenAI client` pentru integrarea LLM-urilor din OpenRouter.
* **Diagrame UML furnizate în repository**:
  * **Use Case Diagram**: Detaliază interacțiunile actorilor (Web User, Registered User, Admin) cu sistemul (`UML diagrame/Use case Connectify (1).png`).
  
  * **Entity-Relationship Diagram (ERD)**: Prezintă structura și relațiile tabelelor `User`, `SongCache`, `Rating`, `Friendship`, etc. 
  
```mermaid
%%{init: {'theme': 'base', 'themeVariables': { 'primaryColor': '#FF1493', 'primaryTextColor': '#000000', 'primaryBorderColor': '#000000', 'lineColor': '#000000', 'tertiaryColor': '#FF69B4', 'tertiaryTextColor': '#000000'}}}%%
erDiagram
    User ||--o{ Rating : "are"
    SongCache ||--o{ Rating : "primeste"
    User ||--o{ Friendship : "trimite/primeste"
    User ||--o{ UserTopSong : "asculta"
    SongCache ||--o{ UserTopSong : "este in top"
    User ||--o{ UserTopArtist : "asculta"
    ArtistCache ||--o{ UserTopArtist : "este in top"

    User {
        integer id PK
        boolean is_admin
        varchar email
        varchar password_hash
        varchar spotify_id
        varchar display_name
    }
    SongCache {
        varchar spotify_id PK
        varchar name
        varchar artist
        varchar image_url
    }
    ArtistCache {
        varchar spotify_id PK
        varchar name
        varchar image_url
    }
    Rating {
        integer id PK
        integer score
        varchar comment
        integer user_id FK
        varchar spotify_item_id FK
    }
    Friendship {
        integer id PK
        varchar status
        integer user_id FK
        integer friend_id FK
    }
    UserTopSong {
        integer id PK
        integer user_id FK
        varchar spotify_id FK
    }
    UserTopArtist {
        integer id PK
        integer user_id FK
        varchar spotify_id FK
    }
Flowchart / AI Flow: Descrie fluxul logic al aplicației și arhitectura de prelucrare AI pentru modulul de compatibilitate.

Fragment de cod
graph TD
    A([Start: Click 'Vezi Compatibilitate']) --> B[Backend Flask: Preia UserID & FriendID]
    B --> C[(PostgreSQL Aiven: Extrage Top Artiști și Piese)]
    C --> D{Date suficiente?}
    
    D -- Nu --> E[Afișare Eroare: Date Insuficiente] --> Z([Stop])
    D -- Da --> F[Intersectare matematică a gusturilor muzicale]
    
    F --> G[Construire System Prompt strict JSON]
    G --> H((Apel API: OpenRouter LLM))
    
    H --> I{Răspunsul AI este JSON valid?}
    
    I -- Nu --> J[Aplicare Fallback: RegEx pentru izolare/curățare JSON]
    J --> K[Parsare Obiect JSON]
    I -- Da --> K
    
    K --> L[Trimite datele structurate către Frontend]
    L --> M[Afișare Vibe Comun și Procentaj în Interfață]
    M --> Z([Stop])

    classDef backend fill:#fbcfe8,stroke:#9d174d,stroke-width:2px,color:#000;
    classDef database fill:#fdf2f8,stroke:#db2777,stroke-width:2px,color:#000;
    classDef ai fill:#f9a8d4,stroke:#831843,stroke-width:2px,color:#000;
    classDef startstop fill:#fce7f3,stroke:#be185d,stroke-width:2px,color:#000;
    
    class A,Z startstop;
    class B,F,G,J,K,L backend;
    class C database;
    class H ai;
---

## 🧪 6. Asigurarea Calității: Testare Automată & CI/CD

Validarea stabilității codului este realizată printr-o suită extinsă de teste automate localizate în `teste_unitest.py`, utilizând framework-ul nativ din Python `unittest`.

### Suitele de Testare includ:

* **Validarea regulilor de integritate:** Testarea mecanismelor de securitate și consistență a sesiunilor.
* **Logica de Business:** Verificarea constrângerilor logice critice (de exemplu, validarea faptului că un utilizator primește eroare dacă încearcă să își trimită o cerere de prietenie lui însuși sau să își autoevalueze listele în modul comparativ).
* **Testarea Pattern-urilor:** Verificarea riguroasă a comportamentului instanței unice `DatabaseSingleton`.

### Fluxul de Integrare Continuă (CI):

Automatizarea testelor este orchestrată prin **GitHub Actions**. Fișierul de configurare `.github/workflows/python-tests.yml` rulează la fiecare eveniment de `push` sau `pull_request` pe ramura `main`:

1. Instanțiază un container izolat cu mediul Python corespunzător.
2. Instalează dependențele din `requirements.txt`.
3. Execută suita din `teste_unitest.py`. O blocare a testelor previne fuzionarea codului defect în ramura stabilă.

---

## 🐛 7. Managementul Defectelor (Bug Tracking) & Soluționare

Urmărirea problemelor tehnice s-a realizat prin intermediul **GitHub Issues**. Pe parcursul ciclului de dezvoltare, cele mai mari provocări tehnice identificate și rezolvate au fost:

* **Problema de Stocasticitate AI (JSON Invalid):** LLM-ul genera uneori text adiacent sau formata greșit obiectul JSON la endpoint-ul `/compatibilitate`.
* *Rezolvare:* S-a implementat o arhitectură defensivă în backend utilizând expresii regulate (`re`) pentru izolarea blocului JSON și un mecanism de tip *fallback* (try-except extins) care reîncearcă interogarea sau structurează un răspuns standard în caz de eșec critic de parsare.


* **Rate Limiting Spotify API:** Interogările repetate pentru aceiași artiști încetineau aplicația.
* *Rezolvare:* Extinderea tabelului `SongCache` și stocarea locală a răspunsurilor pe o perioadă determinată de timp (*Time-To-Live* conceptual).


## 🧠 8. Raport de Integrare a Ecosistemului AI în Ciclul de Viață al Dezvoltării

Procesul de inginerie software din cadrul proiectului **Connectify** a fost accelerat prin integrarea metodologiilor bazate pe Modele de Limbaj Mari (LLMs), utilizând asistenți AI avansați (cum ar fi ecosistemul Gemini, ChatGPT sau Claude) pe post de consultant arhitectural și partener de programare (*Pair Programmer*). Acest flux de lucru a adus o valoare adăugată directă în toate etapele:

* **Consultanță de Înaltă Viteză în Selectia Stack-ului:** AI-ul a funcționat ca un motor decizional pentru alegerea microframework-ului Flask (optimizând rutele față de structura rigidă Django), implementarea driverului `psycopg2-binary` pentru PostgreSQL și orchestrarea parametrilor de reîmprospătare a token-urilor în `spotipy`.
* **Generare de Cod de Tip Boilerplate:** S-a eliminat timpul consumat cu sarcini repetitive prin generarea structurilor CSS flexibile și responsive pentru interfețele de autentificare (`login+signup.css`) și panoul principal (`style.css`).
* **Suport în Proiectarea Testelor și CI/CD:** Asistenții AI au ghidat scrierea structurii YAML pentru GitHub Actions, depanarea sintaxelor specifice runner-elor virtuale și definirea metodelor de aserțiune pentru instanțele de tip Singleton.
* **Dezvoltare Defensivă:** AI-ul a contribuit activ la conceperea algoritmilor de fallback și a expresiilor regulate utilizate pentru curățarea string-urilor primite de la rețelele neuronale generative, crescând reziliența generală a software-ului la fenomene de halucinație.

* ---

## ⚙️ 8. Ghid Complet de Instalare și Configurare (Setup)

Urmați pașii de mai jos pentru a rula aplicația Connectify în mediu de dezvoltare local:

### Pasul 1: Clonarea Repository-ului

```bash
git clone <url-repository>
cd CONNECTIFY

```

### Pasul 2: Configurarea Mediului Virtual Python

```bash
# Crearea mediului virtual
python -m venv venv

# Activarea mediului virtual
# Pe Linux/macOS:
source venv/bin/activate
# Pe Windows (CMD):
venv\Scripts\activate
# Pe Windows (PowerShell):
.\venv\Scripts\Activate.ps1

```

### Pasul 3: Instalarea Dependențelor

```bash
pip install -r requirements.txt

```

### Pasul 4: Configurarea Variabilelor de Mediu

Creați un fișier numit `.env` în rădăcina proiectului și definiți următoarele variabile cu datele preluate din Dashboard-ul Spotify Developer și consola OpenRouter / Aiven Cloud:

```env
FLASK_APP=app.py
FLASK_ENV=development
SECRET_KEY=o_cheie_secreta_pentru_sesiuni_flask

# Configurații Spotify API
SPOTIPY_CLIENT_ID=constructor_client_id_de_la_spotify
SPOTIPY_CLIENT_SECRET=constructor_client_secret_de_la_spotify
SPOTIPY_REDIRECT_URI=http://localhost:5000/callback

# Configurație Cloud Database (Aiven PostgreSQL)
DATABASE_URL=postgresql://user:password@host:port/dbname?sslmode=require

# Configurație OpenRouter API Key pentru Agenții AI
OPENROUTER_API_KEY=sk-or-v1-cheia_ta_de_acces_openrouter

```

### Pasul 5: Inițializarea Bazei de Date & Rularea Aplicației

```bash
# Executarea suitei de teste pentru asigurarea integrității
python -m unittest teste_unitest.py

# Pornirea serverului local de dezvoltare
flask run

```

Aplicația va fi accesibilă la adresa: `http://localhost:5000`

---
Ne bucurăm că ați decis să folosiți aplicația noastră!<3

```

```
