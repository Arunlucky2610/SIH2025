# Rural Digital Learning App - Development Instructions

This is a Django-based learning management system designed for rural education with offline capabilities and multilingual support.

## Project Information

- **Language**: Python 3.13
- **Framework**: Django 4.2.7
- **Database**: SQLite3 (development), PostgreSQL (production)
- **Frontend**: Bootstrap 5, PWA-enabled
- **Purpose**: Educational platform for students, teachers, and parents in rural areas

## Quick Start

1. **Environment**: Python virtual environment is configured at `.venv/`
2. **Dependencies**: Install via `pip install -r requirements.txt`
3. **Database**: Run `python manage.py migrate` and `python manage.py populate_data`
4. **Server**: Start with `python manage.py runserver`
5. **Access**: http://127.0.0.1:8000/

## Sample Credentials

- **Admin**: admin/admin123
- **Teacher**: teacher1/teacher123
- **Students**: student1/student123, student2/student123, student3/student123
- **Parent**: parent1/parent123

## Features

- Multi-language support (English, Hindi, Punjabi)
- Offline-first PWA design
- Role-based access control
- Lesson management and quiz system
- Progress tracking and analytics
- Teacher-parent communication

