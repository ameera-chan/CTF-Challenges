window.addEventListener('DOMContentLoaded', () => {
    const bandName = document.getElementById('band-name');
    const bandChannels = document.getElementById('band-channels');
    const guide = window.__starlogBand;

    if (!bandName || !bandChannels || !guide) {
        return;
    }

    bandName.textContent = guide.name || 'unknown';
    bandChannels.textContent = (guide.channels || []).join(' / ') || 'none';
});
