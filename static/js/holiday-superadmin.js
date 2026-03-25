// holiday-superadmin.js
// Handles all actions, buttons, and chart sync for superadmin holiday page

document.addEventListener('DOMContentLoaded', function () {
  // Helper for toast
  const toast = (a, b) => {
    const tt = document.getElementById('tt');
    const tm = document.getElementById('tm');
    const toastDiv = document.getElementById('toast');
    if (tt && tm && toastDiv) {
      tt.textContent = a;
      tm.textContent = b;
      toastDiv.classList.remove('hidden');
      clearTimeout(window.__t);
      window.__t = setTimeout(() => toastDiv.classList.add('hidden'), 2200);
    }
  };

  // State
  let holidays = [];
  let selectedIds = new Set();

  // Fetch holidays
  async function fetchHolidays() {
    try {
      const res = await fetch('/superadmin/api/hrm/holidays');
      const data = await res.json();
      if (data && data.success && Array.isArray(data.holidays)) {
        holidays = data.holidays;
      } else {
        holidays = [];
      }
      renderTable();
      renderCharts();
    } catch (err) {
      holidays = [];
      renderTable();
      renderCharts();
      toast('Error', 'Failed to load holidays');
    }
  }

  // Render table
  function renderTable() {
    const tb = document.getElementById('tb');
    if (!tb) return;
    tb.innerHTML = holidays.length ? holidays.map(x => `
      <tr class="hover:bg-slate-50 transition-colors data-row">
        <td class="px-3 py-1.5 align-middle text-center border-r border-slate-100">
          <input type="checkbox" class="rc cursor-pointer" data-id="${x.id}" ${selectedIds.has(x.id) ? 'checked' : ''}>
        </td>
        <td class="px-3 py-1.5 align-middle text-center border-r border-slate-100 font-mono text-slate-800 font-bold">${x.date || ''}</td>
        <td class="px-3 py-1.5 align-middle border-r border-slate-100">
          <div class="font-black text-slate-900 uppercase tracking-tight">${x.name || ''}</div>
          ${x.basis ? `<div class="text-[9px] text-slate-500 mt-0.5 tracking-widest font-bold">${x.basis}</div>` : ''}
        </td>
        <td class="px-3 py-1.5 align-middle text-center border-r border-slate-100">${x.type || ''}</td>
        <td class="px-3 py-1.5 align-middle text-center border-r border-slate-100">${x.scope || ''}</td>
        <td class="px-3 py-1.5 align-middle border-r border-slate-100 text-[9px] font-bold text-slate-800 uppercase tracking-widest text-center">${x.region || ''}</td>
        <td class="px-3 py-1.5 align-middle border-r border-slate-100 text-[9px] font-bold text-slate-800 uppercase tracking-widest text-center">${x.municipality || ''}</td>
        <td class="px-3 py-1.5 align-middle border-r border-slate-100 text-[9px] font-bold text-slate-700 uppercase tracking-widest text-center">${x.basis || ''}</td>
        <td class="px-3 py-1.5 align-middle border-r border-slate-100 text-center">
          ${x.office_status === 'open' ? `<span class='text-emerald-700 font-bold'>Open${x.open_time && x.close_time ? ` (${x.open_time} - ${x.close_time})` : ''}</span>` : `<span class='text-rose-700 font-bold'>Closed</span>`}
        </td>
        <td class="px-3 py-1.5 align-middle text-center no-print w-[60px]">
          <div class="flex justify-center gap-1 flex-nowrap">
            <button class="ed btn-action btn-edit" title="Edit" data-id="${x.id}"><span class="material-icons-round text-[12px]">edit</span></button>
            <button class="rm btn-action btn-delete" title="Delete" data-id="${x.id}"><span class="material-icons-round text-[12px]">delete</span></button>
          </div>
        </td>
      </tr>
    `).join('') : '<tr><td colspan="10" class="py-10 text-center text-slate-400 font-bold uppercase tracking-widest text-[9px]">No holiday records found.</td></tr>';
  }

  // Render charts (simple count by type, scope)
  function renderCharts() {
    // You can use Chart.js or similar here, but for brevity, just update counts
    document.getElementById('stAll').textContent = holidays.length;
    document.getElementById('stReg').textContent = holidays.filter(x => x.type === 'REGULAR').length;
    document.getElementById('stSpec').textContent = holidays.filter(x => String(x.type || '').startsWith('SPECIAL')).length;
    // TODO: Add Chart.js rendering for chType, chScope, chRegion
  }

  // Event listeners for action buttons
  document.addEventListener('click', function (e) {
    if (e.target.closest('.btn-edit')) {
      const id = e.target.closest('.btn-edit').dataset.id;
      // TODO: Open edit modal and populate with holiday data
      toast('Edit', 'Edit holiday ' + id);
    }
    if (e.target.closest('.btn-delete')) {
      const id = e.target.closest('.btn-delete').dataset.id;
      // TODO: Confirm and delete holiday
      toast('Delete', 'Delete holiday ' + id);
    }
    if (e.target.closest('.rc')) {
      const id = e.target.closest('.rc').dataset.id;
      if (e.target.checked) selectedIds.add(id);
      else selectedIds.delete(id);
    }
    if (e.target.closest('#btnBulkDelete')) {
      // TODO: Bulk delete selected
      toast('Bulk Delete', 'Delete selected holidays');
    }
    if (e.target.closest('#btnOpenCreate')) {
      // TODO: Open create modal
      toast('Create', 'Open create holiday modal');
    }
    if (e.target.closest('#btnImport')) {
      // TODO: Open import modal
      toast('Import', 'Open import modal');
    }
    if (e.target.closest('#btnExport')) {
      // TODO: Export holidays to CSV/Excel
      toast('Export', 'Export holidays');
    }
    if (e.target.closest('#btnToggleView')) {
      // TODO: Toggle calendar/table view
      toast('Toggle View', 'Switch calendar/table view');
    }
    if (e.target.closest('#btnCalcWD')) {
      // TODO: Calculate working days
      toast('Calc WD', 'Calculate working days');
    }
    if (e.target.closest('#btnCalcPay')) {
      // TODO: Calculate estimated pay
      toast('Calc Pay', 'Calculate estimated pay');
    }
    if (e.target.closest('#btnCopyNationalToRegion')) {
      // TODO: Copy national holidays to region
      toast('Copy', 'Copy national holidays to region');
    }
    if (e.target.closest('#btnCloneRegionToMunicipalities')) {
      // TODO: Clone region holidays to municipalities
      toast('Clone', 'Clone region holidays to municipalities');
    }
  });

  // Initial load
  fetchHolidays();
});
