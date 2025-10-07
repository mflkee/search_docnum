// Main JavaScript file for Arshin Registry Synchronization System

// Function to update progress bar
function updateProgress(percent) {
    const progressBar = document.getElementById('progressBar');
    const progressValue = document.getElementById('progressValue');
    
    if (progressBar && progressValue) {
        progressBar.style.width = percent + '%';
        progressValue.textContent = percent + '%';
    }
}

// Function to handle status polling
function pollStatus(taskId, maxRetries = 100) {
    let retries = 0;
    
    const pollInterval = setInterval(() => {
        fetch(`/api/task-status/${taskId}`)
            .then(response => response.json())
            .then(data => {
                if (data.error) {
                    console.error('Error getting task status:', data.error);
                    clearInterval(pollInterval);
                    return;
                }
                
                // Update status information
                document.getElementById('statusText').textContent = data.status;
                updateProgress(data.progress);
                
                // Check if task is complete
                if (data.status === 'COMPLETED' || data.status === 'FAILED') {
                    if (data.status === 'FAILED') {
                        document.getElementById('errorDiv').style.display = 'block';
                        document.getElementById('errorMessage').textContent = data.error_message || 'Task failed unexpectedly';
                    }
                    clearInterval(pollInterval);
                    return;
                }
                
                retries++;
                if (retries >= maxRetries) {
                    clearInterval(pollInterval);
                    console.warn('Status polling stopped due to maximum retries reached');
                }
            })
            .catch(error => {
                console.error('Error polling status:', error);
                clearInterval(pollInterval);
            });
    }, 5000); // Poll every 5 seconds
    
    return pollInterval;
}

// Function to save recent tasks to localStorage
function saveRecentTask(taskId) {
    let recentTasks = JSON.parse(localStorage.getItem('recentTasks') || '[]');
    
    // Add new task to the beginning of the array
    const newTask = {
        id: taskId,
        timestamp: new Date().toISOString()
    };
    
    // Remove existing task if it's already in the list
    recentTasks = recentTasks.filter(task => task.id !== taskId);
    
    // Add new task
    recentTasks.unshift(newTask);
    
    // Keep only the 5 most recent tasks
    if (recentTasks.length > 5) {
        recentTasks = recentTasks.slice(0, 5);
    }
    
    localStorage.setItem('recentTasks', JSON.stringify(recentTasks));
}

// Function to load and display recent tasks
function loadRecentTasks() {
    const recentTasks = JSON.parse(localStorage.getItem('recentTasks') || '[]');
    const recentTasksList = document.getElementById('recentTasksList');
    
    if (!recentTasksList || recentTasks.length === 0) {
        return;
    }
    
    // Show the recent tasks section
    document.getElementById('recentTasks').style.display = 'block';
    
    // Clear the current list
    recentTasksList.innerHTML = '';
    
    // Add each task to the list
    recentTasks.forEach(task => {
        const listItem = document.createElement('li');
        listItem.className = 'list-group-item';
        listItem.innerHTML = `
            <div class="d-flex justify-content-between align-items-center">
                <span>${task.id}</span>
                <div>
                    <a href="/status/${task.id}" class="btn btn-sm btn-outline-primary">View</a>
                </div>
            </div>
        `;
        recentTasksList.appendChild(listItem);
    });
}

// Function to handle drag and drop for file uploads
function setupDragAndDrop() {
    const dropZone = document.getElementById('dropZone');
    const fileInput = document.getElementById('file');
    const uploadForm = document.getElementById('uploadForm');
    
    if (!dropZone || !fileInput) return;
    
    // Prevent default drag behaviors
    ['dragenter', 'dragover', 'dragleave', 'drop'].forEach(eventName => {
        dropZone.addEventListener(eventName, preventDefaults, false);
        document.body.addEventListener(eventName, preventDefaults, false);
    });
    
    // Highlight drop area when item is dragged over it
    ['dragenter', 'dragover'].forEach(eventName => {
        dropZone.addEventListener(eventName, highlight, false);
    });
    
    ['dragleave', 'drop'].forEach(eventName => {
        dropZone.addEventListener(eventName, unhighlight, false);
    });
    
    // Handle dropped files
    dropZone.addEventListener('drop', handleDrop, false);
    
    // Clicking the drop zone should open file browser
    dropZone.addEventListener('click', () => {
        fileInput.click();
    });
    
    function preventDefaults(e) {
        e.preventDefault();
        e.stopPropagation();
    }
    
    function highlight(e) {
        dropZone.style.display = 'flex';
    }
    
    function unhighlight(e) {
        dropZone.style.display = 'none';
    }
    
    function handleDrop(e) {
        const dt = e.dataTransfer;
        const files = dt.files;
        
        if (files.length) {
            fileInput.files = files;
            handleFileSelection();
        }
        
        dropZone.style.display = 'none';
    }
    
    // Also handle regular file selection
    fileInput.addEventListener('change', handleFileSelection);
    
    function handleFileSelection() {
        if (fileInput.files.length > 0) {
            const file = fileInput.files[0];
            // Optionally update UI to show selected file
            console.log('File selected:', file.name);
        }
    }
}

// Initialize the app when DOM is loaded
document.addEventListener('DOMContentLoaded', function() {
    // Setup drag and drop if on upload page
    if (document.getElementById('uploadForm')) {
        setupDragAndDrop();
    }
    
    // Load recent tasks if on status page
    if (document.getElementById('recentTasks')) {
        loadRecentTasks();
    }
    
    // Setup form submission if on upload page
    const uploadForm = document.getElementById('uploadForm');
    if (uploadForm) {
        uploadForm.addEventListener('submit', function(e) {
            e.preventDefault();
            
            const fileInput = document.getElementById('file');
            if (!fileInput.files[0]) {
                alert('Please select a file to upload');
                return;
            }
            
            const formData = new FormData();
            formData.append('file', fileInput.files[0]);
            
            // Add column identifiers if specified
            const verificationDateColumn = document.getElementById('verificationDateColumn');
            const certificateNumberColumn = document.getElementById('certificateNumberColumn');
            
            if (verificationDateColumn && verificationDateColumn.value.trim()) {
                formData.append('verification_date_column', verificationDateColumn.value.trim());
            }
            if (certificateNumberColumn && certificateNumberColumn.value.trim()) {
                formData.append('certificate_number_column', certificateNumberColumn.value.trim());
            }
            
            // Submit the form
            fetch('/api/v1/upload', {
                method: 'POST',
                body: formData
            })
            .then(response => response.json())
            .then(data => {
                if (data.task_id) {
                    // Hide upload form and show result
                    document.getElementById('uploadProgress').style.display = 'none';
                    
                    // Show result div
                    document.getElementById('resultDiv').style.display = 'block';
                    document.getElementById('taskId').textContent = data.task_id;
                    document.getElementById('statusLink').href = `/status/${data.task_id}`;
                    
                    // Save task to recent tasks
                    saveRecentTask(data.task_id);
                    
                    // Start polling for status if needed
                    // pollStatus(data.task_id);
                } else {
                    // Show error
                    document.getElementById('uploadProgress').style.display = 'none';
                    document.getElementById('errorDiv').style.display = 'block';
                    document.getElementById('errorMessage').textContent = data.detail || 'Upload failed';
                }
            })
            .catch(error => {
                console.error('Error uploading file:', error);
                document.getElementById('uploadProgress').style.display = 'none';
                document.getElementById('errorDiv').style.display = 'block';
                document.getElementById('errorMessage').textContent = error.message || 'Upload failed';
            });
        });
    }
});