"""
MongoDB utilities for Rural Learning Platform
"""
import pymongo
import bcrypt
from pymongo import MongoClient
from django.conf import settings
import logging

logger = logging.getLogger(__name__)

# MongoDB connection configuration
MONGO_URI = "mongodb://localhost:27017"
DATABASE_NAME = "rural_learning_platform"

def get_mongodb_connection():
    """
    Establish connection to MongoDB
    Returns the database instance
    """
    try:
        client = MongoClient(MONGO_URI)
        # Test the connection
        client.admin.command('ping')
        db = client[DATABASE_NAME]
        logger.info("Successfully connected to MongoDB")
        return db
    except Exception as e:
        logger.error(f"Failed to connect to MongoDB: {str(e)}")
        raise Exception(f"Database connection failed: {str(e)}")

def hash_password(password):
    """
    Hash password using bcrypt
    """
    salt = bcrypt.gensalt()
    hashed = bcrypt.hashpw(password.encode('utf-8'), salt)
    return hashed.decode('utf-8')

def verify_password(password, hashed_password):
    """
    Verify password against hashed password
    """
    return bcrypt.checkpw(password.encode('utf-8'), hashed_password.encode('utf-8'))

def create_user_in_mongodb(user_data):
    """
    Create a new user in MongoDB
    
    Args:
        user_data (dict): User information including role, username, password, etc.
    
    Returns:
        dict: Created user document or None if failed
    """
    try:
        db = get_mongodb_connection()
        users_collection = db.users
        
        # Check if username or email already exists
        existing_user = users_collection.find_one({
            "$or": [
                {"username": user_data["username"]},
                {"email": user_data["email"]}
            ]
        })
        
        if existing_user:
            if existing_user["username"] == user_data["username"]:
                raise ValueError("Username already exists")
            if existing_user["email"] == user_data["email"]:
                raise ValueError("Email already registered")
        
        # Hash the password
        user_data["password"] = hash_password(user_data["password"])
        
        # Add creation timestamp
        from datetime import datetime
        user_data["created_at"] = datetime.utcnow()
        user_data["updated_at"] = datetime.utcnow()
        user_data["is_active"] = True
        
        # Insert user into MongoDB
        result = users_collection.insert_one(user_data)
        
        # Return the created user (without password)
        created_user = users_collection.find_one({"_id": result.inserted_id})
        if created_user:
            created_user.pop("password", None)  # Remove password from returned data
            logger.info(f"User created successfully: {user_data['username']}")
            return created_user
        
        return None
        
    except ValueError as ve:
        logger.warning(f"User creation validation error: {str(ve)}")
        raise ve
    except Exception as e:
        logger.error(f"Error creating user in MongoDB: {str(e)}")
        raise Exception(f"Failed to create user: {str(e)}")

def get_user_by_username(username):
    """
    Retrieve user by username from MongoDB
    """
    try:
        db = get_mongodb_connection()
        users_collection = db.users
        user = users_collection.find_one({"username": username})
        return user
    except Exception as e:
        logger.error(f"Error retrieving user: {str(e)}")
        return None

def get_user_by_email(email):
    """
    Retrieve user by email from MongoDB
    """
    try:
        db = get_mongodb_connection()
        users_collection = db.users
        user = users_collection.find_one({"email": email})
        return user
    except Exception as e:
        logger.error(f"Error retrieving user by email: {str(e)}")
        return None

def save_to_role_collection(collection_name, user_data):
    """
    Save user data to role-specific MongoDB collection
    
    Args:
        collection_name (str): Name of the collection (students, parents, teachers)
        user_data (dict): User data to save
    
    Returns:
        dict: Created document or None if failed
    """
    try:
        db = get_mongodb_connection()
        collection = db[collection_name]
        
        # Check if username already exists in this collection
        existing_user = collection.find_one({"username": user_data["username"]})
        if existing_user:
            raise ValueError(f"Username already exists in {collection_name}")
        
        # Check if email exists (for parents and teachers)
        if "email" in user_data:
            existing_email = collection.find_one({"email": user_data["email"]})
            if existing_email:
                raise ValueError(f"Email already registered in {collection_name}")
        
        # Hash the password
        user_data["password"] = hash_password(user_data["password"])
        
        # Add timestamps
        from datetime import datetime
        user_data["created_at"] = datetime.utcnow()
        user_data["updated_at"] = datetime.utcnow()
        user_data["is_active"] = True
        
        # Insert user into MongoDB collection
        result = collection.insert_one(user_data)
        
        # Return the created user (without password)
        created_user = collection.find_one({"_id": result.inserted_id})
        if created_user:
            created_user.pop("password", None)  # Remove password from returned data
            logger.info(f"User created successfully in {collection_name}: {user_data['username']}")
            return created_user
        
        return None
        
    except ValueError as ve:
        logger.warning(f"User creation validation error in {collection_name}: {str(ve)}")
        raise ve
    except Exception as e:
        logger.error(f"Error creating user in {collection_name}: {str(e)}")
        raise Exception(f"Failed to create user in {collection_name}: {str(e)}")

def check_username_exists_in_collections(username):
    """
    Check if username exists in any role collection
    
    Args:
        username (str): Username to check
    
    Returns:
        bool: True if username exists, False otherwise
    """
    try:
        db = get_mongodb_connection()
        collections = ['students', 'parents', 'teachers']
        
        for collection_name in collections:
            collection = db[collection_name]
            if collection.find_one({"username": username}):
                return True
        
        return False
        
    except Exception as e:
        logger.error(f"Error checking username existence: {str(e)}")
        return False

def check_email_exists_in_collections(email):
    """
    Check if email exists in any role collection
    
    Args:
        email (str): Email to check
    
    Returns:
        bool: True if email exists, False otherwise
    """
    try:
        db = get_mongodb_connection()
        collections = ['parents', 'teachers']  # Students don't have email input
        
        for collection_name in collections:
            collection = db[collection_name]
            if collection.find_one({"email": email}):
                return True
        
        return False
        
    except Exception as e:
        logger.error(f"Error checking email existence: {str(e)}")
        return False

def get_user_from_role_collection(username_or_email, role):
    """
    Get user from role-specific MongoDB collection by username or email
    
    Args:
        username_or_email (str): Username or email to search for
        role (str): Role (student, parent, teacher)
    
    Returns:
        dict: User document or None if not found
    """
    try:
        db = get_mongodb_connection()
        collection_name = f"{role}s"  # students, parents, teachers
        collection = db[collection_name]
        
        # Search by username first, then by email (if applicable)
        user = collection.find_one({"username": username_or_email})
        
        if not user and role in ['parent', 'teacher']:
            # Try searching by email for parents and teachers
            user = collection.find_one({"email": username_or_email})
        
        return user
        
    except Exception as e:
        logger.error(f"Error retrieving user from {role}s collection: {str(e)}")
        return None

def authenticate_user_mongodb(username_or_email, password, role):
    """
    Authenticate user against MongoDB role collection
    
    Args:
        username_or_email (str): Username or email
        password (str): Plain text password
        role (str): User role (student, parent, teacher)
    
    Returns:
        dict: User document if authenticated, None otherwise
    """
    try:
        user = get_user_from_role_collection(username_or_email, role)
        
        if user and verify_password(password, user.get('password', '')):
            # Remove password from returned user data
            user.pop('password', None)
            return user
        
        return None
        
    except Exception as e:
        logger.error(f"Error authenticating user: {str(e)}")
        return None

def update_user_login_session(username, session_data):
    """
    Update user's last login session information
    """
    try:
        db = get_mongodb_connection()
        users_collection = db.users
        
        from datetime import datetime
        result = users_collection.update_one(
            {"username": username},
            {
                "$set": {
                    "last_login": datetime.utcnow(),
                    "last_session": session_data,
                    "updated_at": datetime.utcnow()
                }
            }
        )
        
        return result.modified_count > 0
        
    except Exception as e:
        logger.error(f"Error updating user session: {str(e)}")
        return False