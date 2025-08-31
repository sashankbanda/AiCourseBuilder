import React, { useState, useEffect } from 'react';
import { BrowserRouter, Routes, Route, Navigate, useNavigate } from 'react-router-dom';
import axios from 'axios';
import './App.css';

const BACKEND_URL = process.env.REACT_APP_BACKEND_URL;
const API = `${BACKEND_URL}/api`;

// Configure axios defaults
axios.defaults.headers.common['Content-Type'] = 'application/json';

// Auth Context
const AuthContext = React.createContext();

const AuthProvider = ({ children }) => {
  const [user, setUser] = useState(null);
  const [token, setToken] = useState(localStorage.getItem('token'));
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    if (token) {
      axios.defaults.headers.common['Authorization'] = `Bearer ${token}`;
      // You could verify token here if needed
    }
    setLoading(false);
  }, [token]);

  const login = (userData, userToken) => {
    setUser(userData);
    setToken(userToken);
    localStorage.setItem('token', userToken);
    axios.defaults.headers.common['Authorization'] = `Bearer ${userToken}`;
  };

  const logout = () => {
    setUser(null);
    setToken(null);
    localStorage.removeItem('token');
    delete axios.defaults.headers.common['Authorization'];
  };

  return (
    <AuthContext.Provider value={{ user, token, login, logout, loading }}>
      {children}
    </AuthContext.Provider>
  );
};

const useAuth = () => {
  const context = React.useContext(AuthContext);
  if (!context) {
    throw new Error('useAuth must be used within AuthProvider');
  }
  return context;
};

// Loading Component
const LoadingSpinner = () => (
  <div className="loading-spinner">
    <div className="spinner"></div>
    <p>Generating your course...</p>
  </div>
);

// Landing Page Component
const LandingPage = () => {
  const navigate = useNavigate();
  const { user } = useAuth();

  if (user) {
    navigate('/dashboard');
    return null;
  }

  return (
    <div className="landing-page">
      <div className="hero-section">
        <div className="glass-panel hero-content">
          <h1 className="hero-title">
            AI-Powered <span className="gradient-text">Mini Courses</span>
          </h1>
          <p className="hero-subtitle">
            Enter any topic and get a complete course with lessons, videos, and quizzes
          </p>
          <div className="hero-buttons">
            <button 
              className="cta-button primary"
              onClick={() => navigate('/auth')}
            >
              Get Started
            </button>
            <button 
              className="cta-button secondary"
              onClick={() => navigate('/demo')}
            >
              Try Demo
            </button>
          </div>
        </div>
      </div>
      
      <div className="features-section">
        <div className="features-grid">
          <div className="feature-card glass-panel">
            <div className="feature-icon">🧠</div>
            <h3>AI-Generated Content</h3>
            <p>Intelligent course creation powered by advanced AI</p>
          </div>
          <div className="feature-card glass-panel">
            <div className="feature-icon">📚</div>
            <h3>Structured Lessons</h3>
            <p>Well-organized lessons with clear explanations</p>
          </div>
          <div className="feature-card glass-panel">
            <div className="feature-icon">🎥</div>
            <h3>Video Integration</h3>
            <p>Relevant YouTube videos embedded in lessons</p>
          </div>
          <div className="feature-card glass-panel">
            <div className="feature-icon">📝</div>
            <h3>Interactive Quizzes</h3>
            <p>Test your knowledge with auto-generated quizzes</p>
          </div>
        </div>
      </div>
    </div>
  );
};

// Auth Component
const AuthPage = () => {
  const [isLogin, setIsLogin] = useState(true);
  const [formData, setFormData] = useState({
    username: '',
    email: '',
    password: ''
  });
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState('');
  const { login } = useAuth();
  const navigate = useNavigate();

  const handleSubmit = async (e) => {
    e.preventDefault();
    setLoading(true);
    setError('');

    try {
      const endpoint = isLogin ? '/auth/login' : '/auth/register';
      const data = isLogin 
        ? { username: formData.username, password: formData.password }
        : formData;

      const response = await axios.post(`${API}${endpoint}`, data);
      login(response.data.user, response.data.token);
      navigate('/dashboard');
    } catch (err) {
      setError(err.response?.data?.detail || 'Authentication failed');
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="auth-page">
      <div className="auth-container glass-panel">
        <h2 className="auth-title">{isLogin ? 'Welcome Back' : 'Create Account'}</h2>
        
        {error && <div className="error-message">{error}</div>}
        
        <form onSubmit={handleSubmit} className="auth-form">
          <div className="form-group">
            <input
              type="text"
              placeholder="Username"
              value={formData.username}
              onChange={(e) => setFormData({...formData, username: e.target.value})}
              required
              className="form-input"
            />
          </div>
          
          {!isLogin && (
            <div className="form-group">
              <input
                type="email"
                placeholder="Email"
                value={formData.email}
                onChange={(e) => setFormData({...formData, email: e.target.value})}
                required
                className="form-input"
              />
            </div>
          )}
          
          <div className="form-group">
            <input
              type="password"
              placeholder="Password"
              value={formData.password}
              onChange={(e) => setFormData({...formData, password: e.target.value})}
              required
              className="form-input"
            />
          </div>
          
          <button type="submit" disabled={loading} className="auth-button">
            {loading ? 'Processing...' : (isLogin ? 'Sign In' : 'Sign Up')}
          </button>
        </form>
        
        <p className="auth-switch">
          {isLogin ? "Don't have an account? " : "Already have an account? "}
          <button 
            onClick={() => setIsLogin(!isLogin)}
            className="link-button"
          >
            {isLogin ? 'Sign Up' : 'Sign In'}
          </button>
        </p>
      </div>
    </div>
  );
};

// Dashboard Component
const Dashboard = () => {
  const [courses, setCourses] = useState([]);
  const [loading, setLoading] = useState(true);
  const [showGenerator, setShowGenerator] = useState(false);
  const { user, logout } = useAuth();
  const navigate = useNavigate();

  useEffect(() => {
    fetchCourses();
  }, []);

  const fetchCourses = async () => {
    try {
      const response = await axios.get(`${API}/courses`);
      setCourses(response.data);
    } catch (error) {
      console.error('Error fetching courses:', error);
    } finally {
      setLoading(false);
    }
  };

  if (loading) {
    return <div className="dashboard-loading">Loading your courses...</div>;
  }

  return (
    <div className="dashboard">
      <div className="dashboard-header">
        <div className="dashboard-nav">
          <h1 className="dashboard-title">My Courses</h1>
          <div className="nav-actions">
            <span className="user-greeting">Hello, {user?.username}!</span>
            <button 
              className="btn-primary"
              onClick={() => setShowGenerator(true)}
            >
              Generate New Course
            </button>
            <button className="btn-secondary" onClick={logout}>Logout</button>
          </div>
        </div>
      </div>

      {showGenerator && (
        <CourseGenerator 
          onClose={() => setShowGenerator(false)}
          onCourseGenerated={fetchCourses}
        />
      )}

      <div className="courses-grid">
        {courses.length === 0 ? (
          <div className="empty-state glass-panel">
            <div className="empty-icon">📚</div>
            <h3>No courses yet</h3>
            <p>Generate your first AI-powered course to get started</p>
            <button 
              className="btn-primary"
              onClick={() => setShowGenerator(true)}
            >
              Create First Course
            </button>
          </div>
        ) : (
          courses.map(course => (
            <div key={course.id} className="course-card glass-panel">
              <h3 className="course-title">{course.title}</h3>
              <p className="course-description">{course.description}</p>
              <div className="course-stats">
                <span className="stat">{course.lessons?.length || 0} lessons</span>
                <span className="stat">{course.quizzes?.length || 0} quizzes</span>
              </div>
              <button 
                className="btn-primary course-btn"
                onClick={() => navigate(`/course/${course.id}`)}
              >
                Start Learning
              </button>
            </div>
          ))
        )}
      </div>
    </div>
  );
};

// Course Generator Component
const CourseGenerator = ({ onClose, onCourseGenerated }) => {
  const [topic, setTopic] = useState('');
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState('');

  const handleSubmit = async (e) => {
    e.preventDefault();
    if (!topic.trim()) return;

    setLoading(true);
    setError('');

    try {
      // Generate course
      const generateResponse = await axios.post(`${API}/courses/generate`, {
        topic: topic
      });

      // Save course
      await axios.post(`${API}/courses/save`, generateResponse.data);

      // Refresh course list and close modal
      await onCourseGenerated();
      onClose();
    } catch (err) {
      setError(err.response?.data?.detail || 'Failed to generate course');
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="generator-overlay">
      <div className="generator-modal glass-panel">
        <div className="modal-header">
          <h2>Generate New Course</h2>
          <button className="close-btn" onClick={onClose}>×</button>
        </div>

        {loading ? (
          <LoadingSpinner />
        ) : (
          <form onSubmit={handleSubmit} className="generator-form">
            {error && <div className="error-message">{error}</div>}
            
            <div className="form-group">
              <label htmlFor="topic">What would you like to learn about?</label>
              <input
                id="topic"
                type="text"
                placeholder="e.g., JavaScript async/await, Machine Learning basics, React Hooks..."
                value={topic}
                onChange={(e) => setTopic(e.target.value)}
                className="form-input topic-input"
                required
              />
            </div>

            <div className="form-actions">
              <button type="button" className="btn-secondary" onClick={onClose}>
                Cancel
              </button>
              <button type="submit" className="btn-primary">
                Generate Course
              </button>
            </div>
          </form>
        )}
      </div>
    </div>
  );
};

// Course View Component
const CourseView = () => {
  const [course, setCourse] = useState(null);
  const [currentLesson, setCurrentLesson] = useState(0);
  const [showQuiz, setShowQuiz] = useState(false);
  const [quizAnswers, setQuizAnswers] = useState({});
  const [quizResult, setQuizResult] = useState(null);
  const [loading, setLoading] = useState(true);
  const { user } = useAuth();
  const navigate = useNavigate();
  
  // Get course ID from URL
  const courseId = window.location.pathname.split('/').pop();

  useEffect(() => {
    fetchCourse();
  }, [courseId]);

  const fetchCourse = async () => {
    try {
      const response = await axios.get(`${API}/courses/${courseId}`);
      setCourse(response.data);
    } catch (error) {
      console.error('Error fetching course:', error);
      navigate('/dashboard');
    } finally {
      setLoading(false);
    }
  };

  const handleQuizSubmit = async () => {
    try {
      const answers = course.quizzes.map((_, index) => quizAnswers[index] || '');
      const response = await axios.post(`${API}/quiz/submit`, {
        course_id: courseId,
        user_id: user.id,
        answers
      });
      setQuizResult(response.data);
    } catch (error) {
      console.error('Error submitting quiz:', error);
    }
  };

  if (loading) {
    return <div className="course-loading">Loading course...</div>;
  }

  if (!course) {
    return <div className="course-error">Course not found</div>;
  }

  return (
    <div className="course-view">
      <div className="course-header">
        <button className="back-btn" onClick={() => navigate('/dashboard')}>
          ← Back to Dashboard
        </button>
        <h1 className="course-title">{course.title}</h1>
        <p className="course-description">{course.description}</p>
      </div>

      <div className="course-content">
        <aside className="course-sidebar glass-panel">
          <h3>Course Content</h3>
          <div className="lesson-list">
            {course.lessons.map((lesson, index) => (
              <button
                key={lesson.id}
                className={`lesson-item ${currentLesson === index ? 'active' : ''}`}
                onClick={() => setCurrentLesson(index)}
              >
                <span className="lesson-number">{index + 1}</span>
                <span className="lesson-title">{lesson.title}</span>
              </button>
            ))}
            <button
              className={`lesson-item quiz-item ${showQuiz ? 'active' : ''}`}
              onClick={() => setShowQuiz(true)}
            >
              <span className="lesson-number">📝</span>
              <span className="lesson-title">Take Quiz</span>
            </button>
          </div>
        </aside>

        <main className="course-main">
          {showQuiz ? (
            <div className="quiz-section glass-panel">
              <h2>Course Quiz</h2>
              {quizResult ? (
                <div className="quiz-result">
                  <h3>Quiz Results</h3>
                  <div className="score-display">
                    <span className="score">{quizResult.result.score}/{quizResult.result.total_questions}</span>
                    <span className="percentage">{quizResult.percentage}%</span>
                  </div>
                  <div className="result-details">
                    {course.quizzes.map((quiz, index) => (
                      <div key={index} className="question-result">
                        <p className="question">{quiz.question}</p>
                        <p className={`answer ${quizAnswers[index] === quiz.correct_answer ? 'correct' : 'incorrect'}`}>
                          Your answer: {quizAnswers[index] || 'Not answered'}
                        </p>
                        <p className="correct-answer">Correct answer: {quiz.correct_answer}</p>
                        {quiz.explanation && <p className="explanation">{quiz.explanation}</p>}
                      </div>
                    ))}
                  </div>
                </div>
              ) : (
                <div className="quiz-questions">
                  {course.quizzes.map((quiz, index) => (
                    <div key={index} className="quiz-question">
                      <h4>Question {index + 1}</h4>
                      <p className="question-text">{quiz.question}</p>
                      <div className="quiz-options">
                        {quiz.options.map((option, optionIndex) => (
                          <label key={optionIndex} className="quiz-option">
                            <input
                              type="radio"
                              name={`question-${index}`}
                              value={option}
                              onChange={(e) => setQuizAnswers({
                                ...quizAnswers,
                                [index]: e.target.value
                              })}
                            />
                            <span>{option}</span>
                          </label>
                        ))}
                      </div>
                    </div>
                  ))}
                  <button className="btn-primary" onClick={handleQuizSubmit}>
                    Submit Quiz
                  </button>
                </div>
              )}
            </div>
          ) : (
            <div className="lesson-content glass-panel">
              <h2>{course.lessons[currentLesson]?.title}</h2>
              <div className="lesson-text">
                {course.lessons[currentLesson]?.content.split('\n').map((paragraph, index) => (
                  <p key={index}>{paragraph}</p>
                ))}
              </div>
              
              {course.lessons[currentLesson]?.code_examples && (
                <div className="code-section">
                  <h3>Code Examples</h3>
                  <pre className="code-block">
                    <code>{course.lessons[currentLesson].code_examples}</code>
                  </pre>
                </div>
              )}

              {course.lessons[currentLesson]?.videos?.length > 0 && (
                <div className="videos-section">
                  <h3>Related Videos</h3>
                  <div className="video-grid">
                    {course.lessons[currentLesson].videos.map((video, index) => (
                      <div key={index} className="video-card">
                        <a href={video.url} target="_blank" rel="noopener noreferrer" className="video-link">
                          <img src={video.thumbnail} alt={video.title} className="video-thumbnail" />
                          <p className="video-title">{video.title}</p>
                        </a>
                      </div>
                    ))}
                  </div>
                </div>
              )}

              <div className="lesson-navigation">
                <button
                  className="btn-secondary"
                  onClick={() => setCurrentLesson(Math.max(0, currentLesson - 1))}
                  disabled={currentLesson === 0}
                >
                  Previous Lesson
                </button>
                <button
                  className="btn-primary"
                  onClick={() => setCurrentLesson(Math.min(course.lessons.length - 1, currentLesson + 1))}
                  disabled={currentLesson === course.lessons.length - 1}
                >
                  Next Lesson
                </button>
              </div>
            </div>
          )}
        </main>
      </div>
    </div>
  );
};

// Protected Route Component
const ProtectedRoute = ({ children }) => {
  const { token, loading } = useAuth();
  
  if (loading) {
    return <div className="loading">Loading...</div>;
  }
  
  return token ? children : <Navigate to="/auth" />;
};

// Main App Component
function App() {
  return (
    <div className="App">
      <AuthProvider>
        <BrowserRouter>
          <Routes>
            <Route path="/" element={<LandingPage />} />
            <Route path="/auth" element={<AuthPage />} />
            <Route path="/dashboard" element={
              <ProtectedRoute>
                <Dashboard />
              </ProtectedRoute>
            } />
            <Route path="/course/:id" element={
              <ProtectedRoute>
                <CourseView />
              </ProtectedRoute>
            } />
            <Route path="*" element={<Navigate to="/" />} />
          </Routes>
        </BrowserRouter>
      </AuthProvider>
    </div>
  );
}

export default App;