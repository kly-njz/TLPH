import { db } from './firebase-config.js';
import { collection, getDocs, doc, updateDoc } from "https://www.gstatic.com/firebasejs/10.8.0/firebase-firestore.js";

async function fetchAttendance() {
    const employeeCol = collection(db, 'employee');
    const employeeSnapshot = await getDocs(employeeCol);
    const employeeList = employeeSnapshot.docs.map(docSnap => ({ id: docSnap.id, ref: docSnap.ref, ...docSnap.data() }));
    return employeeList;
}

function pad(num) {
    return num.toString().padStart(2, '0');
}

function renderAttendance(employees) {
    const tbody = document.querySelector('#attendance-tbody');
    tbody.innerHTML = '';
    employees.forEach(async emp => {
        // Compose name: lastname, firstname middle initial
        const lastname = emp.lastname || '';
        const firstname = emp.first_name || '';
        const middle = emp.middle_name || '';
        const middleInitial = middle ? middle.charAt(0).toUpperCase() + '.' : '';
        const fullName = `${lastname}, ${firstname} ${middleInitial}`.trim();
        // Time-in and time-out formatting
        let inTime = '--:--';
        let inDateObj = null;
        if (emp.time_in) {
            if (typeof emp.time_in === 'string') {
                const parts = emp.time_in.split(' ');
                inTime = parts.length > 1 ? parts[1] : parts[0];
                inDateObj = new Date(emp.time_in);
            } else if (emp.time_in.toDate) {
                inDateObj = emp.time_in.toDate();
                inTime = pad(inDateObj.getHours()) + ':' + pad(inDateObj.getMinutes());
            }
        }
        let outTime = '--:--';
        let outDateObj = null;
        if (emp.time_out) {
            if (typeof emp.time_out === 'string') {
                const parts = emp.time_out.split(' ');
                outTime = parts.length > 1 ? parts[1] : parts[0];
                outDateObj = new Date(emp.time_out);
            } else if (emp.time_out.toDate) {
                outDateObj = emp.time_out.toDate();
                outTime = pad(outDateObj.getHours()) + ':' + pad(outDateObj.getMinutes());
            }
        }
        // Duration calculation (if both times are available and valid)
        let duration = '--h --m';
        if (inDateObj && outDateObj) {
            const diffMs = outDateObj - inDateObj;
            if (!isNaN(diffMs) && diffMs > 0) {
                const totalMins = Math.floor(diffMs / 60000);
                const hours = Math.floor(totalMins / 60);
                const mins = totalMins % 60;
                duration = `${pad(hours)}h ${pad(mins)}m`;
                // Save duration to Firestore if not present or different
                if (emp.duration !== duration && emp.ref) {
                    try {
                        await updateDoc(emp.ref, { duration });
                    } catch (e) { /* ignore Firestore update errors for now */ }
                }
            }
        }
        // Attendance status
        const status = emp.attendance_status || 'N/A';
        // Verification icons (mock logic, adjust as needed)
        const verification = `<span class=\"material-icons-round text-emerald-500 text-sm\" title=\"Biometric Verified\">fingerprint</span>`;
        tbody.innerHTML += `
        <tr class=\"hover:bg-slate-50 transition-colors\">\n          <td class=\"p-2\">\n            <p class=\"font-bold text-gov-primary leading-none\">${fullName || 'N/A'}</p>\n            <p class=\"text-[9px] text-slate-400 font-mono mt-1\">ID: ${emp.emp_id || emp.id}</p>\n          </td>\n          <td class=\"p-2\">\n            <p class=\"font-bold text-slate-700\">${inTime}</p>\n          </td>\n          <td class=\"p-2\">\n            <p class=\"font-bold text-slate-700\">${outTime}</p>\n          </td>\n          <td class=\"p-2 text-slate-600 font-mono\">${duration}</td>\n          <td class=\"p-2 text-center\">\n            <span class=\"bg-emerald-100 text-emerald-800 px-2 py-0.5 rounded-[2px] font-bold text-[9px] uppercase border border-emerald-200\">${status}</span>\n          </td>\n          <td class=\"p-2 text-right\">\n            ${verification}\n          </td>\n        </tr>\n        `;
    });
}

window.addEventListener('DOMContentLoaded', async () => {
    const employees = await fetchAttendance();
    renderAttendance(employees);
});
