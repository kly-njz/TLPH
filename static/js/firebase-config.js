// Import the functions you need from the SDKs you need
import { initializeApp, getApps } from "https://www.gstatic.com/firebasejs/10.8.0/firebase-app.js";
import { getAuth, signInWithEmailAndPassword, createUserWithEmailAndPassword, GoogleAuthProvider, signInWithPopup, onAuthStateChanged } from "https://www.gstatic.com/firebasejs/10.8.0/firebase-auth.js";
import { getFirestore } from "https://www.gstatic.com/firebasejs/10.8.0/firebase-firestore.js";
import { getStorage } from "https://www.gstatic.com/firebasejs/10.8.0/firebase-storage.js";

// Your web app's Firebase configuration
const firebaseConfig = {
  apiKey: "AIzaSyCj3EnEG1XhF7_xWgt1vQK_VkT7288yd64",
  authDomain: "denr-d02ae.firebaseapp.com",
  projectId: "denr-d02ae",
  storageBucket: "denr-d02ae.firebasestorage.app",
  messagingSenderId: "499245517370",
  appId: "1:499245517370:web:c66598d7c86d5567a64303"
};

// Initialize Firebase safely (avoid duplicate-app errors)
const app = getApps().length ? getApps()[0] : initializeApp(firebaseConfig);
const auth = getAuth(app);
const db = getFirestore(app);
const storage = getStorage(app);
const googleProvider = new GoogleAuthProvider();

// Expose to global scope
window.app = app;
window.auth = auth;
window.db = db;
window.storage = storage;
window.googleProvider = googleProvider;

export { app, auth, db, storage, signInWithEmailAndPassword, createUserWithEmailAndPassword, googleProvider, signInWithPopup, onAuthStateChanged };

