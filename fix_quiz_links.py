import os
import django

# Setup Django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'rural_edu.settings')
django.setup()

from learning.models import QuizContainer, Quiz

# Get the first QuizContainer
quiz_container = QuizContainer.objects.first()
print(f"Using QuizContainer: {quiz_container}")

# Link all orphaned Quiz objects to this container
orphaned_quizzes = Quiz.objects.filter(quiz_container__isnull=True)
print(f"Found {orphaned_quizzes.count()} orphaned quizzes")

for i, quiz in enumerate(orphaned_quizzes, 1):
    quiz.quiz_container = quiz_container
    quiz.order = i  # Set order for proper sequencing
    quiz.save()
    print(f"Linked Quiz {quiz.id} to QuizContainer {quiz_container.id}")

print("Done! Checking results...")
questions = Quiz.objects.filter(quiz_container=quiz_container)
print(f"QuizContainer '{quiz_container.title}' now has {questions.count()} questions")