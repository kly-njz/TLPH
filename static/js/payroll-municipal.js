import { db } from './firebase-config.js';
import { collection, getDocs } from "https://www.gstatic.com/firebasejs/10.8.0/firebase-firestore.js";

function peso(n) {
    if (typeof n !== 'number') n = parseFloat(n);
    if (isNaN(n)) return '₱ 0.00';
    return '₱ ' + n.toLocaleString('en-PH', { minimumFractionDigits: 2, maximumFractionDigits: 2 });
}

async function renderPayroll() {
    const employeeCol = collection(db, 'employee');
    const employeeSnapshot = await getDocs(employeeCol);
    const employees = employeeSnapshot.docs.map(doc => ({ id: doc.id, ...doc.data() }));
    const tbody = document.getElementById('payroll-tbody');
    tbody.innerHTML = '';
    let gross = 0, deductions = 0, net = 0;
    employees.forEach(emp => {
        // Compose name: lastname, firstname middle initial
        const lastname = emp.lastname || '';
        const firstname = emp.first_name || '';
        const middle = emp.middle_name || '';
        const middleInitial = middle ? middle.charAt(0).toUpperCase() + '.' : '';
        const fullName = `${lastname}, ${firstname} ${middleInitial}`.trim();
        const grade = emp.authority_grade || 'N/A';
        const basicPay = Number(emp.basic_pay) || 0;
        const allowance = Number(emp.allowance) || 0;
        const deduction = Number(emp.deduction) || 0;
        const netPay = basicPay + allowance - deduction;
        gross += basicPay + allowance;
        deductions += deduction;
        net += netPay;
        tbody.innerHTML += `
        <tr class="hover:bg-slate-50 transition-colors">
          <td class="p-2 border-r border-slate-50">
            <p class="font-bold text-gov-primary leading-none">${fullName || 'N/A'}</p>
            <p class="text-[9px] text-slate-400 font-bold mt-1 uppercase">${grade}</p>
          </td>
          <td class="p-2 text-right font-mono-num tracking-tighter">${peso(basicPay)}</td>
          <td class="p-2 text-right font-mono-num tracking-tighter">${peso(allowance)}</td>
          <td class="p-2 text-right font-mono-num tracking-tighter text-rose-600">(${peso(deduction)})</td>
          <td class="p-2 text-right font-mono-num tracking-tighter font-bold text-emerald-900">${peso(netPay)}</td>
          <td class="p-2 text-center">
            <span class="bg-blue-50 text-blue-700 px-1.5 py-0.5 rounded-[2px] font-black text-[8px] border border-blue-200 uppercase">ATM-LBP</span>
          </td>
          <td class="p-2 text-right">
            <button class="text-gov-primary font-black uppercase text-[9px] hover:underline view-payslip-btn" data-emp-id="${emp.id}">View Payslip</button>
          </td>
        </tr>
        `;
    });
    document.getElementById('gross-payroll').textContent = peso(gross);
    document.getElementById('total-deductions').textContent = peso(deductions);
    document.getElementById('net-disbursement').textContent = peso(net);
}

window.addEventListener('DOMContentLoaded', renderPayroll);

// Payslip modal event delegation
document.body.addEventListener('click', async function(e) {
  if (e.target && e.target.matches('.view-payslip-btn')) {
    const empId = e.target.getAttribute('data-emp-id');
    if (!empId) return;
    // Fetch employee data
    const employeeCol = collection(db, 'employee');
    const employeeSnapshot = await getDocs(employeeCol);
    const emp = employeeSnapshot.docs.map(doc => ({ id: doc.id, ...doc.data() })).find(e => e.id === empId);
    if (!emp) return;
    const peso = n => {
      if (typeof n !== 'number') n = parseFloat(n);
      if (isNaN(n)) return '₱ 0.00';
      return '₱ ' + n.toLocaleString('en-PH', { minimumFractionDigits: 2, maximumFractionDigits: 2 });
    };
    const lastname = emp.lastname || '';
    const firstname = emp.first_name || '';
    const middle = emp.middle_name || '';
    const middleInitial = middle ? middle.charAt(0).toUpperCase() + '.' : '';
    const fullName = `${lastname}, ${firstname} ${middleInitial}`.trim();
    document.getElementById('payslip-emp-name').textContent = fullName;
    document.getElementById('payslip-emp-id').textContent = emp.emp_id || emp.id;
    document.getElementById('payslip-emp-title').textContent = emp.official_title || '';
    document.getElementById('payslip-period').textContent = 'Feb 01 - Feb 15, 2026';
    document.getElementById('payslip-basic-pay').textContent = peso(emp.basic_pay);
    document.getElementById('payslip-allowance').textContent = peso(emp.allowance);
    document.getElementById('payslip-deduction').textContent = peso(emp.deduction);
    const netPay = (Number(emp.basic_pay) || 0) + (Number(emp.allowance) || 0) - (Number(emp.deduction) || 0);
    document.getElementById('payslip-net-pay').textContent = peso(netPay);
    document.getElementById('payslip-modal').classList.remove('hidden');
  }
  if (e.target && e.target.id === 'close-payslip-modal') {
    document.getElementById('payslip-modal').classList.add('hidden');
  }
});
