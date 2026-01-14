/* ============================================================================
   static/js/app.js - JavaScript Application Logic
   ============================================================================ */
let currentJobId = null;
let statusInterval = null;

const uploadArea = document.getElementById('uploadArea');
const fileInput = document.getElementById('fileInput');
const uploadSection = document.getElementById('uploadSection');
const processingSection = document.getElementById('processingSection');
const fileName = document.getElementById('fileName');
const statusBadge = document.getElementById('statusBadge');
const logContainer = document.getElementById('logContainer');
const downloadBtn = document.getElementById('downloadBtn');
const newFileBtn = document.getElementById('newFileBtn');
const errorMessage = document.getElementById('errorMessage');
const progressFill = document.getElementById('progressFill');

// Upload area click
uploadArea.addEventListener('click', () => fileInput.click());

// File input change
fileInput.addEventListener('change', (e) => {
    if (e.target.files.length > 0) {
        handleFile(e.target.files[0]);
    }
});

// Drag and drop
uploadArea.addEventListener('dragover', (e) => {
    e.preventDefault();
    uploadArea.classList.add('dragging');
});

uploadArea.addEventListener('dragleave', () => {
    uploadArea.classList.remove('dragging');
});

uploadArea.addEventListener('drop', (e) => {
    e.preventDefault();
    uploadArea.classList.remove('dragging');

    if (e.dataTransfer.files.length > 0) {
        const file = e.dataTransfer.files[0];
        if (file.type === 'application/pdf') {
            handleFile(file);
        } else {
            alert('Please upload a PDF file');
        }
    }
});

// New file button
newFileBtn.addEventListener('click', () => {
    resetUI();
});

// Download button
downloadBtn.addEventListener('click', () => {
    if (currentJobId) {
        // Create a hidden iframe to download without navigation
        const iframe = document.createElement('iframe');
        iframe.style.display = 'none';
        iframe.src = `/download/${currentJobId}`;
        document.body.appendChild(iframe);

        // Show success message immediately
        const successMsg = document.createElement('div');
        successMsg.style.cssText = `
            position: fixed;
            top: 20px;
            right: 20px;
            background: #10b981;
            color: white;
            padding: 16px 24px;
            border-radius: 8px;
            box-shadow: 0 4px 12px rgba(0,0,0,0.15);
            z-index: 1000;
            font-weight: 600;
        `;
        successMsg.textContent = '✓ Download started! Ready for next file...';
        document.body.appendChild(successMsg);

        // Reset UI immediately so user can upload next file
        setTimeout(() => {
            document.body.removeChild(successMsg);
            resetUI();
        }, 1500);

        // Clean up iframe after download has had time to complete
        setTimeout(() => {
            document.body.removeChild(iframe);
        }, 3000);

        // No automatic server cleanup - files will be cleaned by cron
    }
});

function handleFile(file) {
    const formData = new FormData();
    formData.append('file', file);

    fetch('/upload', {
        method: 'POST',
        body: formData
    })
    .then(response => response.json())
    .then(data => {
        if (data.error) {
            alert(data.error);
            return;
        }

        currentJobId = data.job_id;
        fileName.textContent = data.filename;

        uploadSection.style.display = 'none';
        processingSection.style.display = 'block';

        // Add a small delay before starting to poll status
        // This ensures the backend has time to initialize the job
        setTimeout(() => {
            updateStatus(data.job_id);
            statusInterval = setInterval(() => updateStatus(data.job_id), 1000);
        }, 100);
    })
    .catch(error => {
        console.error('Error:', error);
        alert('Failed to upload file');
    });
}

function updateStatus(jobId) {
    fetch(`/status/${jobId}`)
        .then(response => response.json())
        .then(data => {
            if (data.error) {
                showError(data.error);
                return;
            }

            updateStatusBadge(data.status);

            if (data.messages && data.messages.length > 0) {
                data.messages.forEach(msg => addLogEntry(msg));
            }

            if (data.status === 'completed') {
                clearInterval(statusInterval);
                progressFill.style.width = '100%';
                downloadBtn.disabled = false;
                console.log('Job completed. Output file:', data.output_file);
            } else if (data.status === 'failed') {
                clearInterval(statusInterval);
                showError(data.error || 'Processing failed');
            } else if (data.status === 'processing') {
                progressFill.style.width = '70%';
            }
        })
        .catch(error => {
            console.error('Error fetching status:', error);
        });
}

function updateStatusBadge(status) {
    statusBadge.className = 'status-badge status-' + status;
    statusBadge.textContent = status.charAt(0).toUpperCase() + status.slice(1);
}

function addLogEntry(msg) {
    const entry = document.createElement('div');
    entry.className = `log-entry log-${msg.type}`;
    entry.innerHTML = `
        <span class="log-time">[${msg.timestamp}]</span>
        <span class="log-message">${escapeHtml(msg.message)}</span>
    `;
    logContainer.appendChild(entry);
    logContainer.scrollTop = logContainer.scrollHeight;
}

function showError(message) {
    errorMessage.textContent = message;
    errorMessage.style.display = 'block';
}

function resetUI() {
    uploadSection.style.display = 'block';
    processingSection.style.display = 'none';
    logContainer.innerHTML = '';
    errorMessage.style.display = 'none';
    downloadBtn.disabled = true;
    progressFill.style.width = '0%';
    fileInput.value = '';
    currentJobId = null;
    if (statusInterval) {
        clearInterval(statusInterval);
    }
}

function escapeHtml(text) {
    const div = document.createElement('div');
    div.textContent = text;
    return div.innerHTML;
}