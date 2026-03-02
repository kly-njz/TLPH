// Import the functions you need from the SDKs you need
import { initializeApp, getApps } from "https://www.gstatic.com/firebasejs/10.8.0/firebase-app.js";
import { getAuth, signInWithEmailAndPassword, createUserWithEmailAndPassword, GoogleAuthProvider, signInWithPopup, onAuthStateChanged } from "https://www.gstatic.com/firebasejs/10.8.0/firebase-auth.js";
import { getFirestore } from "https://www.gstatic.com/firebasejs/10.8.0/firebase-firestore.js";
import { getStorage } from "https://www.gstatic.com/firebasejs/10.8.0/firebase-storage.js";

// Your web app's Firebase configuration
const firebaseConfig = {
  apiKey: "AIzaSyBpdvsvmF5JI7B50L8P_f9Q_OULRSCm9w4",
  authDomain: "tlph-denr-system.firebaseapp.com",
  projectId: "tlph-denr-system",
  storageBucket: "tlph-denr-system.appspot.com",
  messagingSenderId: "999028568640",
  appId: "1:999028568640:web:2b488c8ea8e24ba39f19eb",
  measurementId: "G-TXKQ1Z0J1X"
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

