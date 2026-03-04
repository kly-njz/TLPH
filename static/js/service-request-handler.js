/**
 * Service Request Handler
 * Manages Firebase storage and Xendit payment for all service requests
 * Usage: import { submitServiceRequest } from '/static/js/service-request-handler.js'
 */

import { auth, db } from '/static/js/firebase-config.js';
import { collection, addDoc, doc, getDoc } from 'https://www.gstatic.com/firebasejs/10.8.0/firebase-firestore.js';

/**
 * Submit a service request with payment
 * @param {Object} config Configuration object
 * @param {string} config.formId - ID of the form element
 * @param {string} config.submitBtnId - ID of the submit button
 * @param {string} config.serviceType - Type of service (e.g., "Initial Farm Visit")
 * @param {Object} config.formData - Form fields to capture (key: field_id, value: field_name)
 * @param {number} config.amount - Payment amount in PHP
 * @param {string} config.itemName - Item name for invoice
 * @param {string} config.description - Payment description
 * @param {string} config.successUrl - URL after successful payment
 * @param {string} config.failureUrl - URL after failed payment
 * @param {Function} config.onPreSubmit - Optional callback before submission
 * @param {Function} config.onSuccess - Optional callback on success
 * @param {Function} config.onError - Optional callback on error
 * @returns {void}
 */
export async function submitServiceRequest(config) {
  const form = document.getElementById(config.formId);
  const submitBtn = document.getElementById(config.submitBtnId);
  const btnText = submitBtn.querySelector('span') || submitBtn;

  if (!form || !submitBtn) {
    console.error('Form or button not found');
    return;
  }

  // Mark as handled to avoid auto-binding on the same form
  form.dataset.serviceHandler = 'manual';

  form.addEventListener('submit', async (e) => {
    e.preventDefault();

    try {
      // Check if user is authenticated
      if (!auth.currentUser) {
        alert('Please login to submit service request');
        window.location.href = '/login';
        return;
      }

      // Change button state
      const originalText = btnText.textContent;
      btnText.textContent = 'Processing Payment...';
      submitBtn.disabled = true;

      // Call pre-submit callback if provided
      if (config.onPreSubmit) {
        await config.onPreSubmit();
      }

      // Capture form data
      const serviceData = {
        userId: auth.currentUser.uid,
        userEmail: auth.currentUser.email,
        serviceType: config.serviceType,
        status: 'pending',
        paymentStatus: 'pending',
        createdAt: new Date().toISOString()
      };

      // Enrich with user profile data (municipality, province, barangay, name) for proper routing
      try {
        const userDoc = await getDoc(doc(db, 'users', auth.currentUser.uid));
        if (userDoc.exists()) {
          const ud = userDoc.data();
          serviceData.municipality = ud.municipality || '';
          serviceData.province = ud.province || '';
          serviceData.barangay = ud.barangay || ud.address || '';
          serviceData.userName = `${ud.firstName || ''} ${ud.lastName || ''}`.trim() || auth.currentUser.email || '';
          serviceData.region = ud.region || '';
        }
      } catch (profileErr) {
        console.warn('Could not enrich service data with user profile:', profileErr);
      }

      // Add form fields to serviceData (auto-capture if formData not provided)
      if (config.formData && Object.keys(config.formData).length > 0) {
        for (const [fieldId, fieldName] of Object.entries(config.formData)) {
          const element = document.getElementById(fieldId);
          if (element) {
            if (element.type === 'file') {
              // For file inputs, store file names and count
              const files = element.files;
              if (files.length > 0) {
                serviceData[fieldName] = Array.from(files).map(f => f.name);
                serviceData[`${fieldName}Count`] = files.length;
              }
            } else if (element.tagName === 'TEXTAREA' || element.tagName === 'INPUT' || element.tagName === 'SELECT') {
              serviceData[fieldName] = element.value;
            }
          }
        }
      } else {
        captureAllFields(form, serviceData);
      }

      // Create Xendit invoice
      const amount = parseInt(document.getElementById('xendit_raw_amount')?.value || config.amount) || config.amount;
      
      const invoiceResponse = await fetch('/api/payments/create-invoice', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json'
        },
        body: JSON.stringify({
          amount: amount,
          email: auth.currentUser.email,
          external_id: `service-${config.serviceType.replace(/[^a-zA-Z0-9]/g, '-').replace(/-+/g, '-')}-${auth.currentUser.uid}-${Date.now()}`,
          description: config.description,
          item_name: config.itemName,
          success_url: config.successUrl,
          failure_url: config.failureUrl
        })
      });

      const invoiceData = await invoiceResponse.json();

      if (invoiceData.status !== 'success') {
        throw new Error(invoiceData.message || 'Failed to create invoice');
      }

      // Store service request in Firebase
      const serviceRequestData = {
        ...serviceData,
        invoiceId: invoiceData.invoice_id,
        externalId: invoiceData.external_id,
        amount: amount
      };
      
      const docRef = await addDoc(collection(db, 'service_requests'), serviceRequestData);

      console.log('Service request saved with ID:', docRef.id);

      // Store data in localStorage for confirmation page
      localStorage.setItem('pendingServiceRequest', JSON.stringify(serviceRequestData));
      localStorage.setItem('servicePaymentUrl', invoiceData.invoice_url);

      // Call success callback if provided
      if (config.onSuccess) {
        await config.onSuccess(invoiceData);
      }

      // Redirect to confirmation page
      window.location.href = '/user/service-confirmation';

    } catch (error) {
      console.error('Error processing service request:', error);
      alert('Error: ' + error.message);
      
      // Call error callback if provided
      if (config.onError) {
        config.onError(error);
      }

      // Reset button
      btnText.textContent = originalText;
      submitBtn.disabled = false;
    }
  });
}

/**
 * Handle free service requests (no payment required)
 * @param {Object} config Configuration object (same as submitServiceRequest but without payment fields)
 * @returns {void}
 */
export async function submitFreeServiceRequest(config) {
  const form = document.getElementById(config.formId);
  const submitBtn = document.getElementById(config.submitBtnId);
  const btnText = submitBtn.querySelector('span') || submitBtn;

  if (!form || !submitBtn) {
    console.error('Form or button not found');
    return;
  }

  // Mark as handled to avoid auto-binding on the same form
  form.dataset.serviceHandler = 'manual';

  form.addEventListener('submit', async (e) => {
    e.preventDefault();

    try {
      // Check if user is authenticated
      if (!auth.currentUser) {
        alert('Please login to submit service request');
        window.location.href = '/login';
        return;
      }

      // Change button state
      const originalText = btnText.textContent;
      btnText.textContent = 'Submitting...';
      submitBtn.disabled = true;

      // Call pre-submit callback if provided
      if (config.onPreSubmit) {
        await config.onPreSubmit();
      }

      // Capture form data
      const serviceData = {
        userId: auth.currentUser.uid,
        userEmail: auth.currentUser.email,
        serviceType: config.serviceType,
        status: 'pending',
        paymentStatus: 'free',
        createdAt: new Date().toISOString()
      };

      // Enrich with user profile data (municipality, province, name) for proper routing
      try {
        const userDoc = await getDoc(doc(db, 'users', auth.currentUser.uid));
        if (userDoc.exists()) {
          const ud = userDoc.data();
          serviceData.municipality = ud.municipality || '';
          serviceData.province = ud.province || '';
          serviceData.barangay = ud.barangay || ud.address || '';
          serviceData.userName = `${ud.firstName || ''} ${ud.lastName || ''}`.trim() || ud.email || '';
          serviceData.region = ud.region || '';
        }
      } catch (profileErr) {
        console.warn('Could not enrich service data with user profile:', profileErr);
      }

      // Add form fields to serviceData (auto-capture if formData not provided)
      if (config.formData && Object.keys(config.formData).length > 0) {
        for (const [fieldId, fieldName] of Object.entries(config.formData)) {
          const element = document.getElementById(fieldId);
          if (element) {
            if (element.type === 'file') {
              const files = element.files;
              if (files.length > 0) {
                serviceData[fieldName] = Array.from(files).map(f => f.name);
                serviceData[`${fieldName}Count`] = files.length;
              }
            } else if (element.tagName === 'TEXTAREA' || element.tagName === 'INPUT' || element.tagName === 'SELECT') {
              serviceData[fieldName] = element.value;
            }
          }
        }
      } else {
        captureAllFields(form, serviceData);
      }

      // Store service request in Firebase
      const docRef = await addDoc(collection(db, 'service_requests'), serviceData);

      console.log('Service request saved with ID:', docRef.id);

      // Store data in localStorage for confirmation page
      localStorage.setItem('pendingServiceRequest', JSON.stringify(serviceData));

      // Call success callback if provided
      if (config.onSuccess) {
        await config.onSuccess();
      }

      // Redirect to specified URL or confirmation page
      const redirectUrl = config.redirectUrl || '/user/service-confirmation';
      window.location.href = redirectUrl;

    } catch (error) {
      console.error('Error submitting service request:', error);
      alert('Error: ' + error.message);
      
      // Call error callback if provided
      if (config.onError) {
        config.onError(error);
      }

      // Reset button
      btnText.textContent = originalText;
      submitBtn.disabled = false;
    }
  });
}

function captureAllFields(form, target) {
  const elements = form.querySelectorAll('input, textarea, select');
  elements.forEach((element) => {
    const key = element.name || element.id;
    if (!key || element.disabled) return;

    if (element.type === 'file') {
      const files = element.files;
      if (files && files.length > 0) {
        target[key] = Array.from(files).map(f => f.name);
        target[`${key}Count`] = files.length;
      }
      return;
    }

    if (element.type === 'checkbox') {
      target[key] = element.checked;
      return;
    }

    if (element.type === 'radio') {
      if (element.checked) {
        target[key] = element.value;
      }
      return;
    }

    target[key] = element.value;
  });
}
