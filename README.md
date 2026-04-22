# CityVoice

`CityVoice` is a local web platform where residents can report city problems, publish petitions, and support initiatives by voting.

## Authors

GitHub repository:

- `https://github.com/askarsltv17/CityVoice.git`

## Stack

- Frontend: `HTML`, `CSS`, `JavaScript`
- Backend: `Python`, `Flask`
- Database: `PostgreSQL`

## Main Features

- user registration and login
- complaints publishing
- petitions creation and voting
- admin status updates for complaints and petitions
- notifications
- password reset by email

## Project Structure

- `app.py` - Flask server and API
- `db.py` - PostgreSQL connection, schema setup, and legacy SQLite migration
- `templates/index.html` - main UI template
- `static/styles.css` - styles and responsive layout
- `static/script.js` - frontend logic
- `start.ps1` - Windows startup script
- `requirements.txt` - Python dependencies
- `.env.example` - environment variables example
- `help.md` - detailed launch guide

## Quick Start

You need to install separately:

- `Python 3.13`
- `PostgreSQL`

Before launch, make sure PostgreSQL is already installed and running.

Then run:

```powershell
.\start.ps1
```

Open in browser:

```text
http://127.0.0.1:5000
```

`start.ps1` will automatically:

- create `.venv` if needed
- install dependencies from `requirements.txt`
- start the application

## Database

The app now uses `PostgreSQL` as the main runtime database.

- connection is configured through `CITYVOICE_DATABASE_URL` or PostgreSQL variables in `.env`
- on first launch, old data from `cityvoice.db` can be migrated automatically if that file exists
- user scenarios stay the same: registration, login, demo accounts, complaints, petitions, notifications, and password reset

Example connection from `.env.example`:

```env
CITYVOICE_DATABASE_URL=postgresql://postgres:postgres@127.0.0.1:5432/cityvoice
```

## Demo Accounts

Demo user:

- email: `aidana@example.com`
- password: `user123`

Admin:

- email: `admin@cityvoice.local`
- password: `admin123`

## Password Reset

Password reset works through email.

If SMTP is configured, the app sends a reset link to the user.
If SMTP is not configured, the reset link is still printed in the server console for local development.

## Notes

- `Docker` is not required for this version
- `.env` is ignored by git and should not be pushed with real secrets
- for a more detailed launch guide, see `help.md`
