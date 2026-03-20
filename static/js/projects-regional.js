// static/js/projects-regional.js
// Handles regional project actions (mark as Done)

function markProjectDoneRegional(projectId) {
    if (!projectId) {
        alert('Invalid project ID');
        return;
    }
    if (!confirm('Mark this project as DONE?')) {
        return;
    }
    fetch('/regional/api/projects/' + encodeURIComponent(projectId) + '/status', {
        method: 'POST',
        headers: {
            'Content-Type': 'application/json',
        },
        body: JSON.stringify({ status: 'DONE' })
    })
    .then(response => response.json())
    .then(data => {
        if (data.success) {
            alert('Project marked as DONE.');
            window.location.reload();
        } else {
            alert('Failed to update project: ' + (data.error || 'Unknown error'));
        }
    })
    .catch(err => {
        alert('Error updating project: ' + err);
    });
}
