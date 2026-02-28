// Device type detection
function getDeviceType() {
    const ua = navigator.userAgent;
    if (/mobile/i.test(ua)) return 'Mobile';
    if (/tablet/i.test(ua)) return 'Tablet';
    if (/iPad|Android|Touch/.test(ua)) return 'Tablet';
    if (/Macintosh|Windows|Linux/.test(ua)) return 'Desktop';
    return 'Unknown';
}
import { auth, onAuthStateChanged } from "./firebase-config.js";
import { saveLicenseApplicationToFirebase, collectLicenseFormData } from "./license-firebase-storage.js";

const EMAIL_TIMEOUT_MS = 1500;
let cachedEmail = "";
let cachedUserId = "";
let emailPromise = null;

function getCurrentUserEmail() {
    if (cachedEmail) {
        return Promise.resolve(cachedEmail);
    }
    if (emailPromise) {
        return emailPromise;
    }
    emailPromise = new Promise((resolve) => {
        const timeoutId = setTimeout(() => {
            resolve("");
        }, EMAIL_TIMEOUT_MS);

        const unsubscribe = onAuthStateChanged(auth, (user) => {
            clearTimeout(timeoutId);
            if (typeof unsubscribe === "function") {
                unsubscribe();
            }
            cachedEmail = user && user.email ? user.email : "";
            cachedUserId = user && user.uid ? user.uid : "";
            resolve(cachedEmail);
        });
    });

    return emailPromise;
}

function getCurrentUserId() {
    return cachedUserId;
}

function slugify(value) {
    return (value || "")
        .toString()
        .toLowerCase()
        .trim()
        .replace(/[^a-z0-9]+/g, "-")
        .replace(/^-+|-+$/g, "");
}

function getItemName(form) {
    const pageHeading = Array.from(document.querySelectorAll("h1")).find(
        (heading) => !heading.closest("header")
    );

    return form.dataset.itemName
        || (pageHeading && pageHeading.textContent.trim())
        || document.title
        || "License Application";
}

function getDescription(form, itemName) {
    return form.dataset.description || itemName;
}

function getExternalPrefix(form, itemName) {
    return form.dataset.externalPrefix || slugify(itemName) || "license";
}

function getSuccessUrl() {
    const form = document.querySelector("form");
    if (form && form.dataset.successUrl) {
        return form.dataset.successUrl;
    }
    // Default redirect to transaction page after license application
    if (window.location.pathname.includes('/user/license/')) {
        return `${window.location.origin}/user/transaction`;
    }
    return window.location.href.split("#")[0];
}

function getFailureUrl() {
    return window.location.href.split("#")[0];
}

async function handlePaymentSubmit(event, form) {
    const amountInput = form.querySelector("#xendit_raw_amount");
    if (!amountInput) {
        return;
    }

    event.preventDefault();
    event.stopImmediatePropagation();

    const submitBtn = form.querySelector("button[type='submit']");
    if (submitBtn) {
        submitBtn.disabled = true;
        submitBtn.textContent = 'Saving application...';
    }

    const amount = parseInt(amountInput.value, 10);
    const itemName = getItemName(form);
    const description = getDescription(form, itemName);
    const externalPrefix = getExternalPrefix(form, itemName);

    try {
        const email = await getCurrentUserEmail();
        if (!email) {
            alert("Please sign in before continuing with payment.");
            if (submitBtn) {
                submitBtn.disabled = false;
                submitBtn.textContent = 'Apply Now';
            }
            return;
        }
        localStorage.setItem("denr_user_email", email);
        
        const externalId = `${externalPrefix}-${Date.now()}`;
        
        // Collect and save form data to Firebase
        try {
            console.log('Collecting form data...');
            const formData = collectLicenseFormData('form');
            console.log('Form data collected:', formData.applicationType);
            
            if (submitBtn) {
                submitBtn.textContent = 'Uploading documents...';
            }
            
            formData.externalId = externalId;
            formData.amount = amount;
            
            console.log('Starting Firebase save...');
            await saveLicenseApplicationToFirebase(formData);
            console.log('Firebase save completed successfully');
            
            if (submitBtn) {
                submitBtn.textContent = 'Processing payment...';
            }
        } catch (firebaseError) {
            console.error('Firebase save error:', firebaseError);
            let errorMessage = 'Error saving application data. Please try again.';
            if (firebaseError.message.includes('not authenticated')) {
                errorMessage = 'Please sign in before submitting the application.';
            } else if (firebaseError.message.includes('No files')) {
                errorMessage = 'Please upload all required documents.';
            } else if (firebaseError.message.includes('Failed to upload')) {
                errorMessage = 'Failed to upload documents. Please check file size and try again.';
            } else if (firebaseError.message.includes('User not authenticated')) {
                errorMessage = 'You must be logged in to submit an application.';
            }
            alert(errorMessage);
            if (submitBtn) {
                submitBtn.disabled = false;
                submitBtn.textContent = 'Apply Now';
            }
            return;
        }
        
        const payload = {
            external_id: externalId,
            amount: amount,
            email: email,
            user_id: getCurrentUserId(),
            description: description,
            item_name: itemName,
            success_url: getSuccessUrl(),
            failure_url: getFailureUrl(),
            device_type: getDeviceType()
        };

        const response = await fetch("/api/payments/create-invoice", {
            method: "POST",
            headers: {
                "Content-Type": "application/json"
            },
            body: JSON.stringify(payload)
        });

        const result = await response.json();

        if (result.status === "success" && result.invoice_url) {
            window.location.href = result.invoice_url;
            return;
        }

        const details = result.details ? `\n${JSON.stringify(result.details)}` : "";
        alert(`Payment error: ${result.message || "Unknown error"}${details}`);
    } catch (error) {
        console.error("Payment error:", error);
        alert("Failed to process payment. Please try again.");
    } finally {
        if (submitBtn) {
            submitBtn.disabled = false;
            submitBtn.textContent = 'Apply Now';
        }
    }
}

function bindPayments() {
    const forms = Array.from(document.querySelectorAll("form"));
    forms.forEach((form) => {
        if (!form.querySelector("#xendit_raw_amount")) {
            return;
        }
        form.addEventListener(
            "submit",
            (event) => {
                handlePaymentSubmit(event, form);
            },
            true
        );
    });
}

if (document.readyState === "loading") {
    document.addEventListener("DOMContentLoaded", bindPayments);
} else {
    bindPayments();
}
