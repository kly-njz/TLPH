// quotation-national.js
// National quotation page: reuse superadmin modal logic for action buttons

async function openEditDrawer(quoteId) {
    const modal = document.getElementById('quoteDrawer');
    modal.hidden = false;
    modal.classList.remove('hidden');
    modal.classList.add('flex');
    document.getElementById('editQuoteId').value = quoteId;
    // Fetch quotation data from backend (national endpoint)
    const res = await fetch(`/national/api/quotation/${quoteId}`);
    if (!res.ok) {
        alert('Failed to fetch quotation data.');
        return;
    }
    const data = await res.json();
    // Populate modal fields (adjust IDs as needed)
    document.getElementById('editMetaRow').classList.remove('hidden');
    document.getElementById('editQuoteDisplay').value = data.id || '';
    document.getElementById('editIssueDate').value = data.issue_date || '';
    document.getElementById('newBuyer').value = data.buyer || '';
    document.getElementById('newTitle').value = data.title || '';
    document.getElementById('newCategory').value = data.category || '';
    document.getElementById('newSupplier').value = data.supplier || '';
    const deliverFromRaw = String(data.deliver_from || '').toLowerCase();
    const deliverFrom = (deliverFromRaw === 'national' || deliverFromRaw === 'regional' || deliverFromRaw === 'municipal')
        ? deliverFromRaw
        : 'national';
    document.getElementById('newDeliverFrom').value = deliverFrom;
    document.getElementById('newDeliverTo').value = data.deliver_to || '';
    document.getElementById('newStatusRow').classList.remove('hidden');
    document.getElementById('newStatus').value = data.status || 'pending';
    document.getElementById('newBuyerType').value = data.buyer_type || 'company';
    document.getElementById('newProd').value = data.product || '';
    document.getElementById('newQty').value = data.quantity || 0;
    document.getElementById('newPrice').value = data.unit_price || 0;
    document.getElementById('newOtherCharges').value = data.other_charges || 0;
    document.getElementById('newOtherChargesNote').value = data.other_charges_note || '';
    // Show modal
    modal.classList.remove('opacity-0', 'pointer-events-none');
    modal.classList.add('opacity-100');
}

function closeQuoteDrawer() {
    const modal = document.getElementById('quoteDrawer');
    modal.classList.add('opacity-0', 'pointer-events-none');
    setTimeout(() => {
        modal.classList.remove('opacity-100');
        modal.classList.add('hidden');
        modal.classList.remove('flex');
        modal.hidden = true;
    }, 300);
}

async function openDraftPreview(source) {
    let row = null;

    if (source && typeof source.closest === 'function') {
        row = source.closest('tr');
    } else if (typeof source === 'string') {
        row = document.querySelector(`tr[data-quote-id="${source}"]`);
    }

    if (row) {
        const cells = row.querySelectorAll('td');
        const getText = (idx) => (cells[idx] ? cells[idx].textContent.trim() : '—');
        const statusBadge = cells[15] ? cells[15].querySelector('.status-badge') : null;
        const deliverToCell = cells[14];
        const deliverTo =
            deliverToCell && deliverToCell.childNodes.length
                ? (deliverToCell.childNodes[0].textContent || '').trim()
                : getText(14);

        document.getElementById('draftPrevId').textContent = getText(0);
        document.getElementById('draftPrevDate').textContent = getText(1);
        document.getElementById('draftPrevBuyer').textContent = getText(2);
        document.getElementById('draftPrevTitle').textContent = getText(3);
        document.getElementById('draftPrevCategory').textContent = getText(4);
        document.getElementById('draftPrevSupplier').textContent = getText(5);
        document.getElementById('draftPrevProduct').textContent = getText(6);
        document.getElementById('draftPrevQty').textContent = getText(7);
        document.getElementById('draftPrevUnitPrice').textContent = getText(8);
        document.getElementById('draftPrevSubtotal').textContent = getText(9);
        document.getElementById('draftPrevOtherChargesNote').textContent = getText(10);
        document.getElementById('draftPrevOtherCharges').textContent = getText(11);
        document.getElementById('draftPrevTotal').textContent = getText(12);
        document.getElementById('draftPrevDeliverFrom').textContent = getText(13);
        document.getElementById('draftPrevDeliverTo').textContent = deliverTo || '—';
        const statusText = statusBadge ? statusBadge.textContent.trim() : getText(15);
        const statusEl = document.getElementById('draftPrevStatus');
        statusEl.textContent = statusText;
        setDraftStatusColor(statusEl, statusText, statusBadge);
    } else {
        const res = await fetch(`/national/api/quotation/${source}`);
        if (!res.ok) {
            alert('Failed to fetch quotation data.');
            return;
        }
        const data = await res.json();
        document.getElementById('draftPrevId').textContent = data.id || '—';
        document.getElementById('draftPrevDate').textContent = data.issue_date || '—';
        document.getElementById('draftPrevBuyer').textContent = data.buyer || '—';
        document.getElementById('draftPrevTitle').textContent = data.title || '—';
        document.getElementById('draftPrevCategory').textContent = data.category || '—';
        document.getElementById('draftPrevSupplier').textContent = data.supplier || '—';
        document.getElementById('draftPrevProduct').textContent = data.product || '—';
        document.getElementById('draftPrevQty').textContent = data.quantity || '—';
        document.getElementById('draftPrevUnitPrice').textContent = data.unit_price || '—';
        document.getElementById('draftPrevSubtotal').textContent = (data.quantity && data.unit_price) ? (data.quantity * data.unit_price).toFixed(2) : '—';
        document.getElementById('draftPrevOtherCharges').textContent = data.other_charges || '—';
        document.getElementById('draftPrevOtherChargesNote').textContent = data.other_charges_note || '—';
        document.getElementById('draftPrevTotal').textContent = (data.quantity && data.unit_price ? (data.quantity * data.unit_price) : 0) + (parseFloat(data.other_charges) || 0);
        document.getElementById('draftPrevDeliverFrom').textContent = data.deliver_from || '—';
        document.getElementById('draftPrevDeliverTo').textContent = data.deliver_to || '—';
        const statusText = data.status || '—';
        const statusEl = document.getElementById('draftPrevStatus');
        statusEl.textContent = statusText;
        setDraftStatusColor(statusEl, statusText);
    }

    // Show modal
    const modal = document.getElementById('draftPreviewModal');
    modal.hidden = false;
    modal.classList.remove('hidden');
    modal.classList.add('flex');
    setTimeout(() => modal.classList.add('opacity-100'), 10);
}

function setDraftStatusColor(el, statusText, badgeEl) {
    if (!el) return;
    const status = (statusText || '').toLowerCase();
    el.classList.remove(
        'text-emerald-700',
        'text-blue-700',
        'text-indigo-700',
        'text-rose-700',
        'text-amber-700',
        'text-slate-600'
    );
    if (badgeEl && badgeEl.classList) {
        const textClass = Array.from(badgeEl.classList).find((cls) => cls.startsWith('text-'));
        if (textClass) {
            el.classList.add(textClass);
            return;
        }
    }
    if (status === 'delivered') return el.classList.add('text-emerald-700');
    if (status === 'in-transit') return el.classList.add('text-blue-700');
    if (status === 'for-delivery') return el.classList.add('text-indigo-700');
    if (status === 'cancelled') return el.classList.add('text-rose-700');
    if (status === 'pending') return el.classList.add('text-amber-700');
    if (status === 'approved') return el.classList.add('text-blue-700');
    if (status === 'rejected') return el.classList.add('text-rose-700');
    return el.classList.add('text-slate-600');
}
function closeDraftPreview() {
    const modal = document.getElementById('draftPreviewModal');
    modal.classList.remove('opacity-100');
    setTimeout(() => {
        modal.classList.add('hidden');
        modal.classList.remove('flex');
        modal.hidden = true;
    }, 300);
}

async function downloadDeliveryDetails(quoteId) {
    const res = await fetch(`/national/api/quotation/${quoteId}`);
    if (!res.ok) {
        alert('Failed to fetch quotation data.');
        return;
    }
    const data = await res.json();
    const headers = [
        'Quotation ID',
        'Buyer',
        'Supplier',
        'Deliver From',
        'Deliver To',
        'Product',
        'Quantity',
        'Status'
    ];
    const row = [
        data.id || '',
        data.buyer || '',
        data.supplier || '',
        data.deliver_from || '',
        data.deliver_to || '',
        data.product || '',
        data.quantity || '',
        data.status || ''
    ];
    const escapeCell = (v) => `"${String(v).replace(/"/g, '""')}"`;
    const csv = `${headers.map(escapeCell).join(',')}\n${row.map(escapeCell).join(',')}`;
    const blob = new Blob([csv], { type: 'text/csv;charset=utf-8;' });
    const url = URL.createObjectURL(blob);
    const a = document.createElement('a');
    a.href = url;
    a.download = `delivery-details-${data.id || quoteId}.csv`;
    document.body.appendChild(a);
    a.click();
    document.body.removeChild(a);
    URL.revokeObjectURL(url);
}

// Show quotation history (placeholder)
function showHistory(quoteId) {
    alert('Show history for Quotation ID: ' + quoteId + '\n(This feature is under development.)');
}



