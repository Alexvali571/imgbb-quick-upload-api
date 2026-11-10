# ImgBB Quick Upload – server public (FastAPI)

Acesta este serverul intermediar pentru extensia Chrome. Cheia ImgBB rămâne pe server și nu este inclusă în extensie.

## Publicare gratuită pe Render

1. Creează un repository GitHub nou, de exemplu `imgbb-quick-upload-api`.
2. Încarcă în repository fișierele din acest folder: `main.py`, `requirements.txt` și `render.yaml`.
3. În Render, alege **New + → Blueprint** și conectează repository-ul.
4. Render va detecta `render.yaml` și va crea serviciul.
5. În setările serviciului, la **Environment**, adaugă `IMGBB_API_KEY` cu cheia API ImgBB. Nu o publica în GitHub și nu o trimite în extensie.
6. Așteaptă finalizarea publicării și verifică adresa serviciului, de exemplu `https://numele-serviciului.onrender.com/health`.
7. Răspunsul de la `/health` trebuie să conțină `{"status":"ok","api_key_configured":true}`.

## Endpoint-uri

- `GET /health` – verifică dacă serverul funcționează și dacă variabila API este configurată.
- `POST /upload` – primește un fișier multipart cu numele câmpului `image` și îl transmite către ImgBB.

Răspunsul reușit are forma:
```json
{"success": true, "data": {"url": "https://i.ibb.co/..."}}
```

## Limite și securitate

- Maximum 32 MB pentru fiecare imagine.
- Sunt acceptate formate imagine uzuale.
- Limitare temporară de 8 cereri/minut/IP (în memoria procesului).
- Cheia ImgBB este citită numai din variabila de mediu `IMGBB_API_KEY`.

**Important:** acesta este un prototip public pentru testare. Limitarea de trafic este în memoria serverului și se resetează la repornire; nu este o protecție puternică împotriva abuzului distribuit. Înainte de distribuirea extensiei către foarte mulți utilizatori, adăugăm protecție persistentă, cote globale și eventual autentificare/anti-abuz. Planul gratuit Render poate opri serviciul după inactivitate, iar prima cerere ulterioară poate porni mai lent.
