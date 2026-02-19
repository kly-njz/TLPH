import { db } from './firebase-config.js';
import { collection, getDocs } from "https://www.gstatic.com/firebasejs/10.8.0/firebase-firestore.js";

async function fetchEmployees() {
    const employeeCol = collection(db, 'employee');
    const employeeSnapshot = await getDocs(employeeCol);
    const employeeList = employeeSnapshot.docs.map(doc => ({ id: doc.id, ...doc.data() }));
    return employeeList;
}

function renderEmployees(employees) {
    const tbody = document.querySelector('#employee-tbody');
    tbody.innerHTML = '';
    employees.forEach(emp => {
        // Compose name: lastname, firstname middle initial
        const lastname = emp.lastname || '';
        const firstname = emp.first_name || '';
        const middle = emp.middle_name || '';
        const middleInitial = middle ? middle.charAt(0).toUpperCase() + '.' : '';
        const fullName = `${lastname}, ${firstname} ${middleInitial}`.trim();

        tbody.innerHTML += `
        <tr class="hover:bg-slate-50 transition-colors">
            <td class="p-2 text-center">
                <div class="w-8 h-8 rounded-sm bg-slate-200 overflow-hidden border border-gov-border mx-auto flex items-center justify-center text-slate-400">
                    <span class="material-icons-round text-sm">person</span>
                </div>
            </td>
            <td class="p-2">
                <p class="font-bold text-gov-primary leading-none">${fullName || 'N/A'}</p>
                <p class="text-[10px] text-slate-400 font-mono mt-1">${emp.emp_id || emp.id}</p>
            </td>
            <td class="p-2">
                <p class="font-bold text-slate-700 leading-none">${emp.official_title || 'N/A'}</p>
                <p class="text-[9px] text-slate-500 uppercase mt-1">${emp.municipality || 'N/A'}</p>
            </td>
            <td class="p-2">
                <p class="font-medium text-slate-600">${emp.region || 'N/A'} / ${emp.province || 'N/A'}</p>
            </td>
            <td class="p-2 text-center">
                <span class="bg-emerald-100 text-emerald-800 px-2 py-0.5 rounded-[2px] font-bold text-[9px] uppercase border border-emerald-200">${emp.status || 'N/A'}</span>
            </td>
            <td class="p-2 text-right">
                <button class="text-sky-700 hover:text-sky-900 font-black uppercase text-[10px] tracking-tighter">Profile</button>
                <span class="mx-1 text-slate-300">|</span>
                <button class="text-slate-400 hover:text-rose-700 font-black uppercase text-[10px] tracking-tighter">Archive</button>
            </td>
        </tr>
        `;
    });
}

window.addEventListener('DOMContentLoaded', async () => {
    const employees = await fetchEmployees();
    renderEmployees(employees);
});
