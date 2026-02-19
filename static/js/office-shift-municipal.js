import { db } from './firebase-config.js';
import { collection, getDocs } from "https://www.gstatic.com/firebasejs/10.8.0/firebase-firestore.js";

async function fetchEmployeesOnShift() {
    // You can filter by office_shift if needed
    const employeeCol = collection(db, 'employee');
    const employeeSnapshot = await getDocs(employeeCol);
    const employeeList = employeeSnapshot.docs.map(doc => ({ id: doc.id, ...doc.data() }));
    // Optionally filter for those on 'regular day shift'
    return employeeList.filter(emp => (emp.office_shift || '').toLowerCase().includes('regular day shift'));
}

function renderEmployeesOnShift(employees) {
    const tbody = document.querySelector('#shift-employee-tbody');
    tbody.innerHTML = '';
    employees.forEach(emp => {
        // Compose name: lastname, firstname middle initial
        const lastname = emp.lastname || '';
        const firstname = emp.first_name || '';
        const middle = emp.middle_name || '';
        const middleInitial = middle ? middle.charAt(0).toUpperCase() + '.' : '';
        const fullName = `${lastname}, ${firstname} ${middleInitial}`.trim();
        let inTime = '--:--';
        if (emp.time_in) {
            if (typeof emp.time_in === 'string') {
                const parts = emp.time_in.split(' ');
                inTime = parts.length > 1 ? parts[1] : parts[0];
            } else if (emp.time_in.toDate) {
                // Firestore Timestamp object
                const dateObj = emp.time_in.toDate();
                inTime = dateObj.toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' });
            }
        }
        tbody.innerHTML += `
        <tr>
          <td class="p-2">
            <p class="font-bold text-gov-primary">${fullName || 'N/A'}</p>
            <p class="text-[9px] text-slate-400 font-bold uppercase">${emp.official_title || 'N/A'}</p>
          </td>
          <td class="p-2 text-slate-600 uppercase">${emp.municipality || 'N/A'}</td>
          <td class="p-2 font-mono text-indigo-700">${inTime}</td>
          <td class="p-2 text-center">
            <span class="bg-emerald-100 text-emerald-800 px-2 py-0.5 rounded-[2px] font-bold text-[9px] uppercase border border-emerald-200">${emp.status || 'N/A'}</span>
          </td>
        </tr>
        `;
    });
}

window.addEventListener('DOMContentLoaded', async () => {
    const employees = await fetchEmployeesOnShift();
    renderEmployeesOnShift(employees);
});
