function markProjectFullyComplete(projectId) {
  if (!confirm('Mark this project as fully completed? This will override municipal/regional status.')) return;
  fetch(`/national/api/projects/${projectId}/status`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ status: 'fully_completed' })
  })
    .then(res => res.json())
    .then(data => {
      if (data.success) {
        alert('Project marked as fully completed.');
        window.location.reload();
      } else {
        alert('Failed to update project status: ' + (data.error || 'Unknown error'));
      }
    })
    .catch(err => {
      alert('Error: ' + err);
    });
}
