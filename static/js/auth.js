// Import Firebase
import { app, auth, signInWithEmailAndPassword, createUserWithEmailAndPassword, googleProvider, signInWithPopup } from './firebase-config.js';
import { getFirestore, doc, setDoc, getDoc } from "https://www.gstatic.com/firebasejs/10.8.0/firebase-firestore.js";
import { setPersistence, browserLocalPersistence, browserSessionPersistence } from "https://www.gstatic.com/firebasejs/10.8.0/firebase-auth.js";
import { philippineLocations } from './ph-locations.js';

// Initialize Firestore
const db = getFirestore(app);

// Registration state
let registrationData = {};
let verificationId = null;

// Email validation helper
function validateEmail(email) {
    const re = /^[^\s@]+@[^\s@]+\.[^\s@]+$/;
    return re.test(email);
}

// Initialize location dropdowns
function initializeLocationDropdowns() {
    const provinceSelects = ['province', 'coopProvince', 'businessProvince', 'institutionProvince'];
    const provinces = Object.keys(philippineLocations).sort();
    
    // Populate all province dropdowns
    provinceSelects.forEach(selectId => {
        const selectElement = document.getElementById(selectId);
        if (selectElement) {
            provinces.forEach(province => {
                const option = document.createElement('option');
                option.value = province;
                option.textContent = province;
                selectElement.appendChild(option);
            });
        }
    });
    
    // Set up province change listeners
    setupProvinceListener('province', 'municipality');
    setupProvinceListener('coopProvince', 'coopMunicipality');
    setupProvinceListener('businessProvince', 'businessMunicipality');
    setupProvinceListener('institutionProvince', 'institutionMunicipality');
}

function setupProvinceListener(provinceId, municipalityId) {
    const provinceSelect = document.getElementById(provinceId);
    const municipalitySelect = document.getElementById(municipalityId);
    
    if (provinceSelect && municipalitySelect) {
        provinceSelect.addEventListener('change', function() {
            const selectedProvince = this.value;
            
            // Clear and reset municipality dropdown
            municipalitySelect.innerHTML = '<option value="">Select Municipality</option>';
            municipalitySelect.disabled = !selectedProvince;
            
            if (selectedProvince && philippineLocations[selectedProvince]) {
                const municipalities = philippineLocations[selectedProvince].sort();
                municipalities.forEach(municipality => {
                    const option = document.createElement('option');
                    option.value = municipality;
                    option.textContent = municipality;
                    municipalitySelect.appendChild(option);
                });
            }
        });
    }
}

// Handle application type change
document.addEventListener('DOMContentLoaded', function() {
    // Initialize location dropdowns
    initializeLocationDropdowns();
    
    const appTypeSelect = document.getElementById('applicationType');
    if (appTypeSelect) {
        appTypeSelect.addEventListener('change', function() {
            updateFormFields(this.value);
        });
    }
});

function updateFormFields(applicationType) {
    const firstNameGroup = document.getElementById('firstNameGroup');
    const lastNameGroup = document.getElementById('lastNameGroup');
    const firstNameLabel = document.getElementById('firstNameLabel');
    const lastNameLabel = document.getElementById('lastNameLabel');
    const firstNameInput = document.getElementById('firstName');
    const lastNameInput = document.getElementById('lastName');
    
    const tenantFields = document.getElementById('tenantFields');
    const cooperativeFields = document.getElementById('cooperativeFields');
    const agribusinessFields = document.getElementById('agribusinessFields');
    const researchFields = document.getElementById('researchFields');
    
    // Hide all fields first
    if (tenantFields) tenantFields.style.display = 'none';
    if (cooperativeFields) cooperativeFields.style.display = 'none';
    if (agribusinessFields) agribusinessFields.style.display = 'none';
    if (researchFields) researchFields.style.display = 'none';
    
    if (applicationType === 'cooperative') {
        // Change to Cooperative fields in Step 1
        firstNameLabel.innerHTML = 'Cooperative Name <span class="required">*</span>';
        lastNameLabel.innerHTML = 'Contact Person Name <span class="required">*</span>';
        firstNameInput.placeholder = 'Enter cooperative name';
        lastNameInput.placeholder = 'Contact person full name';
        
        // Show cooperative fields in Step 3
        if (cooperativeFields) cooperativeFields.style.display = 'block';
        
        // Update required status for cooperative
        setRequiredFields(['cdaNumber', 'registrationDate', 'officeAddress', 'coopMunicipality', 'coopProvince', 'primaryActivity'], true);
        setRequiredFields(['address', 'municipality', 'province', 'businessRegNumber', 'businessType', 'businessRegDate', 'businessAddress', 'businessMunicipality', 'businessProvince', 'natureOfBusiness', 'businessScale', 'accreditationNumber', 'institutionType', 'institutionAddress', 'institutionMunicipality', 'institutionProvince', 'researchFocus'], false);
        
    } else if (applicationType === 'agribusiness') {
        // Change to Agribusiness Company fields in Step 1
        firstNameLabel.innerHTML = 'Company Name <span class="required">*</span>';
        lastNameLabel.innerHTML = 'Authorized Representative Name <span class="required">*</span>';
        firstNameInput.placeholder = 'Enter company name';
        lastNameInput.placeholder = 'Representative full name';
        
        // Show agribusiness fields in Step 3
        if (agribusinessFields) agribusinessFields.style.display = 'block';
        
        // Update required status for agribusiness
        setRequiredFields(['businessRegNumber', 'businessType', 'businessRegDate', 'businessAddress', 'businessMunicipality', 'businessProvince', 'natureOfBusiness', 'businessScale'], true);
        setRequiredFields(['address', 'municipality', 'province', 'cdaNumber', 'registrationDate', 'officeAddress', 'coopMunicipality', 'coopProvince', 'primaryActivity', 'accreditationNumber', 'institutionType', 'institutionAddress', 'institutionMunicipality', 'institutionProvince', 'researchFocus'], false);
        
    } else if (applicationType === 'research') {
        // Change to Research Institution fields in Step 1
        firstNameLabel.innerHTML = 'Institution Name <span class="required">*</span>';
        lastNameLabel.innerHTML = 'Contact Person Name <span class="required">*</span>';
        firstNameInput.placeholder = 'Enter institution name';
        lastNameInput.placeholder = 'Contact person full name';
        
        // Show research fields in Step 3
        if (researchFields) researchFields.style.display = 'block';
        
        // Update required status for research institution
        setRequiredFields(['accreditationNumber', 'institutionType', 'institutionAddress', 'institutionMunicipality', 'institutionProvince', 'researchFocus'], true);
        setRequiredFields(['address', 'municipality', 'province', 'cdaNumber', 'registrationDate', 'officeAddress', 'coopMunicipality', 'coopProvince', 'primaryActivity', 'businessRegNumber', 'businessType', 'businessRegDate', 'businessAddress', 'businessMunicipality', 'businessProvince', 'natureOfBusiness', 'businessScale'], false);
        
    } else {
        // Default to Tenant/Individual fields
        firstNameLabel.innerHTML = 'First Name <span class="required">*</span>';
        lastNameLabel.innerHTML = 'Last Name <span class="required">*</span>';
        firstNameInput.placeholder = 'First name';
        lastNameInput.placeholder = 'Last name';
        
        // Show tenant fields in Step 3
        if (tenantFields) tenantFields.style.display = 'block';
        
        // Update required status for tenant
        setRequiredFields(['address', 'municipality', 'province'], true);
        setRequiredFields(['cdaNumber', 'registrationDate', 'officeAddress', 'coopMunicipality', 'coopProvince', 'primaryActivity', 'businessRegNumber', 'businessType', 'businessRegDate', 'businessAddress', 'businessMunicipality', 'businessProvince', 'natureOfBusiness', 'businessScale', 'accreditationNumber', 'institutionType', 'institutionAddress', 'institutionMunicipality', 'institutionProvince', 'researchFocus'], false);
    }
}

function setRequiredFields(fieldIds, isRequired) {
    fieldIds.forEach(id => {
        const field = document.getElementById(id);
        if (field) {
            field.required = isRequired;
        }
    });
}

// Multi-step navigation
window.goToStep = function(stepNumber) {
    document.querySelectorAll('.form-step').forEach(step => {
        step.classList.remove('active');
    });
    document.getElementById('step' + stepNumber).classList.add('active');
    
    // If going to step 3a, update form fields based on application type
    if (stepNumber === '3a') {
        const applicationType = registrationData.applicationType || document.getElementById('applicationType').value;
        if (applicationType) {
            updateFormFields(applicationType);
        }
    }
}

// Validate Step 3A and proceed to Step 3B
window.validateAndGoToStep3b = function() {
    const applicationType = registrationData.applicationType;
    let isValid = true;
    let missingFields = [];
    
    if (applicationType === 'tenant') {
        const address = document.getElementById('address').value;
        const province = document.getElementById('province').value;
        const municipality = document.getElementById('municipality').value;
        
        if (!address) missingFields.push('Address');
        if (!province) missingFields.push('Province');
        if (!municipality) missingFields.push('Municipality');
        
        isValid = address && province && municipality;
        
    } else if (applicationType === 'cooperative') {
        const cdaNumber = document.getElementById('cdaNumber').value;
        const registrationDate = document.getElementById('registrationDate').value;
        const officeAddress = document.getElementById('officeAddress').value;
        const coopProvince = document.getElementById('coopProvince').value;
        const coopMunicipality = document.getElementById('coopMunicipality').value;
        const primaryActivity = document.getElementById('primaryActivity').value;
        
        if (!cdaNumber) missingFields.push('CDA Number');
        if (!registrationDate) missingFields.push('Registration Date');
        if (!officeAddress) missingFields.push('Office Address');
        if (!coopProvince) missingFields.push('Province');
        if (!coopMunicipality) missingFields.push('Municipality');
        if (!primaryActivity) missingFields.push('Primary Activity');
        
        isValid = cdaNumber && registrationDate && officeAddress && coopProvince && coopMunicipality && primaryActivity;
        
    } else if (applicationType === 'agribusiness') {
        const businessRegNumber = document.getElementById('businessRegNumber').value;
        const businessType = document.getElementById('businessType').value;
        const businessRegDate = document.getElementById('businessRegDate').value;
        const businessAddress = document.getElementById('businessAddress').value;
        const businessProvince = document.getElementById('businessProvince').value;
        const businessMunicipality = document.getElementById('businessMunicipality').value;
        const natureOfBusiness = document.getElementById('natureOfBusiness').value;
        const businessScale = document.getElementById('businessScale').value;
        
        if (!businessRegNumber) missingFields.push('Business Registration Number');
        if (!businessType) missingFields.push('Business Type');
        if (!businessRegDate) missingFields.push('Registration Date');
        if (!businessAddress) missingFields.push('Business Address');
        if (!businessProvince) missingFields.push('Province');
        if (!businessMunicipality) missingFields.push('Municipality');
        if (!natureOfBusiness) missingFields.push('Nature of Business');
        if (!businessScale) missingFields.push('Business Scale');
        
        isValid = businessRegNumber && businessType && businessRegDate && businessAddress && businessProvince && businessMunicipality && natureOfBusiness && businessScale;
        
    } else if (applicationType === 'research') {
        const accreditationNumber = document.getElementById('accreditationNumber').value;
        const institutionType = document.getElementById('institutionType').value;
        const institutionAddress = document.getElementById('institutionAddress').value;
        const institutionProvince = document.getElementById('institutionProvince').value;
        const institutionMunicipality = document.getElementById('institutionMunicipality').value;
        const researchFocus = document.getElementById('researchFocus').value;
        
        if (!accreditationNumber) missingFields.push('Accreditation Number');
        if (!institutionType) missingFields.push('Institution Type');
        if (!institutionAddress) missingFields.push('Institution Address');
        if (!institutionProvince) missingFields.push('Province');
        if (!institutionMunicipality) missingFields.push('Municipality');
        if (!researchFocus) missingFields.push('Research Focus');
        
        isValid = accreditationNumber && institutionType && institutionAddress && institutionProvince && institutionMunicipality && researchFocus;
    }
    
    if (isValid) {
        goToStep('3b');
    } else {
        alert('Please fill in all required fields:\n- ' + missingFields.join('\n- '));
    }
}

// Send OTP
window.sendOTP = async function() {
    const firstName = document.getElementById('firstName').value;
    const lastName = document.getElementById('lastName').value;
    const email = document.getElementById('email').value;
    const phone = document.getElementById('phone').value;
    const applicationType = document.getElementById('applicationType').value;
    
    // Validation
    if (!applicationType || !firstName || !lastName || !email || !phone) {
        alert('Please fill in all required fields');
        return;
    }
    
    if (!validateEmail(email)) {
        alert('Please enter a valid email address');
        return;
    }
    
    // Store data
    registrationData = { firstName, lastName, email, phone, applicationType };
    
    try {
        // Call backend to send OTP
        const response = await fetch('/api/send-otp', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
            },
            body: JSON.stringify({ email: email })
        });
        
        const result = await response.json();
        
        if (result.success) {
            alert('OTP has been sent to your email address. Please check your inbox.');
            goToStep(2);
        } else {
            alert('Failed to send OTP: ' + result.message);
        }
    } catch (error) {
        console.error('Error sending OTP:', error);
        alert('Error sending OTP: ' + error.message);
    }
}

// Resend OTP
window.resendOTP = function() {
    sendOTP();
}

// Verify OTP
window.verifyOTP = async function() {
    const otpCode = document.getElementById('otpCode').value;
    
    if (!otpCode || otpCode.length !== 6) {
        alert('Please enter a valid 6-digit OTP code');
        return;
    }
    
    try {
        // Call backend to verify OTP
        const response = await fetch('/api/verify-otp', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
            },
            body: JSON.stringify({ 
                email: registrationData.email,
                otp: otpCode 
            })
        });
        
        const result = await response.json();
        
        if (result.success) {
            alert('Email verified successfully!');
            goToStep('3a');
        } else {
            alert('Verification failed: ' + result.message);
        }
    } catch (error) {
        console.error('Error verifying OTP:', error);
        alert('Error verifying OTP: ' + error.message);
    }
}

// Signup Form Handler
const signupForm = document.getElementById('signupForm');
if (signupForm) {
    signupForm.addEventListener('submit', async function(e) {
        e.preventDefault();
        
        const password = document.getElementById('password').value;
        const confirmPassword = document.getElementById('confirmPassword').value;
        const terms = document.querySelector('input[name="terms"]').checked;
        const applicationType = registrationData.applicationType;
        
        // Get fields based on application type
        let profileData = {};
        
        if (applicationType === 'cooperative') {
            const cdaNumber = document.getElementById('cdaNumber').value;
            const registrationDate = document.getElementById('registrationDate').value;
            const officeAddress = document.getElementById('officeAddress').value;
            const coopMunicipality = document.getElementById('coopMunicipality').value;
            const coopProvince = document.getElementById('coopProvince').value;
            const primaryActivity = document.getElementById('primaryActivity').value;
            
            // Validation for cooperative
            if (!cdaNumber || !registrationDate || !officeAddress || !coopMunicipality || !coopProvince || !primaryActivity || !password || !confirmPassword) {
                alert('Please fill in all required fields');
                return;
            }
            
            profileData = {
                cdaNumber,
                registrationDate,
                officeAddress,
                municipality: coopMunicipality,
                province: coopProvince,
                primaryActivity
            };
        } else if (applicationType === 'agribusiness') {
            const businessRegNumber = document.getElementById('businessRegNumber').value;
            const businessType = document.getElementById('businessType').value;
            const businessRegDate = document.getElementById('businessRegDate').value;
            const businessAddress = document.getElementById('businessAddress').value;
            const businessMunicipality = document.getElementById('businessMunicipality').value;
            const businessProvince = document.getElementById('businessProvince').value;
            const natureOfBusiness = document.getElementById('natureOfBusiness').value;
            const businessScale = document.getElementById('businessScale').value;
            
            // Validation for agribusiness
            if (!businessRegNumber || !businessType || !businessRegDate || !businessAddress || !businessMunicipality || !businessProvince || !natureOfBusiness || !businessScale || !password || !confirmPassword) {
                alert('Please fill in all required fields');
                return;
            }
            
            profileData = {
                businessRegNumber,
                businessType,
                registrationDate: businessRegDate,
                businessAddress,
                municipality: businessMunicipality,
                province: businessProvince,
                natureOfBusiness,
                businessScale
            };
        } else if (applicationType === 'research') {
            const accreditationNumber = document.getElementById('accreditationNumber').value;
            const institutionType = document.getElementById('institutionType').value;
            const institutionAddress = document.getElementById('institutionAddress').value;
            const institutionMunicipality = document.getElementById('institutionMunicipality').value;
            const institutionProvince = document.getElementById('institutionProvince').value;
            const researchFocus = document.getElementById('researchFocus').value;
            
            // Validation for research institution
            if (!accreditationNumber || !institutionType || !institutionAddress || !institutionMunicipality || !institutionProvince || !researchFocus || !password || !confirmPassword) {
                alert('Please fill in all required fields');
                return;
            }
            
            profileData = {
                accreditationNumber,
                institutionType,
                institutionAddress,
                municipality: institutionMunicipality,
                province: institutionProvince,
                researchFocus
            };
        } else {
            // Tenant/Individual and other types
            const address = document.getElementById('address').value;
            const municipality = document.getElementById('municipality').value;
            const province = document.getElementById('province').value;
            const farmSize = document.getElementById('farmSize').value;
            const cropType = document.getElementById('cropType').value;
            
            // Validation for tenant
            if (!address || !municipality || !province || !password || !confirmPassword) {
                alert('Please fill in all required fields');
                return;
            }
            
            profileData = {
                address,
                municipality,
                province,
                farmSize: farmSize || null,
                cropType: cropType || null
            };
        }
        
        if (password.length < 8) {
            alert('Password must be at least 8 characters long');
            return;
        }
        
        if (password !== confirmPassword) {
            alert('Passwords do not match');
            return;
        }
        
        if (!terms) {
            alert('Please agree to the Terms of Service and Privacy Policy');
            return;
        }
        
        try {
            // Create user with Firebase Authentication
            const userCredential = await createUserWithEmailAndPassword(auth, registrationData.email, password);
            const user = userCredential.user;
            
            // Determine role based on application type
            let userRole = 'user';
            const appType = registrationData.applicationType;
            
            if (appType === 'municipal') userRole = 'municipal';
            else if (appType === 'national') userRole = 'national';
            else if (appType === 'regional') userRole = 'regional';
            else if (appType === 'super-admin') userRole = 'super-admin';
            
            // Save user profile to Firestore with role
            await setDoc(doc(db, 'users', user.uid), {
                firstName: registrationData.firstName,
                lastName: registrationData.lastName,
                email: registrationData.email,
                phone: registrationData.phone,
                applicationType: registrationData.applicationType,
                role: userRole,
                ...profileData,
                userType: 'farmer',
                status: 'pending',
                createdAt: new Date().toISOString()
            });
            
            console.log('Registration successful:', user);
            alert('Registration successful!');
            
            // Redirect based on role
            if (userRole === 'municipal') {
                window.location.href = '/municipal/dashboard';
            } else if (userRole === 'national') {
                window.location.href = '/national/dashboard';
            } else if (userRole === 'regional') {
                window.location.href = '/regional/dashboard';
            } else if (userRole === 'super-admin') {
                window.location.href = '/super-admin/dashboard';
            } else {
                window.location.href = '/approval-status';
            }
        } catch (error) {
            console.error('Registration error:', error);
            alert('Registration failed: ' + error.message);
        }
    });
}

// Login Form Handler
const loginForm = document.getElementById('loginForm');
if (loginForm) {
    // Load saved email if exists
    const savedEmail = localStorage.getItem('rememberedEmail');
    if (savedEmail) {
        document.getElementById('email').value = savedEmail;
        document.querySelector('input[name="remember"]').checked = true;
    }
    
    loginForm.addEventListener('submit', async function(e) {
        e.preventDefault();
        
        const email = document.getElementById('email').value;
        const password = document.getElementById('password').value;
        const rememberMe = document.querySelector('input[name="remember"]').checked;
        const loginBtn = document.getElementById('loginBtn');
        
        // Frontend validation
        if (!email || !password) {
            alert('Please fill in all fields');
            return;
        }
        
        if (!validateEmail(email)) {
            alert('Please enter a valid email address');
            return;
        }
        
        // Show loading on button
        if (loginBtn) {
            loginBtn.classList.add('loading');
            loginBtn.disabled = true;
        }
        
        try {
            // Set Firebase persistence based on remember me
            if (rememberMe) {
                await setPersistence(auth, browserLocalPersistence);
                localStorage.setItem('rememberedEmail', email);
            } else {
                await setPersistence(auth, browserSessionPersistence);
                localStorage.removeItem('rememberedEmail');
            }
            
            // Sign in with Firebase
            const userCredential = await signInWithEmailAndPassword(auth, email, password);
            const user = userCredential.user;
            
            console.log('Login successful:', user);
            
            // Get user role from Firestore
            const userDocRef = doc(db, 'users', user.uid);
            const userDocSnap = await getDoc(userDocRef);
            
            if (userDocSnap.exists()) {
                const userData = userDocSnap.data();
                const userRole = userData.role || 'user';
                
                console.log('User role:', userRole);
                
                // Set Flask session
                await fetch('/api/set-session', {
                    method: 'POST',
                    headers: {
                        'Content-Type': 'application/json',
                    },
                    body: JSON.stringify({
                        user_email: user.email,
                        user_role: userRole
                    })
                });
                
                // Redirect based on role
                if (userRole === 'municipal') {
                    window.location.href = '/municipal/dashboard';
                } else if (userRole === 'national') {
                    window.location.href = '/national/dashboard';
                } else if (userRole === 'regional') {
                    window.location.href = '/regional/dashboard';
                } else if (userRole === 'super-admin') {
                    window.location.href = '/super-admin/dashboard';
                } else {
                    window.location.href = '/user/dashboard';
                }
            } else {
                // Default to user dashboard if no role found
                window.location.href = '/user/dashboard';
            }
        } catch (error) {
            console.error('Login error:', error);
            // Hide loading on button
            if (loginBtn) {
                loginBtn.classList.remove('loading');
                loginBtn.disabled = false;
            }
            alert('Login failed: ' + error.message);
        }
    });
}

// Google Sign In
const googleButtons = document.querySelectorAll('.btn-google');
googleButtons.forEach(button => {
    button.addEventListener('click', async function() {
        try {
            const result = await signInWithPopup(auth, googleProvider);
            const user = result.user;
            
            console.log('Google sign in successful:', user);
            
            // Redirect to user dashboard
            window.location.href = '/user/dashboard';
        } catch (error) {
            console.error('Google sign in error:', error);
            alert('Google sign in failed: ' + error.message);
        }
    });
});

// Initialize
document.addEventListener('DOMContentLoaded', function() {
    console.log('Auth page loaded');
});
