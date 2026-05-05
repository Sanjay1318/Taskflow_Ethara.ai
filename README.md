# TaskFlow — Team Task Manager

A full-stack collaborative task management app built with **Flask + SQLite/PostgreSQL**, featuring authentication, role-based access control, and a modern dark-mode UI.

---

## 🚀 Features

### Authentication
- JWT-based signup/login/logout (cookie + header support)
- Password hashing with Werkzeug
- Protected routes via `@jwt_required`

### Projects
- Create, edit, delete projects
- Admin/Member role per project
- Progress tracking with stats (total, done, in-progress, overdue)

### Tasks
- Create/edit/delete tasks with title, description, status, priority, assignee, due date
- 4 statuses: `todo → in_progress → review → done`
- 4 priorities: `low / medium / high / critical`
- Overdue detection
- Task comments
- Kanban board view per project

### Dashboard
- Aggregate stats: total projects, tasks, my tasks, overdue count
- Quick views: my assigned tasks, overdue tasks across all projects

### Role-Based Access Control
| Action | Admin | Member |
|--------|-------|--------|
| Create/Edit/Delete project | ✅ | ❌ |
| Add/Remove members | ✅ | ❌ |
| Change member roles | ✅ | ❌ |
| Create tasks | ✅ | ✅ |
| Edit own tasks | ✅ | ✅ |
| Edit any task | ✅ | ❌ |
| Delete own tasks | ✅ | ✅ |
| Delete any task | ✅ | ❌ |

---

## 🛠 Tech Stack

- **Backend**: Python 3.11+, Flask 3.0
- **Database**: SQLite (dev) / PostgreSQL (Railway)
- **ORM**: SQLAlchemy + Flask-SQLAlchemy
- **Auth**: JWT (Flask-JWT-Extended)
- **CORS**: Flask-CORS
- **Server**: Gunicorn
- **Frontend**: Vanilla JS SPA, served by Flask

---

## ⚙️ Local Development

```bash
# 1. Clone repo
git clone <your-repo-url>
cd taskflow

# 2. Create virtual environment
python -m venv venv
source venv/bin/activate   # Windows: venv\Scripts\activate

# 3. Install dependencies
pip install -r requirements.txt

# 4. Set environment variables
cp .env.example .env
# Edit .env with your SECRET_KEY and JWT_SECRET_KEY

# 5. Run the app
python wsgi.py
# → http://localhost:5000
```

---

## 🌐 Deploy on Railway

### Step 1 — Push to GitHub
```bash
git init
git add .
git commit -m "Initial commit"
git remote add origin https://github.com/YOUR_USERNAME/taskflow.git
git push -u origin main
```

### Step 2 — Create Railway Project
1. Go to [railway.app](https://railway.app) and sign in
2. Click **New Project → Deploy from GitHub repo**
3. Select your `taskflow` repository

### Step 3 — Add PostgreSQL
1. In your Railway project, click **+ New → Database → Add PostgreSQL**
2. Railway auto-injects `DATABASE_URL` into your app

### Step 4 — Set Environment Variables
In Railway project → **Variables**, add:
```
SECRET_KEY=your-super-secret-key-here
JWT_SECRET_KEY=your-jwt-secret-key-here
FLASK_ENV=production
```

### Step 5 — Deploy
Railway auto-deploys on every push. Your app will be live at:
`https://your-app-name.up.railway.app`

---

## 📡 REST API Reference

### Auth
| Method | Endpoint | Description |
|--------|----------|-------------|
| POST | `/api/auth/signup` | Register new user |
| POST | `/api/auth/login` | Login |
| POST | `/api/auth/logout` | Logout |
| GET | `/api/auth/me` | Get current user |

### Projects
| Method | Endpoint | Description |
|--------|----------|-------------|
| GET | `/api/projects` | List user's projects |
| POST | `/api/projects` | Create project |
| GET | `/api/projects/:id` | Get project detail |
| PUT | `/api/projects/:id` | Update project (admin) |
| DELETE | `/api/projects/:id` | Delete project (admin) |

### Members
| Method | Endpoint | Description |
|--------|----------|-------------|
| GET | `/api/projects/:id/members` | List members |
| POST | `/api/projects/:id/members` | Add member (admin) |
| PUT | `/api/projects/:id/members/:uid` | Change role (admin) |
| DELETE | `/api/projects/:id/members/:uid` | Remove member |

### Tasks
| Method | Endpoint | Description |
|--------|----------|-------------|
| GET | `/api/projects/:id/tasks` | List project tasks |
| POST | `/api/projects/:id/tasks` | Create task |
| GET | `/api/tasks/:id` | Get task detail |
| PUT | `/api/tasks/:id` | Update task |
| DELETE | `/api/tasks/:id` | Delete task |
| POST | `/api/tasks/:id/comments` | Add comment |

### Dashboard
| Method | Endpoint | Description |
|--------|----------|-------------|
| GET | `/api/dashboard` | Get dashboard stats & tasks |

---

## 📁 Project Structure

```
taskflow/
├── wsgi.py              # Entry point
├── app.py               # Flask app factory
├── config.py            # Configuration classes
├── models.py            # SQLAlchemy models
├── routes/
│   ├── __init__.py
│   ├── auth.py          # Auth endpoints
│   ├── projects.py      # Project & member endpoints
│   └── tasks.py         # Task, comment & dashboard endpoints
├── templates/
│   └── index.html       # SPA frontend
├── static/              # Static assets
├── requirements.txt
├── Procfile             # Railway/Heroku process file
├── railway.toml         # Railway config
└── .env.example
```

---

## 📝 Database Schema

```
users           → id, name, email, password_hash, created_at
projects        → id, name, description, status, created_at, updated_at
project_members → id, project_id, user_id, role, joined_at
tasks           → id, title, description, status, priority, project_id,
                   assignee_id, creator_id, due_date, created_at, updated_at
comments        → id, content, task_id, user_id, created_at
```
