// quotations-shared.js
// Shared JS for quotation actions (approve, delete, etc.)

async function approveQuotationShared(quotationId, apiUrl, onSuccess) {
  if (!quotationId) return;
  if (!confirm('Approve this quotation?')) return;
  try {
    const res = await fetch(apiUrl, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ status: 'APPROVED' })
    });
    const data = await res.json();
    if (!res.ok || !data.success) throw new Error(data.error || 'Failed to approve quotation');
    if (onSuccess) onSuccess();
    alert('Quotation approved.');
  } catch (err) {
    alert(err.message || 'Unable to approve quotation.');
  }
}

async function deleteQuotationShared(quotationId, apiUrl, onSuccess) {
  if (!quotationId) return;
  if (!confirm('Delete this quotation? This cannot be undone.')) return;
  try {
    const res = await fetch(apiUrl, { method: 'DELETE' });
    const data = await res.json();
    if (!res.ok || !data.success) throw new Error(data.error || 'Failed to delete quotation');
    if (onSuccess) onSuccess();
    alert('Quotation deleted.');
  } catch (err) {
    alert(err.message || 'Unable to delete quotation.');
  }
}
