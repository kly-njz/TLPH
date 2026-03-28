// quotation-regional.js
// Client-side workflow for Regional quotation page

(function () {
  const peso = '\u20B1';

  const byId = (id) => document.getElementById(id);

  function toNumber(value) {
    const n = parseFloat(value);
    return Number.isFinite(n) ? n : 0;
  }

  function formatMoney(value) {
    const n = Number.isFinite(value) ? value : 0;
    return n.toLocaleString('en-PH', { minimumFractionDigits: 2, maximumFractionDigits: 2 });
  }

  function normalizeStatus(raw) {
    return String(raw || '').trim().toUpperCase();
  }

  function statusLabel(status) {
    const s = normalizeStatus(status);
    if (s === 'RECEIVED') return 'Received';
    return 'Pending';
  }

  function statusBadgeClass(status) {
    const s = normalizeStatus(status);
    if (s === 'RECEIVED') return 'bg-emerald-50 text-emerald-700 border-emerald-200';
    return 'bg-amber-50 text-amber-700 border-amber-200';
  }

  function setStatusCell(cell, status) {
    if (!cell) return;
    const badge = document.createElement('span');
    badge.className =
      'inline-block px-1.5 py-0.5 rounded-[1px] font-black text-[8px] uppercase border w-20 text-center ' +
      statusBadgeClass(status);
    badge.textContent = statusLabel(status);
    cell.innerHTML = '';
    cell.appendChild(badge);
  }

  function readRowData(row) {
    if (!row) return null;
    return {
      id: row.dataset.id || '',
      number: row.dataset.number || '',
      client: row.dataset.client || '',
      municipality: row.dataset.municipality || '',
      amount: toNumber(row.dataset.amount || 0),
      date: row.dataset.date || '',
      status: normalizeStatus(row.dataset.status || 'PENDING'),
      deliverFrom: row.dataset.deliver_from || '',
      deliverTo: row.dataset.deliver_to || '',
      deliverToType: row.dataset.deliver_to_type || '',
      buyerType: row.dataset.buyer_type || '',
      title: row.dataset.title || '',
      category: row.dataset.category || '',
      supplier: row.dataset.supplier || '',
      product: row.dataset.product || '',
      quantity: toNumber(row.dataset.quantity || 0),
      unitPrice: toNumber(row.dataset.unit_price || 0),
      otherCharges: toNumber(row.dataset.other_charges || 0),
      otherChargesNote: row.dataset.other_charges_note || '',
      fy: row.dataset.fy || ''
    };
  }

  function writeRowData(row, data) {
    if (!row || !data) return;
    row.dataset.id = data.id || row.dataset.id || '';
    row.dataset.number = data.number || '';
    row.dataset.client = data.client || '';
    row.dataset.municipality = data.municipality || '';
    row.dataset.amount = String(Number.isFinite(data.amount) ? data.amount : 0);
    row.dataset.date = data.date || '';
    row.dataset.status = normalizeStatus(data.status || 'PENDING');
    row.dataset.deliver_from = data.deliverFrom || '';
    row.dataset.deliver_to = data.deliverTo || '';
    row.dataset.deliver_to_type = data.deliverToType || '';
    row.dataset.buyer_type = data.buyerType || '';
    row.dataset.title = data.title || '';
    row.dataset.category = data.category || '';
    row.dataset.supplier = data.supplier || '';
    row.dataset.product = data.product || '';
    row.dataset.quantity = String(Number.isFinite(data.quantity) ? data.quantity : 0);
    row.dataset.unit_price = String(Number.isFinite(data.unitPrice) ? data.unitPrice : 0);
    row.dataset.other_charges = String(Number.isFinite(data.otherCharges) ? data.otherCharges : 0);
    row.dataset.other_charges_note = data.otherChargesNote || '';
    if (data.fy) row.dataset.fy = data.fy;

    const cells = row.querySelectorAll('td');
    if (cells.length >= 9) {
      cells[0].textContent = data.number || '';
      cells[1].textContent = data.client || '';
      cells[2].textContent = data.municipality || '';
      cells[3].textContent = `${peso}${formatMoney(data.amount || 0)}`;
      cells[4].textContent = data.date || '';
      setStatusCell(cells[5], data.status);
      cells[6].textContent = data.deliverFrom || '';
      cells[7].textContent = data.deliverTo || '';
      cells[8].textContent = data.deliverToType || '';
    }
  }

  function createActionButton(title, icon, onClick) {
    const btn = document.createElement('button');
    btn.type = 'button';
    btn.title = title;
    btn.className =
      'gov-btn text-[8px] border border-slate-300 bg-white hover:bg-slate-100 px-1 py-0.5';
    btn.onclick = onClick;
    const span = document.createElement('span');
    span.className = 'material-icons-round text-[12px]';
    span.textContent = icon;
    btn.appendChild(span);
    return btn;
  }

  function buildActionCell() {
    const wrapper = document.createElement('div');
    wrapper.className = 'flex flex-wrap gap-1 justify-center';
    wrapper.appendChild(createActionButton('View', 'visibility', function () { viewQuotation(this); }));
    wrapper.appendChild(
      createActionButton('Mark as Received', 'task_alt', function () {
        openReceiveModal(this);
      })
    );
    return wrapper;
  }

  function removeEmptyRow() {
    const tbody = byId('quoteTable');
    if (!tbody) return;
    const emptyCell = tbody.querySelector('tr td[colspan]');
    if (emptyCell) emptyCell.parentElement.remove();
  }

  // --- Create Quotation ---
  function openCreateModal() {
    const modal = byId('createQuotationModal');
    if (!modal) return;
    modal.classList.remove('hidden');
    modal.classList.add('flex');
    const dateInput = byId('qDate');
    if (dateInput) {
      dateInput.value = new Date().toISOString().slice(0, 10);
    }
    const statusInput = byId('qStatus');
    if (statusInput) statusInput.value = 'pending';
  }

  function closeCreateModal() {
    const modal = byId('createQuotationModal');
    if (!modal) return;
    modal.classList.add('hidden');
    modal.classList.remove('flex');
    const form = byId('createQuotationForm');
    if (form) form.reset();
  }

  function submitQuotation(e) {
    e.preventDefault();
    const number = (byId('qNumber')?.value || '').trim();
    const date = byId('qDate')?.value || '';
    const client = (byId('qClient')?.value || '').trim();
    const municipality = byId('qMunicipality')?.value || '';
    const amount = toNumber(byId('qAmount')?.value);
    const deliverFrom = (byId('qDeliverFrom')?.value || '').trim();
    const deliverTo = (byId('qDeliverTo')?.value || '').trim();
    const deliverToType = byId('qDeliverToType')?.value || '';
    const status = normalizeStatus(byId('qStatus')?.value || 'PENDING');

    if (!number || !date || !client || !municipality || !Number.isFinite(amount) || !deliverFrom || !deliverTo) {
      alert('Please complete all required fields.');
      return;
    }

    removeEmptyRow();

    const row = document.createElement('tr');
    row.className = 'hover:bg-emerald-50 transition quote-row';

    const fiscalYear = date ? `FY ${date.slice(0, 4)}` : 'ALL';
    const data = {
      id: `tmp-${Date.now()}`,
      number,
      client,
      municipality,
      amount,
      date,
      status,
      deliverFrom,
      deliverTo,
      deliverToType,
      buyerType: '',
      title: '',
      category: '',
      supplier: '',
      product: '',
      quantity: 0,
      unitPrice: 0,
      otherCharges: 0,
      otherChargesNote: '',
      fy: fiscalYear
    };

    writeRowData(row, data);

    const cells = [
      document.createElement('td'),
      document.createElement('td'),
      document.createElement('td'),
      document.createElement('td'),
      document.createElement('td'),
      document.createElement('td'),
      document.createElement('td'),
      document.createElement('td'),
      document.createElement('td'),
      document.createElement('td')
    ];

    cells[0].className = 'font-black text-slate-900 border-r border-slate-100 uppercase';
    cells[1].className = 'font-bold text-slate-700 border-r border-slate-100 uppercase';
    cells[2].className = 'font-bold text-slate-700 border-r border-slate-100 uppercase';
    cells[3].className = 'font-mono font-bold text-emerald-800 border-r border-slate-100 text-right text-[11px]';
    cells[4].className = 'font-mono text-slate-500 border-r border-slate-100 text-center';
    cells[5].className = 'text-center border-r border-slate-100';
    cells[6].className = 'text-center border-r border-slate-100';
    cells[7].className = 'text-center border-r border-slate-100';
    cells[8].className = 'text-center border-r border-slate-100';
    cells[9].className = 'text-center';

    row.appendChild(cells[0]);
    row.appendChild(cells[1]);
    row.appendChild(cells[2]);
    row.appendChild(cells[3]);
    row.appendChild(cells[4]);
    row.appendChild(cells[5]);
    row.appendChild(cells[6]);
    row.appendChild(cells[7]);
    row.appendChild(cells[8]);
    row.appendChild(cells[9]);

    cells[9].appendChild(buildActionCell());

    writeRowData(row, data);

    const tbody = byId('quoteTable');
    if (tbody) tbody.appendChild(row);

    closeCreateModal();
    filterTable();
  }

  // --- View Quotation ---
  function viewQuotation(btn) {
    const row = btn?.closest('tr');
    const data = readRowData(row);
    if (!data) return;
    byId('vqNumber').textContent = data.number || 'N/A';
    byId('vqClient').textContent = data.client || 'N/A';
    byId('vqMunicipality').textContent = data.municipality || 'N/A';
    byId('vqStatus').textContent = data.status || 'N/A';
    byId('vqDate').textContent = data.date || 'N/A';
    byId('vqDeliverFrom').textContent = data.deliverFrom || 'N/A';
    byId('vqDeliverTo').textContent = data.deliverTo || 'N/A';
    byId('vqDeliverToType').textContent = data.deliverToType || 'N/A';
    byId('vqBuyerType').textContent = data.buyerType || 'N/A';
    byId('vqCategory').textContent = data.category || 'N/A';
    byId('vqSupplier').textContent = data.supplier || 'N/A';
    byId('vqProduct').textContent = data.product || 'N/A';
    byId('vqQuantity').textContent = data.quantity || '0';
    byId('vqUnitPrice').textContent = data.unitPrice ? `${peso} ${formatMoney(data.unitPrice)}` : 'N/A';
    byId('vqOtherCharges').textContent = data.otherCharges ? `${peso} ${formatMoney(data.otherCharges)}` : 'N/A';
    byId('vqOtherChargesNote').textContent = data.otherChargesNote || 'N/A';
    byId('vqAmount').textContent = `${peso} ${formatMoney(data.amount || 0)}`;

    const modal = byId('viewQuotationModal');
    modal.classList.remove('hidden');
    modal.classList.add('flex');
  }

  function closeViewModal() {
    const modal = byId('viewQuotationModal');
    modal.classList.add('hidden');
    modal.classList.remove('flex');
  }

  // --- Forward Modal ---
  let currentForwardRow = null;
  function openForwardModal(btn) {
    currentForwardRow = btn?.closest('tr') || null;
    const rowData = readRowData(currentForwardRow);
    const modal = byId('forwardModal');
    if (!modal) return;
    byId('forwardQuotationId').value = rowData?.id || '';
    byId('forwardMunicipality').value = rowData?.municipality || '';
    modal.classList.remove('hidden');
    modal.classList.add('flex');
  }

  function closeForwardModal() {
    const modal = byId('forwardModal');
    modal.classList.add('hidden');
    modal.classList.remove('flex');
    currentForwardRow = null;
  }

  function submitForward(e) {
    e.preventDefault();
    if (!currentForwardRow) return;
    const target = byId('forwardMunicipality')?.value || '';
    const data = readRowData(currentForwardRow);
    if (!data) return;
    data.deliverTo = target;
    data.deliverToType = 'municipal';
    writeRowData(currentForwardRow, data);
    closeForwardModal();
  }

  // --- Status Modal ---
  let currentStatusRow = null;
  function openStatusModal(btn) {
    currentStatusRow = btn?.closest('tr') || null;
    const data = readRowData(currentStatusRow);
    const modal = byId('statusModal');
    if (!modal) return;
    byId('statusQuotationId').value = data?.id || '';
    byId('statusSelect').value = data?.status || 'PENDING';
    byId('statusNotes').value = '';
    modal.classList.remove('hidden');
    modal.classList.add('flex');
  }

  function closeStatusModal() {
    const modal = byId('statusModal');
    modal.classList.add('hidden');
    modal.classList.remove('flex');
    currentStatusRow = null;
  }

  function submitStatus(e) {
    e.preventDefault();
    if (!currentStatusRow) return;
    const newStatus = normalizeStatus(byId('statusSelect')?.value || 'PENDING');
    const data = readRowData(currentStatusRow);
    if (!data) return;
    data.status = newStatus;
    writeRowData(currentStatusRow, data);
    closeStatusModal();
    filterTable();
  }

  // --- Receive Modal ---
  let currentReceiveRow = null;
  function openReceiveModal(btn) {
    currentReceiveRow = btn?.closest('tr') || null;
    const data = readRowData(currentReceiveRow);
    const modal = byId('receiveModal');
    if (!modal) return;
    const quoteId = byId('receiveQuoteId');
    const client = byId('receiveClient');
    const amount = byId('receiveAmount');
    if (quoteId) quoteId.textContent = data?.number || data?.id || 'N/A';
    if (client) client.textContent = data?.client || 'N/A';
    if (amount) amount.textContent = `${peso} ${formatMoney(data?.amount || 0)}`;
    modal.classList.remove('hidden');
    modal.classList.add('flex');
  }

  function closeReceiveModal() {
    const modal = byId('receiveModal');
    if (!modal) return;
    modal.classList.add('hidden');
    modal.classList.remove('flex');
    currentReceiveRow = null;
  }

  function confirmReceive() {
    if (!currentReceiveRow) return;
    markAsReceived(currentReceiveRow);
    closeReceiveModal();
  }

  // --- History Modal ---
  function showHistoryModal(btn) {
    const row = btn?.closest('tr');
    const data = readRowData(row);
    const modal = byId('historyModal');
    if (!modal) return;
    const content = byId('historyContent');
    if (content) {
      const lines = [
        `Quotation #${data?.number || ''}`,
        `Client: ${data?.client || ''}`,
        `Status: ${statusLabel(data?.status)}`,
        `Last Updated: ${new Date().toLocaleString()}`
      ];
      content.textContent = lines.join('\n');
    }
    modal.classList.remove('hidden');
    modal.classList.add('flex');
  }

  function closeHistoryModal() {
    const modal = byId('historyModal');
    modal.classList.add('hidden');
    modal.classList.remove('flex');
  }

  // --- Edit Quotation ---
  let currentEditRow = null;
  function editQuotation(btn) {
    currentEditRow = btn?.closest('tr') || null;
    const data = readRowData(currentEditRow);
    if (!data) return;
    byId('editMetaRow').classList.remove('hidden');
    byId('editQuoteDisplay').value = data.number || data.id || '';
    byId('editQuoteId').value = data.id || '';
    const formattedDate = data.date.includes('T') ? data.date.substring(0, 10) : data.date;
    byId('editIssueDate').value = formattedDate || '';
    byId('newBuyer').value = data.client || '';
    byId('newTitle').value = data.title || '';
    byId('newCategory').value = data.category || '';
    byId('newSupplier').value = data.supplier || '';
    byId('newDeliverFrom').value = data.deliverFrom || '';
    byId('newDeliverTo').value = data.deliverTo || '';
    byId('newStatusRow').classList.remove('hidden');
    byId('newStatus').value = (data.status || 'pending').toLowerCase();
    byId('newBuyerType').value = data.buyerType || 'company';
    byId('newProd').value = data.product || '';
    byId('newQty').value = data.quantity || 0;
    byId('newPrice').value = data.unitPrice || 0;
    byId('newOtherCharges').value = data.otherCharges || 0;
    byId('newOtherChargesNote').value = data.otherChargesNote || '';

    const modal = byId('quoteDrawer');
    modal.classList.remove('opacity-0', 'pointer-events-none');
    setTimeout(() => {
      modal.classList.add('opacity-100');
    }, 10);
  }

  function closeQuoteDrawer() {
    const modal = byId('quoteDrawer');
    modal.classList.remove('opacity-100');
    modal.classList.add('opacity-0');
    modal.classList.add('pointer-events-none');
    currentEditRow = null;
  }

  function submitEditForm(e) {
    e.preventDefault();
    if (!currentEditRow) return;
    const issueDate = byId('editIssueDate')?.value || '';
    const client = (byId('newBuyer')?.value || '').trim();
    const title = (byId('newTitle')?.value || '').trim();
    const category = (byId('newCategory')?.value || '').trim();
    const supplier = (byId('newSupplier')?.value || '').trim();
    const deliverFrom = (byId('newDeliverFrom')?.value || '').trim();
    const deliverTo = (byId('newDeliverTo')?.value || '').trim();
    const status = normalizeStatus(byId('newStatus')?.value || 'PENDING');
    const buyerType = byId('newBuyerType')?.value || '';
    const product = (byId('newProd')?.value || '').trim();
    const quantity = toNumber(byId('newQty')?.value);
    const unitPrice = toNumber(byId('newPrice')?.value);
    const otherCharges = toNumber(byId('newOtherCharges')?.value);
    const otherChargesNote = (byId('newOtherChargesNote')?.value || '').trim();
    let totalAmount = quantity * unitPrice + otherCharges;
    if (!totalAmount && data.amount) {
      totalAmount = data.amount;
    }

    if (!client || !issueDate || !deliverFrom || !deliverTo) {
      alert('Please complete required fields before saving.');
      return;
    }

    const data = readRowData(currentEditRow);
    if (!data) return;
    data.date = issueDate;
    data.client = client;
    data.title = title;
    data.category = category;
    data.supplier = supplier;
    data.deliverFrom = deliverFrom;
    data.deliverTo = deliverTo;
    data.status = status;
    data.buyerType = buyerType;
    data.product = product;
    data.quantity = quantity;
    data.unitPrice = unitPrice;
    data.otherCharges = otherCharges;
    data.otherChargesNote = otherChargesNote;
    data.amount = totalAmount;
    data.fy = issueDate ? `FY ${issueDate.slice(0, 4)}` : data.fy;
    writeRowData(currentEditRow, data);
    closeQuoteDrawer();
  }

  function markAsReceived(rowOrBtn) {
    const row = rowOrBtn?.closest ? rowOrBtn.closest('tr') : rowOrBtn;
    const data = readRowData(row);
    if (!data) return;
    data.status = 'RECEIVED';
    writeRowData(row, data);
    const actionCell = row.querySelector('td:last-child .flex');
    if (actionCell) {
      const receiveBtn = actionCell.querySelector('button[title="Mark as Received"]');
      if (receiveBtn) receiveBtn.remove();
    }
    filterTable();
  }

  // --- Draft Preview ---
  function draftQuotation(btn) {
    const row = btn?.closest('tr');
    const data = readRowData(row);
    if (!data) return;
    byId('draftPrevId').textContent = data.id || '—';
    byId('draftPrevDate').textContent = data.date || '';
    byId('draftPrevBuyer').textContent = data.client || '—';
    byId('draftPrevTitle').textContent = data.title || '—';
    byId('draftPrevType').textContent = data.buyerType || '—';
    byId('draftPrevCategory').textContent = data.category || '—';
    byId('draftPrevSupplier').textContent = data.supplier || '—';
    byId('draftPrevProduct').textContent = data.product || '—';
    byId('draftPrevQty').textContent = data.quantity || '—';
    byId('draftPrevUnitPrice').textContent = data.unitPrice ? formatMoney(data.unitPrice) : '—';
    const subtotal = data.quantity * data.unitPrice;
    byId('draftPrevSubtotal').textContent = subtotal ? formatMoney(subtotal) : '—';
    byId('draftPrevOtherCharges').textContent = data.otherCharges ? formatMoney(data.otherCharges) : '—';
    byId('draftPrevOtherChargesNote').textContent = data.otherChargesNote || '—';
    byId('draftPrevTotal').textContent = formatMoney(subtotal + data.otherCharges);
    byId('draftPrevDeliverFrom').textContent = data.deliverFrom || '—';
    byId('draftPrevDeliverTo').textContent = data.deliverTo || '—';
    byId('draftPrevStatus').textContent = statusLabel(data.status);

    const modal = byId('draftPreviewModal');
    modal.classList.remove('hidden');
    setTimeout(() => modal.classList.add('opacity-100'), 10);
  }

  function closeDraftPreview() {
    const modal = byId('draftPreviewModal');
    modal.classList.remove('opacity-100');
    setTimeout(() => modal.classList.add('hidden'), 300);
  }

  // --- Filters ---
  function filterTable() {
    const q = (byId('searchQuote')?.value || '').toLowerCase().trim();
    const status = (byId('statusFilter')?.value || 'ALL').toUpperCase();
    const mun = (byId('municipalityFilter')?.value || 'ALL').toUpperCase();
    const fy = (byId('fyFilter')?.value || 'ALL').toUpperCase();

    const rows = document.querySelectorAll('.quote-row');
    let count = 0;

    rows.forEach((row) => {
      const text = row.innerText.toLowerCase();
      const rowStatus = normalizeStatus(row.getAttribute('data-status') || '');
      const rowMun = (row.getAttribute('data-municipality') || '').toUpperCase();
      const rowFY = (row.getAttribute('data-fy') || 'ALL').toUpperCase();

      const matchQ = text.includes(q);
      const matchStatus = status === 'ALL' || rowStatus.includes(status);
      const matchMun = mun === 'ALL' || rowMun.includes(mun);
      const matchFY = fy === 'ALL' || rowFY.includes(fy);

      if (matchQ && matchStatus && matchMun && matchFY) {
        row.style.display = '';
        count++;
      } else {
        row.style.display = 'none';
      }
    });

    const visibleCount = byId('visibleCount');
    if (visibleCount) visibleCount.innerText = count;
    const fyLabel = byId('fyLabel');
    if (fyLabel) fyLabel.innerText = fy === 'ALL' ? 'All Fiscal Years' : fy;
  }

  function resetFilters() {
    if (byId('searchQuote')) byId('searchQuote').value = '';
    if (byId('statusFilter')) byId('statusFilter').value = 'ALL';
    if (byId('municipalityFilter')) byId('municipalityFilter').value = 'ALL';
    if (byId('fyFilter')) byId('fyFilter').value = 'ALL';
    filterTable();
  }

  function normalizeStatusBadges() {
    const rows = document.querySelectorAll('.quote-row');
    rows.forEach((row) => {
      const cells = row.querySelectorAll('td');
      if (cells.length >= 6) {
        setStatusCell(cells[5], row.dataset.status || 'PENDING');
      }
    });
  }

  function initCharts() {
    if (!window.Chart) return;
    Chart.defaults.font.family = 'Verdana, Arial, sans-serif';
    Chart.defaults.font.size = 8;
    Chart.defaults.color = '#64748b';

    const chartOpt = { responsive: true, maintainAspectRatio: false, layout: { padding: 5 } };

    const statusEl = byId('quoteStatusChart');
    if (statusEl) {
      new Chart(statusEl, {
        type: 'doughnut',
        data: {
          labels: ['Pending', 'Received'],
          datasets: [
            { data: [6, 42], backgroundColor: ['#f59e0b', '#10b981'], borderWidth: 0 }
          ]
        },
        options: {
          ...chartOpt,
          cutout: '65%',
          plugins: { legend: { position: 'right', labels: { boxWidth: 8, font: { weight: 'bold' } } } }
        }
      });
    }

    const trendEl = byId('quoteTrendChart');
    if (trendEl) {
      new Chart(trendEl, {
        type: 'bar',
        data: {
          labels: ['Sep', 'Oct', 'Nov', 'Dec', 'Jan', 'Feb'],
          datasets: [
            { label: 'Value (PHP)', data: [150000, 200000, 180000, 320000, 250000, 420000], backgroundColor: '#065f46', borderRadius: 2 }
          ]
        },
        options: {
          ...chartOpt,
          plugins: { legend: { display: false } },
          scales: {
            x: { grid: { display: false }, ticks: { font: { weight: 'bold' } } },
            y: {
              beginAtZero: true,
              grid: { color: '#f1f5f9' },
              ticks: { font: { weight: 'bold' }, callback: (value) => `${peso}${value / 1000}k` }
            }
          }
        }
      });
    }
  }

  function initRegionalQuotation() {
    const editForm = byId('editQuotationForm');
    if (editForm) editForm.addEventListener('submit', submitEditForm);
    normalizeStatusBadges();
    filterTable();
    initCharts();
  }

  // Expose functions for inline handlers
  window.openCreateModal = openCreateModal;
  window.closeCreateModal = closeCreateModal;
  window.submitQuotation = submitQuotation;
  window.viewQuotation = viewQuotation;
  window.closeViewModal = closeViewModal;
  window.openReceiveModal = openReceiveModal;
  window.closeReceiveModal = closeReceiveModal;
  window.confirmReceive = confirmReceive;
  window.markAsReceived = markAsReceived;
  window.filterTable = filterTable;
  window.resetFilters = resetFilters;
  window.initRegionalQuotation = initRegionalQuotation;
})();
