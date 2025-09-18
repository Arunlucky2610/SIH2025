import os
import django

# Setup Django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'rural_edu.settings')
django.setup()

from learning.models import QuizContainer, Quiz, UserProfile

# Check QuizContainers
print("=== QuizContainers ===")
for qc in QuizContainer.objects.all():
    print(f"QuizContainer {qc.id}: {qc.title}, active={qc.is_active}")
    questions = Quiz.objects.filter(quiz_container=qc)
    print(f"  Questions: {questions.count()}")
    for q in questions:
        print(f"    - {q.question[:50]}...")

print("\n=== All Quiz Objects ===")
for q in Quiz.objects.all():
    print(f"Quiz {q.id}: container_id={q.quiz_container_id}, question='{q.question[:50]}...'")

print("\n=== Students ===")
students = UserProfile.objects.filter(role='student')
print(f"Students found: {students.count()}")
for student in students:
    print(f"  - {student.user.username}")