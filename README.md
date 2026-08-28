# UPSC • BPSC • STATE PCS — AI Exam Preparation Platform

An AI-powered preparation platform for **UPSC, BPSC and State PCS** aspirants, built with **FastAPI, React, SQLAlchemy and AI services**.

The platform combines current affairs, MCQ practice, AI-powered answer writing, essay practice, user authentication and paid subscription features into a single preparation ecosystem.

---

## 🚀 Features

### 📰 Current Affairs

* AI-assisted current affairs processing
* UPSC / BPSC / State PCS focused news
* Category-based filtering
* Exam-specific filtering
* Hindi and English support
* Search and pagination
* Current affairs scoring and ranking
* Bihar-focused current affairs support

### 🧠 AI MCQ Practice

* Current-affairs-based MCQs
* UPSC / BPSC focused questions
* Hindi and English support
* Practice mode
* Exam-specific MCQ filtering
* AI-assisted question generation

### ✍️ AI Answer Writing

Dedicated answer-writing practice for competitive examinations.

#### Supported answer lengths

* 150 words
* 250 words

#### Features

* AI-generated questions
* UPSC / BPSC exam selection
* Category selection
* Hindi / English support
* AI model answers
* Answer submission
* AI-based answer evaluation
* Answer submission quota
* Writing history
* Subscription-based access

### 📝 Essay Practice

* AI-generated essays
* Long-form writing practice
* Essay submission
* AI evaluation
* Exam-oriented essay preparation

### 💳 Subscription & Payments

The platform supports paid access using **Razorpay**.

Writing subscription functionality includes:

* Weekly Writing Plan
* Payment order creation
* Payment verification
* Subscription activation
* Subscription expiry
* Answer submission limits
* Remaining-answer tracking
* Payment status tracking

### 🔐 Authentication

* User registration
* Secure password hashing
* JWT authentication
* Protected API endpoints
* User-specific subscriptions
* Protected frontend routes

---

# 🏗️ Project Architecture

```text
UPSC-BPSC-STATEPCS/
│
├── backend/
│   │
│   ├── app/
│   │   ├── dependencies/
│   │   │
│   │   ├── models/
│   │   │   ├── user.py
│   │   │   ├── writing.py
│   │   │   ├── writing_subscription.py
│   │   │   ├── current_affair.py
│   │   │   ├── mcq.py
│   │   │   └── news_payment.py
│   │   │
│   │   ├── routes/
│   │   │   ├── auth_routes.py
│   │   │   ├── news_routes.py
│   │   │   ├── writing_routes.py
│   │   │   └── answer_writing_routes.py
│   │   │
│   │   ├── services/
│   │   │   ├── news_service.py
│   │   │   ├── news_filter.py
│   │   │   ├── news_scoring.py
│   │   │   ├── news_mcq_service.py
│   │   │   ├── news_ai_service.py
│   │   │   ├── translation_service.py
│   │   │   ├── question_service.py
│   │   │   ├── answer_writing_service.py
│   │   │   ├── writing_ai_service.py
│   │   │   ├── writing_payment_service.py
│   │   │   └── news_payment_service.py
│   │   │
│   │   ├── auth.py
│   │   ├── config.py
│   │   ├── database.py
│   │   ├── schemas.py
│   │   └── main.py
│   │
│   ├── Dockerfile
│   └── requirements.txt
│
├── frontend/
│   │
│   ├── src/
│   │   ├── api/
│   │   ├── components/
│   │   ├── pages/
│   │   │   ├── Dashboard.jsx
│   │   │   ├── News.jsx
│   │   │   ├── MCQs.jsx
│   │   │   ├── Writing.jsx
│   │   │   ├── Essay.jsx
│   │   │   ├── Essays.jsx
│   │   │   ├── Login.jsx
│   │   │   └── Signup.jsx
│   │   ├── App.jsx
│   │   └── main.jsx
│   │
│   ├── Dockerfile
│   ├── package.json
│   └── vite.config.js
│
├── docker-compose.yml
├── .gitignore
└── README.md
```

---

# 🛠️ Tech Stack

## Backend

* Python
* FastAPI
* SQLAlchemy
* Pydantic
* JWT Authentication
* Passlib / Argon2
* Uvicorn
* REST APIs

## Frontend

* React
* Vite
* JavaScript / JSX
* CSS
* Axios
* React Router

## AI

The project is designed around AI-powered services for:

* Current affairs processing
* Question generation
* MCQ generation
* Answer evaluation
* Model answers
* Essay generation
* Translation

AI providers can be configured through environment variables.

## Database

* SQLite for local development
* PostgreSQL supported for production deployments
* SQLAlchemy ORM

## Payments

* Razorpay

## Deployment

Docker and Docker Compose are supported.

---

# 📋 Requirements

Before running the project, install:

* Python 3.11+
* Node.js 18+
* npm
* Git
* Docker *(optional)*

---

# ⚙️ Backend Setup

Go to the backend directory:

```bash
cd backend
```

Create a virtual environment:

```bash
python -m venv venv
```

Activate it on Windows:

```powershell
venv\Scripts\activate
```

Install dependencies:

```bash
pip install -r requirements.txt
```

Create a `.env` file inside `backend/`.

Example:

```env
DATABASE_URL=sqlite:///./users.db

SECRET_KEY=your-secret-key

GROQ_API_KEY=your-groq-api-key

NEWS_API_KEY=your-news-api-key

RAZORPAY_KEY_ID=your-razorpay-key-id
RAZORPAY_KEY_SECRET=your-razorpay-key-secret
```

Do **not** commit the `.env` file to GitHub.

---

# ▶️ Run Backend

From the `backend` directory:

```bash
python -m uvicorn app.main:app --reload
```

Backend will be available at:

```text
http://127.0.0.1:8000
```

FastAPI Swagger documentation:

```text
http://127.0.0.1:8000/docs
```

---

# 💻 Frontend Setup

Go to the frontend directory:

```bash
cd frontend
```

Install dependencies:

```bash
npm install
```

Create:

```text
frontend/.env
```

Example:

```env
VITE_API_URL=http://127.0.0.1:8000
VITE_RAZORPAY_KEY_ID=your-razorpay-key-id
```

Run the development server:

```bash
npm run dev
```

The frontend will normally be available at:

```text
http://localhost:5173
```

---

# 🐳 Docker

The project also includes Docker configuration.

From the project root:

```bash
docker compose up --build
```

To stop the containers:

```bash
docker compose down
```

---

# 🔑 Authentication Flow

The application uses JWT-based authentication.

### Signup

```http
POST /auth/signup
```

### Login

```http
POST /auth/login
```

Successful login returns an access token:

```json
{
  "access_token": "JWT_TOKEN",
  "token_type": "bearer"
}
```

The frontend uses this token for protected API requests.

---

# 📰 News API

Example endpoint:

```http
GET /news/search
```

Example:

```text
/news/search?q=India&page=1&page_size=20&language=en&exam=UPSC
```

The news pipeline supports:

```text
Search
  ↓
Normalization
  ↓
Classification
  ↓
Exam Filtering
  ↓
Category Filtering
  ↓
Scoring
  ↓
Ranking
  ↓
Pagination
```

---

# 🧠 MCQ API

Practice endpoint:

```http
GET /news/mcqs/practice
```

Example:

```text
/news/mcqs/practice?exam=UPSC&language=hi&limit=50
```

---

# ✍️ Writing API

### Generate Question

```http
POST /writing/questions/generate
```

Example request:

```json
{
  "exam": "UPSC",
  "category": "General",
  "question_type": "short",
  "target_words": 150,
  "language": "hi"
}
```

Supported word limits:

```text
150
250
```

### List Questions

```http
GET /writing/questions
```

### Generate Model Answer

```http
POST /writing/questions/{question_id}/generate-answer
```

### Submit Answer

```http
POST /writing/questions/{question_id}/submit
```

---

# 💳 Writing Subscription

Writing access is protected by a subscription system.

The backend verifies:

```text
Authentication
      ↓
Subscription exists
      ↓
Payment completed
      ↓
Subscription active
      ↓
Subscription not expired
      ↓
Answer quota available
```

Answer quota is consumed only when an answer submission requires it.

Model-answer access does not consume the answer submission quota.

---

# 🔒 Security

Sensitive configuration must be stored in environment variables.

Never commit:

```text
.env
.env.*
*.db
*.sqlite
*.sqlite3
venv/
.venv/
node_modules/
*.log
*.bak
*.backup
```

Never expose:

```text
RAZORPAY_KEY_SECRET
GROQ_API_KEY
NEWS_API_KEY
SECRET_KEY
DATABASE credentials
```

Only public frontend configuration such as the Razorpay **Key ID** may be exposed where required by the payment SDK.

---

# 📊 Supported Exams

The platform is designed for:

* **UPSC**
* **BPSC**
* **State PCS**

The architecture can be extended to additional state-level competitive examinations.

---

# 🌐 Language Support

Current application support includes:

* 🇮🇳 Hindi
* 🇬🇧 English

The AI and translation services are designed to support bilingual exam preparation.

---

# 🎯 Project Goals

The long-term goal of this project is to provide an integrated AI preparation platform where aspirants can:

1. Read relevant current affairs
2. Practice exam-oriented MCQs
3. Generate answer-writing questions
4. Write answers
5. Receive AI-based evaluation
6. Compare answers with model answers
7. Practice essays
8. Track preparation activity

All from a single platform.

---

# 🚧 Development Status

The project is under active development.

Current major modules:

* [x] Authentication
* [x] JWT protection
* [x] Current Affairs
* [x] News filtering
* [x] MCQ practice
* [x] AI Answer Writing
* [x] Essay module
* [x] Writing subscription
* [x] Razorpay payment integration
* [x] Docker configuration
* [x] Hindi / English support

Future improvements may include:

* Advanced performance analytics
* More State PCS examinations
* Personalized study plans
* Daily targets
* Leaderboards
* Improved AI evaluation
* More detailed answer analytics
* Production-grade PostgreSQL migrations
* Automated testing
* Cloud deployment

---

# 🤝 Contributing

Contributions are welcome.

1. Fork the repository
2. Create a feature branch

```bash
git checkout -b feature/your-feature
```

3. Make your changes
4. Commit your changes

```bash
git commit -m "Add your feature"
```

5. Push the branch

```bash
git push origin feature/your-feature
```

6. Open a Pull Request

---

# 📄 License

This project is currently maintained as a private/development project.

Add an appropriate open-source license before distributing the source code publicly.

---

# 👨‍💻 Project

**UPSC • BPSC • STATE PCS**

Built as an AI-powered competitive-examination preparation platform.

GitHub:

`https://github.com/munikabir2-collab/UPSC-BPSC-STATEPCS`
