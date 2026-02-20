import { db } from './firebase-config.js';
import { collection, getDocs } from "https://www.gstatic.com/firebasejs/10.8.0/firebase-firestore.js";

function getLeaveColor(type) {
  if (type === 'Sick Leave') return 'bg-rose-400';
  if (type === 'Vacation Leave') return 'bg-blue-500';
  if (type === 'Privilege Leave') return 'bg-emerald-400';
  return 'bg-slate-400';
}

function getStatusBadge(status) {
  if (status === 'pending') return '<span class="bg-amber-100 text-amber-800 px-2 py-0.5 rounded-[2px] font-bold text-[9px] uppercase border border-amber-200">Pending Sub-Admin</span>';
  if (status === 'active') return '<span class="bg-emerald-100 text-emerald-800 px-2 py-0.5 rounded-[2px] font-bold text-[9px] uppercase border border-emerald-200">Approved</span>';
  return '<span class="bg-slate-100 text-slate-400 px-2 py-0.5 rounded-[2px] font-bold text-[9px] uppercase border border-slate-200">Unknown</span>';
}

function formatDate(dateStr) {
  if (!dateStr) return '';
  const d = new Date(dateStr);
  return d.toLocaleDateString('en-PH', { month: 'short', day: 'numeric', year: 'numeric' });
}

function calcDays(start, end) {
  if (!start || !end) return '';
  const s = new Date(start);
  const e = new Date(end);
  return Math.max(1, Math.round((e - s) / (1000 * 60 * 60 * 24)) + 1);
}

async function renderLeaveTable() {
  const employeeCol = collection(db, 'employee');
  const employeeSnapshot = await getDocs(employeeCol);
  const employees = employeeSnapshot.docs.map(doc => ({ id: doc.id, ...doc.data() }));
  const tbody = document.getElementById('leave-tbody');
  tbody.innerHTML = '';
  employees.forEach(emp => {
    // Only show if leave_type exists
    if (!emp.leave_type) return;
    const lastname = emp.lastname || '';
    const firstname = emp.first_name || '';
    const middle = emp.middle_name || '';
    const middleInitial = middle ? middle.charAt(0).toUpperCase() + '.' : '';
    const fullName = `${lastname}, ${firstname} ${middleInitial}`.trim();
    const leaveType = emp.leave_type || 'Unknown';
    const leaveColor = getLeaveColor(leaveType);
    const startDate = emp.leave_start || emp.on_leave_date;
    const endDate = emp.leave_end || emp.on_leave_date;
    const days = calcDays(startDate, endDate);
    const status = emp.on_leave_status || 'unknown';
    const badge = getStatusBadge(status);
    tbody.innerHTML += `
      <tr class="hover:bg-slate-50 transition-colors">
        <td class="p-2">
          <p class="font-bold text-gov-primary leading-none">${fullName}</p>
          <p class="text-[9px] text-slate-400 font-mono mt-1">ID: ${emp.emp_id || emp.id}</p>
        </td>
        <td class="p-2">
          <div class="flex items-center gap-2">
            <span class="h-2 w-2 rounded-full ${leaveColor}"></span>
            <span class="font-bold text-slate-700">${leaveType}</span>
          </div>
        </td>
        <td class="p-2">
          <span class="text-slate-600 font-mono">${formatDate(startDate)} - ${formatDate(endDate)}</span>
        </td>
        <td class="p-2 text-center font-bold">${days}</td>
        <td class="p-2">${badge}</td>
        <td class="p-2 text-right">
          <button class="text-gov-primary hover:text-emerald-700 font-black uppercase text-[10px] tracking-tighter">Review</button>
        </td>
      </tr>
    `;
  });
}

window.addEventListener('DOMContentLoaded', renderLeaveTable);
