# Rural Digital Learning App

A comprehensive Django-based learning management system designed specifically for rural education with offline capabilities and multilingual support.

## 🌟 Features

### Core Functionality
- **Multi-language Support**: English, Hindi (हिंदी), and Punjabi (ਪੰਜਾਬੀ)
- **Role-based Access**: Student, Teacher, and Parent dashboards
- **Offline-first Design**: PWA with service worker for offline access
- **Mobile-optimized**: Responsive design for low-end devices
- **Lesson Management**: Upload/download lessons for offline use
- **Quiz System**: Interactive MCQ quizzes with score tracking
- **Progress Tracking**: Comprehensive learning analytics

### Target Users
- **Students**: Access lessons, take quizzes, track progress
- **Teachers**: Upload content, monitor student progress, manage courses
- **Parents**: View children's learning progress and performance

## 🚀 Quick Start

### Prerequisites
- Python 3.8+
- Django 4.2+
- Modern web browser with PWA support

### Installation

1. **Clone the repository**
   ```bash
   git clone <repository-url>
   cd rural-digital-learning
   ```

2. **Install dependencies**
   ```bash
   pip install -r requirements.txt
   ```

3. **Apply migrations**
   ```bash
   python manage.py migrate
   ```

4. **Populate sample data**
   ```bash
   python manage.py populate_data
   ```

5. **Run development server**
   ```bash
   python manage.py runserver
   ```

6. **Access the application**
   - Open http://127.0.0.1:8000 in your browser
   - Use the sample login credentials provided below

## 👥 Sample Login Credentials

| Role | Username | Password | Description |
|------|----------|----------|-------------|
| Admin | admin | admin123 | Full admin access |
| Teacher | teacher1 | teacher123 | Teacher dashboard access |
| Student | student1 | student123 | Student with completed lessons |
| Student | student2 | student123 | Student with in-progress lessons |
| Student | student3 | student123 | New student account |
| Parent | parent1 | parent123 | Parent with linked child |

## 📱 Progressive Web App (PWA)

The app includes full PWA functionality:

- **Offline Access**: Cache lessons for offline viewing
- **Background Sync**: Sync progress when connectivity returns
- **Push Notifications**: Notify about new lessons
- **App-like Experience**: Install on mobile devices
- **Responsive Design**: Works on all screen sizes

### Installing as PWA
1. Open the app in a modern browser
2. Look for "Install App" prompt or menu option
3. Follow browser-specific installation steps

## 🏗️ Architecture

### Tech Stack
- **Backend**: Django 4.2 (Python)
- **Database**: SQLite (development) / PostgreSQL (production)
- **Frontend**: Bootstrap 5 + vanilla JavaScript
- **PWA**: Service Worker + Web App Manifest
- **Authentication**: Django built-in auth system

### Project Structure
```
rural_edu/
├── learning/                 # Main Django app
│   ├── models.py            # Database models
│   ├── views.py             # Business logic
│   ├── admin.py             # Admin interface
│   ├── urls.py              # URL routing
│   ├── templates/           # HTML templates
│   └── management/          # Custom commands
├── static/                  # Static files
│   ├── css/                 # Custom styles
│   ├── js/                  # JavaScript files
│   └── icons/               # PWA icons
├── media/                   # User uploads
├── rural_edu/               # Django project settings
└── requirements.txt         # Python dependencies
```

## 📊 Database Models

### Core Models
- **UserProfile**: Extended user model with roles and preferences
- **Lesson**: Learning content with multilingual support
- **Quiz**: MCQ questions linked to lessons
- **ModuleProgress**: Track student completion and scores
- **QuizAttempt**: Individual quiz attempts and results
- **LessonDownload**: Track offline downloads

### Relationships
- Students can have Parent users linked
- Teachers create and manage Lessons
- Lessons can have multiple Quizzes
- Students have ModuleProgress for each Lesson
- Quiz attempts are tracked per student

## 🌐 Multilingual Support

The app supports three languages with easy extensibility:

- **English (en)**: Default language
- **Hindi (hi)**: हिंदी भाषा में कंटेंट
- **Punjabi (pa)**: ਪੰਜਾਬੀ ਭਾਸ਼ਾ ਵਿੱਚ ਸਮੱਗਰੀ

### Adding New Languages
1. Add language code to `LANGUAGES` in settings.py
2. Create lessons in the new language
3. Update language selection in templates
4. Add translations for UI elements

## 📱 Mobile Optimization

### Design Principles
- **Mobile-first**: Optimized for smartphones and tablets
- **Low-bandwidth**: Minimal resource usage
- **Offline-capable**: Essential functions work without internet
- **Touch-friendly**: Large buttons and easy navigation
- **Battery-efficient**: Optimized JavaScript and CSS

### Performance Features
- Lazy loading of content
- Compressed images and assets
- Efficient caching strategies
- Minimal external dependencies
- Progressive enhancement

## 🔒 Security Features

- **Role-based Access Control**: Different permissions for each user type
- **CSRF Protection**: Built-in Django CSRF middleware
- **SQL Injection Prevention**: Django ORM protection
- **XSS Protection**: Template auto-escaping
- **Secure Headers**: Security middleware enabled
- **Input Validation**: Form validation and sanitization

## 📈 Analytics & Progress Tracking

### Student Analytics
- Lesson completion rates
- Quiz scores and attempts
- Time spent on lessons
- Learning streaks and patterns
- Language preference insights

### Teacher Dashboard
- Class-wide progress overview
- Individual student performance
- Lesson engagement metrics
- Quiz difficulty analysis
- Content effectiveness tracking

### Parent Dashboard
- Child's learning progress
- Recent activity summary
- Performance comparisons
- Learning recommendations
- Goal setting and tracking

## 🚀 Deployment

### Development Setup (Current)
- SQLite database
- Django development server
- Debug mode enabled
- Sample data included

### Production Setup
1. **Switch to PostgreSQL**
   ```python
   # Uncomment PostgreSQL config in settings.py
   DATABASES = {
       'default': {
           'ENGINE': 'django.db.backends.postgresql',
           'NAME': 'rural_edu_db',
           'USER': 'your_user',
           'PASSWORD': 'your_password',
           'HOST': 'localhost',
           'PORT': '5432',
       }
   }
   ```

2. **Environment Variables**
   ```bash
   export DEBUG=False
   export SECRET_KEY='your-secret-key'
   export DATABASE_URL='postgresql://user:pass@localhost:5432/dbname'
   ```

3. **Static Files**
   ```bash
   python manage.py collectstatic
   ```

4. **WSGI Deployment**
   - Use Gunicorn, uWSGI, or similar
   - Configure Nginx for static files
   - Set up SSL certificates

## 🔧 Customization

### Adding New Lesson Types
1. Update `LESSON_TYPE_CHOICES` in models.py
2. Add corresponding icons and styling
3. Update filtering logic in templates
4. Create specific lesson templates if needed

### Custom Quiz Types
1. Extend Quiz model with new question types
2. Update quiz submission logic
3. Add new question templates
4. Implement scoring algorithms

### Theming
1. Modify CSS variables in static/css/style.css
2. Update Bootstrap theme colors
3. Add custom fonts and icons
4. Implement dark mode support

## 🤝 Contributing

1. Fork the repository
2. Create a feature branch
3. Make your changes
4. Add tests for new functionality
5. Submit a pull request

### Development Guidelines
- Follow Django best practices
- Write clean, documented code
- Ensure mobile compatibility
- Test offline functionality
- Maintain accessibility standards

## 📝 License

This project is licensed under the MIT License - see the LICENSE file for details.

## 🙏 Acknowledgments

- Django community for the excellent framework
- Bootstrap team for responsive design components
- Contributors to rural education initiatives
- Open source community for various tools and libraries

## 📞 Support

For support and questions:
- Create an issue on GitHub
- Contact the development team
- Check the documentation wiki
- Join our community discussions

---

**Built with ❤️ for rural education and digital literacy**