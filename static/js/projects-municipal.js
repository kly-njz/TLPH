function markProjectCompleted(projectId) {
  if (!confirm('Mark this project as completed? This action cannot be undone.')) return;
  fetch(`/municipal/api/projects/${projectId}/status`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ status: 'Completed' })
  })
    .then(res => res.json())
    .then(data => {
      if (data.success) {
        alert('Project marked as completed.');
        window.location.reload();
      } else {
        alert('Failed to update project status: ' + (data.error || 'Unknown error'));
      }
    })
    .catch(err => {
      alert('Error: ' + err);
    });
}
