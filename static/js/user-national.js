window.enableNationalAccount = async function(userId, userName) {
  if (!confirm(`Enable access for ${userName}?`)) return;
  try {
    const res = await fetch(`/national/api/user-management/accounts/${userId}/enable`, { method: 'POST' });
    const data = await res.json();
    if (!data.success) throw new Error(data.error || 'Failed to enable account');
    await loadNationalAccounts();
    alert('Account enabled successfully.');
  } catch (e) {
    alert('Failed to enable account: ' + e.message);
  }
}
