import { db } from './firebase-config.js';
import { collection, getDocs } from "https://www.gstatic.com/firebasejs/10.8.0/firebase-firestore.js";

function isToday(dateObj) {
    if (!dateObj) return false;
    const now = new Date();
    return dateObj.getFullYear() === now.getFullYear() &&
           dateObj.getMonth() === now.getMonth() &&
           dateObj.getDate() === now.getDate();
}

async function updateAttendanceStats() {
    const employeeCol = collection(db, 'employee');
    const employeeSnapshot = await getDocs(employeeCol);
    let presentToday = 0;
    let lateArrivals = 0;
    let onOfficialBusiness = 0;
    employeeSnapshot.forEach(doc => {
        const emp = doc.data();
        let inDateObj = null;
        if (emp.time_in) {
            if (typeof emp.time_in === 'string') {
                inDateObj = new Date(emp.time_in);
            } else if (emp.time_in.toDate) {
                inDateObj = emp.time_in.toDate();
            }
        }
        // Present Today: has time_in for today
        if (inDateObj && isToday(inDateObj)) {
            presentToday++;
            // Late Arrivals: attendance_status contains 'late' (case-insensitive)
            if ((emp.attendance_status || '').toLowerCase().includes('late')) {
                lateArrivals++;
            }
            // On Official Business: status or attendance_status contains 'official business'
            if ((emp.status || '').toLowerCase().includes('official business') || (emp.attendance_status || '').toLowerCase().includes('official business')) {
                onOfficialBusiness++;
            }
        }
    });
    document.getElementById('present-today-count').textContent = presentToday;
    document.getElementById('late-arrivals-count').textContent = lateArrivals;
    document.getElementById('official-business-count').textContent = onOfficialBusiness;
}

window.addEventListener('DOMContentLoaded', updateAttendanceStats);
