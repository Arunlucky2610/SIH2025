#!/usr/bin/env python
"""
Test MongoDB connection
"""
import os
import sys
import django

# Setup Django
sys.path.append(os.path.dirname(os.path.abspath(__file__)))
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'rural_edu.settings')
django.setup()

def test_mongodb_connection():
    """Test MongoDB connection"""
    try:
        from learning.mongodb_utils import get_mongodb_connection
        
        print("🔄 Testing MongoDB connection...")
        db = get_mongodb_connection()
        
        # Test connection by pinging
        print("✅ MongoDB connection successful!")
        print(f"📊 Database: {db.name}")
        
        # List collections
        collections = db.list_collection_names()
        print(f"📁 Collections: {collections}")
        
        # Test creating a test document
        test_collection = db.test_collection
        test_doc = {"test": "connection", "status": "working"}
        result = test_collection.insert_one(test_doc)
        print(f"✅ Test document created with ID: {result.inserted_id}")
        
        # Clean up test document
        test_collection.delete_one({"_id": result.inserted_id})
        print("🧹 Test document cleaned up")
        
        print("\n🎉 MongoDB is ready for the application!")
        return True
        
    except Exception as e:
        print(f"❌ MongoDB connection failed: {e}")
        return False

if __name__ == '__main__':
    test_mongodb_connection()