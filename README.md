# AI Mini-Course Generator

[](https://www.python.org/)
[](https://fastapi.tiangolo.com/)
[](https://reactjs.org/)
[](https://www.mongodb.com/)
[](https://tailwindcss.com/)

An intelligent, full-stack web application that generates complete mini-courses on any topic you can imagine. Powered by Google's Gemini AI, this platform creates structured lessons, relevant video suggestions, and interactive quizzes to accelerate your learning.

## Key Features

  - **🤖 AI-Powered Course Generation**: Enter any topic and receive a structured course in seconds.
  - **👤 User Authentication**: Secure registration and login system using JWT.
  - **📚 Structured Lessons**: Each course includes multiple, detailed lessons with explanations and markdown support.
  - **💻 Code Examples**: Automatically generated code snippets for technical topics.
  - **🎥 Video Integration**: Suggests relevant YouTube videos to supplement learning content.
  - **📝 Interactive Quizzes**: Test your knowledge with a quiz at the end of each course and get instant results.
  - **💾 Course Dashboard**: Save and manage all your generated courses in a personal dashboard.
  - **🎨 Modern UI**: A sleek, responsive, and intuitive user interface built with React and shadcn/ui.

## Tech Stack

### Backend

  - **Framework**: FastAPI
  - **Database**: MongoDB (with Motor for asynchronous operations)
  - **AI Integration**: Google Gemini
  - **Authentication**: PyJWT & Passlib
  - **Server**: Uvicorn
  - **Validation**: Pydantic

### Frontend

  - **Framework**: React.js
  - **UI Library**: Custom components inspired by shadcn/ui
  - **Styling**: Tailwind CSS
  - **Routing**: React Router
  - **API Communication**: Axios
  - **Build Tool**: Create React App with Craco

## Getting Started

Follow these instructions to get a copy of the project up and running on your local machine for development and testing purposes.

### Prerequisites

  - Python 3.9+
  - Node.js v18.x or later
  - npm or yarn
  - MongoDB instance (local or cloud-based like MongoDB Atlas)
  - Google API Key with Gemini enabled.

### 1\. Clone the Repository

```bash
git clone <your-repository-url>
cd <your-repository-name>
```

### 2\. Backend Setup

First, navigate to the backend directory and set up the environment.

```bash
cd backend
```

**Create and activate a virtual environment:**

```bash
# For macOS/Linux
python3 -m venv venv
source venv/bin/activate

# For Windows
python -m venv venv
.\venv\Scripts\activate
```

**Install dependencies:**

```bash
pip install -r requirements.txt
```

**Configure environment variables:**

Create a `.env` file in the `backend` directory and add the following variables. Replace the placeholder values with your actual credentials.

```env
# .env

# MongoDB Configuration
MONGO_URL="mongodb://localhost:27017"
DB_NAME="mini_course_db"

# JWT Secret Key (generate a strong, random string)
JWT_SECRET="your_super_secret_jwt_key"

# Google Gemini API Key
GOOGLE_API_KEY="your_google_api_key_here"

# Frontend URL for CORS
CORS_ORIGINS="http://localhost:3000"
```

### 3\. Frontend Setup

In a new terminal, navigate to the frontend directory.

```bash
cd frontend
```

**Install dependencies:**

```bash
# Using npm
npm install

# Or using yarn
yarn install
```

**Configure environment variables:**

Create a `.env` file in the `frontend` directory and specify the backend API URL.

```env
# .env

REACT_APP_BACKEND_URL=http://127.0.0.1:8000
```

## Running the Application

### Start the Backend Server

Make sure you are in the `backend` directory with your virtual environment activated.

```bash
uvicorn server:app --reload
```

The backend API will be running at `http://127.0.0.1:8000`.

### Start the Frontend Development Server

Make sure you are in the `frontend` directory.

```bash
# Using npm
npm start

# Or using yarn
yarn start
```

The frontend application will be available at `http://localhost:3000`.

## API Testing

A comprehensive API test script is included. To run the tests, navigate to the root directory and execute:

```bash
python backend_test.py
```

This script will test user registration, login, course generation, and other critical API endpoints.

## Project Structure

```
.
├── backend/
│   ├── .env              # Backend environment variables
│   ├── requirements.txt  # Python dependencies
│   └── server.py         # FastAPI application logic
├── frontend/
│   ├── public/           # Public assets and index.html
│   ├── src/              # React source code
│   │   ├── components/   # Reusable UI components
│   │   ├── App.js        # Main application component
│   │   └── index.js      # Entry point
│   ├── .env              # Frontend environment variables
│   └── package.json      # Node.js dependencies
└── backend_test.py       # API integration test script
└── README.md             # This file
```

## License

This project is licensed under the MIT License - see the `LICENSE` file for details.

-----

Made with ❤️ by [sashankbanda](https://www.google.com/search?q=https://github.com/sashankbanda)