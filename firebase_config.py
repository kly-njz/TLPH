import firebase_admin
from firebase_admin import credentials, db, firestore
import pyrebase
from config import Config
import os

# Initialize Firebase Admin SDK
def initialize_firebase_admin():
    """Initialize Firebase Admin SDK for server-side operations"""
    try:
        if firebase_admin._apps:
            return

        if not Config.FIREBASE_CREDENTIALS or not os.path.exists(Config.FIREBASE_CREDENTIALS):
            raise FileNotFoundError("firebase-credentials.json not found. Place it in the project root.")

        cred = credentials.Certificate(Config.FIREBASE_CREDENTIALS)
        firebase_admin.initialize_app(cred, {
            'databaseURL': Config.FIREBASE_CONFIG['databaseURL']
        })
        print("Firebase Admin initialized successfully!")
    except Exception as e:
        print(f"Error initializing Firebase Admin: {e}")
        raise

# Initialize Pyrebase for client-side operations
def get_firebase_client():
    """Get Pyrebase client for authentication and client operations"""
    try:
        firebase = pyrebase.initialize_app(Config.FIREBASE_CONFIG)
        return firebase
    except Exception as e:
        print(f"Error initializing Pyrebase: {e}")
        return None

# Get Firestore database reference
def get_firestore_db():
    """Get Firestore database reference"""
    initialize_firebase_admin()
    return firestore.client()

# Get Realtime Database reference
def get_realtime_db():
    """Get Realtime Database reference"""
    return db.reference()
