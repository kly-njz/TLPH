import { auth, db, storage, onAuthStateChanged } from './firebase-config.js';
import { collection, addDoc, serverTimestamp } from "https://www.gstatic.com/firebasejs/10.8.0/firebase-firestore.js";
import { ref, uploadBytes, getDownloadURL } from "https://www.gstatic.com/firebasejs/10.8.0/firebase-storage.js";

/**
 * Get current user data
 */
export function getCurrentUser() {
    return new Promise((resolve) => {
        const unsubscribe = onAuthStateChanged(auth, (user) => {
            unsubscribe();
            resolve(user);
        });
    });
}

/**
 * Upload a single file to Firebase Storage
 */
async function uploadFileToStorage(file, userId, collectionType, filename) {
    try {
        // Validate file object
        if (!file || !file.name) {
            throw new Error('Invalid file object');
        }
        
        const timestamp = Date.now();
        const fileExtension = file.name.split('.').pop();
        const uniqueFilename = `${filename || file.name.split('.')[0]}_${timestamp}.${fileExtension}`;
        const storagePath = `license-applications/${userId}/${collectionType}/${uniqueFilename}`;
        
        const storageRef = ref(storage, storagePath);
        const uploadResult = await uploadBytes(storageRef, file);
        const downloadUrl = await getDownloadURL(uploadResult.ref);
        
        return {
            name: file.name,
            size: file.size,
            type: file.type,
            downloadUrl: downloadUrl,
            storagePath: storagePath,
            uploadedAt: new Date().toISOString()
        };
    } catch (error) {
        console.error('Error uploading file:', error);
        throw new Error(`Failed to upload file: ${file.name || 'unknown'} - ${error.message}`);
    }
}

/**
 * Upload multiple files to Firebase Storage
 */
async function uploadMultipleFiles(fileList, userId, collectionType, filenamePrefix) {
    try {
        // Convert FileList to array if needed
        if (!fileList || fileList.length === 0) {
            throw new Error('No files to upload');
        }
        
        const filesArray = Array.from(fileList);
        const uploadedFiles = [];
        
        for (let file of filesArray) {
            const fileData = await uploadFileToStorage(file, userId, collectionType, filenamePrefix);
            uploadedFiles.push(fileData);
        }
        
        return uploadedFiles;
    } catch (error) {
        console.error('Error uploading multiple files:', error);
        throw new Error(`File upload failed: ${error.message}`);
    }
}

/**
 * Save license application data to Firestore
 */
export async function saveLicenseApplicationToFirebase(formData) {
    try {
        console.log('Starting Firebase save with formData:', {
            appType: formData.applicationType,
            hasMainProofFiles: !!formData.mainProofFiles,
            mainProofFilesLength: formData.mainProofFiles ? formData.mainProofFiles.length : 0,
            hasPrevPermitFile: !!formData.prevPermitFile
        });
        
        // Get current user
        const user = await getCurrentUser();
        
        if (!user) {
            throw new Error('User not authenticated. Please login and try again.');
        }
        
        console.log('User authenticated:', user.email);
        
        const userId = user.uid;
        const userEmail = user.email;
        const applicationType = formData.applicationType || 'license';
        
        // Validate that we have at least some form data
        if (!formData) {
            throw new Error('No form data provided');
        }
        
        // Process file uploads first
        let uploadedFiles = {};
        
        // Validate and upload main/proof documents
        if (formData.mainProofFiles && formData.mainProofFiles.length > 0) {
            try {
                console.log('Uploading main proof files:', formData.mainProofFiles.length);
                uploadedFiles.mainProof = await uploadMultipleFiles(
                    formData.mainProofFiles,
                    userId,
                    applicationType,
                    'proof'
                );
                console.log('Main proof files uploaded successfully');
            } catch (uploadError) {
                throw new Error(`Failed to upload proof documents: ${uploadError.message}`);
            }
        }
        
        // Validate and upload previous permit if exists
        if (formData.prevPermitFile) {
            try {
                console.log('Uploading previous permit file');
                uploadedFiles.prevPermit = await uploadFileToStorage(
                    formData.prevPermitFile,
                    userId,
                    applicationType,
                    'previous-permit'
                );
                console.log('Previous permit uploaded successfully');
            } catch (e) {
                console.warn('Warning: Could not upload previous permit file:', e);
                // Continue without previous permit if it's optional
            }
        }
        
        // Prepare application data for Firestore
        const applicationData = {
            userId: userId,
            userEmail: userEmail,
            applicationType: applicationType,
            formData: {
                ...formData,
                // Remove file objects, keep only metadata
                mainProofFiles: null,
                prevPermitFile: null
            },
            uploadedFiles: uploadedFiles,
            status: 'pending',
            createdAt: serverTimestamp(),
            updatedAt: serverTimestamp(),
            paymentStatus: 'pending',
            externalId: formData.externalId || null,
            amount: formData.amount || null
        };
        
        console.log('Saving to Firestore:', {
            userId,
            applicationType,
            uploadedFilesCount: Object.keys(uploadedFiles).length
        });
        
        // Save to Firestore - BOTH collections
        const licenseCollection = collection(db, 'license_applications');
        const transactionsCollection = collection(db, 'transactions');
        
        const docRef = await addDoc(licenseCollection, applicationData);
        
        // Also save to transactions collection
        const transactionData = {
            ...applicationData,
            docId: docRef.id,
            status: 'approved',  // For transactions, mark as approved
            transactionType: 'license-application',
            transactionDate: serverTimestamp()
        };
        
        const transDocRef = await addDoc(transactionsCollection, transactionData);
        
        console.log('License application saved to Firebase:', docRef.id);
        console.log('Transaction record saved to Firebase:', transDocRef.id);
        
        return {
            success: true,
            documentId: docRef.id,
            message: 'Application data saved successfully'
        };
    } catch (error) {
        console.error('Error saving license application:', error);
        // Re-throw with more specific message
        if (error.message.includes('User not authenticated')) {
            throw error;  // Keep the original message
        }
        throw new Error(`Failed to save application: ${error.message}`);
    }
}

/**
 * Collect form data from license application form
 */
export function collectEnvironmentClearanceFormData() {
    try {
        const complianceType = document.getElementById('complianceType');
        const appType = document.getElementById('appType');
        const mainProof = document.getElementById('mainProof');
        const prevPermitInput = document.getElementById('prevPermitInput');
        const xenditAmount = document.getElementById('xendit_raw_amount');
        
        if (!complianceType || !appType || !mainProof) {
            throw new Error('Required form fields not found');
        }
        
        const formData = {
            applicationType: 'environmental-clearance',
            complianceType: complianceType.value,
            appType: appType.value,
            mainProofFiles: mainProof.files,
            prevPermitFile: prevPermitInput && prevPermitInput.files.length > 0 ? prevPermitInput.files[0] : null,
            amount: xenditAmount ? parseInt(xenditAmount.value) : null,
            submittedAt: new Date().toISOString()
        };
        
        return formData;
    } catch (error) {
        console.error('Error collecting form data:', error);
        throw error;
    }
}

/**
 * Collect form data from a generic license form
 */
export function collectLicenseFormData(formSelector = 'form', fieldsToExtract = []) {
    try {
        const form = document.querySelector(formSelector);
        if (!form) {
            throw new Error(`Form not found with selector: ${formSelector}`);
        }
        
        // Map select values to applicationType for Firebase
        const categoryToApplicationType = {
          "Import_Permit": "Import Permit",
          "Wildlife_Trade_Permit": "Wildlife Trade Permit",
          "Transport_Local_Permit": "Transport Local Permit",
          "Harvest_Permit": "Harvest Permit",
          "Meat_Transport_Shipping_Permit": "Meat Transport / Shipping Permit",
          "Slaughterhouse_Accreditation_Permit": "Slaughterhouse Accreditation Permit",
          "Poultry_Farm_Registration": "Poultry Farm Registration",
          "Animal_Health_Veterinary_Clearance": "Animal Health Veterinary Clearance",
          "Wildlife_Possession_Ownership_Permit": "Wildlife Possession & Ownership Permit",
          "Wildlife_Transport_Licensing_Permit": "Wildlife Transport Licensing Permit",
          "Wildlife_Collection_Licensing_Permit": "Wildlife Collection Licensing Permit",
          "Wildlife_Farm_&_Breeding_Registration": "Wildlife Farm & Breeding Registration",
          "Tree_Cutting_Permit": "Tree Cutting Permit",
          "Timber_Wood_/_Transfer_Permit": "Timber Wood / Transfer Permit",
          "Reforestation_Agreement": "Reforestation Agreement",
          "Nursery_Accreditation": "Nursery Accreditation",
          "Non_Timber_Collection_Permit": "Non-Timber Collection Permit",
          "Environment_Compliance_Certificate_(ECC)": "Environment Compliance Certificate (ECC)",
          "Waste_Management_Permit": "Waste Management Permit",
          "Hazardous_Material_Handling_Clearance": "Hazardous Material Handling Clearance",
          "Aquaculture_Farm_Registration": "Aquaculture Farm Registration",
          "Fish_Transport_Permit": "Fish Transport Permit",
          "Fish_Dealer_/_Trade_License": "Fish Dealer / Trade License",
          "Collection_/_Harvest_Permit": "Collection / Harvest Permit",
          "Wastewater_Discharge_Permit_(WWDP)": "Wastewater Discharge Permit (WWDP)",
          "Permit_to_Operate_(PTO)_Air_Pollution_Source_Installation/Equipment": "Permit to Operate (PTO) Air Pollution Source",
          "Hazardous_Waste_Generator_(HWG)_Registration_/_HWG_ID": "Hazardous Waste Generator (HWG) Registration",
          "PICCS_Validation_/_PICCS_Tool_Certificate": "PICCS validation / PICCS Tool certificate",
          "PCL_Compliance_Certificate": "PCL Compliance Certificate",
          "Chemical_Control_Orders_(CCOs)": "Chemical Control Orders (CCOs)",
          "Certificate_of_Tree_Plantation_Ownership_(CTPO)": "Certificate of Tree Plantation Ownership"
        };
        
        const data = {
            applicationType: 'license',
            submittedAt: new Date().toISOString(),
            formFields: {}
        };
        
        // Collect text/select inputs
        form.querySelectorAll('input[type="text"], input[type="email"], input[type="number"], input[type="date"], select, textarea').forEach(field => {
            if (field.name || field.id) {
                const key = field.name || field.id;
                data.formFields[key] = field.value;
            }
        });
        
        // Set applicationType from categorySelect if present
        const categorySelect = form.querySelector('#categorySelect');
        if (categorySelect && categorySelect.value) {
            data.applicationType = categoryToApplicationType[categorySelect.value] || categorySelect.value;
        }
        
        // Collect file inputs separately (FileList objects)
        let mainProofFound = false;
        let prevPermitFound = false;
        
        form.querySelectorAll('input[type="file"]').forEach(field => {
            if (field.id === 'mainProof' && field.files && field.files.length > 0) {
                data.mainProofFiles = field.files;
                mainProofFound = true;
            }
            if (field.id === 'prevPermitInput' && field.files && field.files.length > 0) {
                data.prevPermitFile = field.files[0];
                prevPermitFound = true;
            }
        });
        
        // Get xendit amount if available
        const xenditAmount = document.getElementById('xendit_raw_amount');
        if (xenditAmount) {
            data.amount = parseInt(xenditAmount.value) || 0;
        }
        
        // Detect application type from page heading (fallback)
        const pageHeading = Array.from(document.querySelectorAll("h1, h2")).find(
            (heading) => !heading.closest("header")
        );
        
        if (!data.applicationType && pageHeading) {
            const heading = pageHeading.textContent.toLowerCase();
            if (heading.includes('environment') || heading.includes('clearance')) {
                data.applicationType = 'environmental-clearance';
            } else if (heading.includes('fisheries')) {
                data.applicationType = 'fisheries-license';
            } else if (heading.includes('forest') || heading.includes('timber')) {
                data.applicationType = 'forest-license';
            } else if (heading.includes('livestock') || heading.includes('farm')) {
                data.applicationType = 'livestock-license';
            } else if (heading.includes('wildlife')) {
                data.applicationType = 'wildlife-license';
            }
        }
        
        console.log('Collected form data:', {
            applicationType: data.applicationType,
            hasMainProof: mainProofFound,
            hasPrevePermit: prevPermitFound,
            amount: data.amount
        });
        
        return data;
    } catch (error) {
        console.error('Error collecting form data:', error);
        throw error;
    }
}
