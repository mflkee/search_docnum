// Upload-specific JavaScript functionality

// Initialize upload page specific functionality
document.addEventListener('DOMContentLoaded', function() {
    // Get references to DOM elements
    const fileInput = document.getElementById('file');
    const uploadForm = document.getElementById('uploadForm');
    const uploadBtn = document.getElementById('uploadBtn');
    const uploadProgress = document.getElementById('uploadProgress');
    const progressText = document.getElementById('progressText');
    const resultDiv = document.getElementById('resultDiv');
    const errorDiv = document.getElementById('errorDiv');
    const taskIdSpan = document.getElementById('taskId');
    const statusLink = document.getElementById('statusLink');
    const verificationDateColumn = document.getElementById('verificationDateColumn');
    const certificateNumberColumn = document.getElementById('certificateNumberColumn');
    const sheetName = document.getElementById('sheetName');
    
    // If this is the upload page, initialize the file upload functionality 
    if (uploadForm) {
        // Handle form submission
        uploadForm.addEventListener('submit', function(e) {
            e.preventDefault();
            
            // Validate file
            if (!fileInput.files[0]) {
                showError('Please select a file to upload');
                return;
            }
            
            const file = fileInput.files[0];
            
            // Validate file type
            const allowedTypes = ['.xlsx', '.xls'];
            const fileExtension = '.' + file.name.split('.').pop().toLowerCase();
            if (!allowedTypes.includes(fileExtension)) {
                showError(`Invalid file type. Only ${allowedTypes.join(', ')} files are allowed.`);
                return;
            }
            
            // Validate file size (100MB max)
            const maxSize = 100 * 1024 * 1024; // 100MB in bytes
            if (file.size > maxSize) {
                showError(`File size exceeds maximum allowed size of 100MB (${formatFileSize(file.size)} provided)`);
                return;
            }
            
            // Prepare form data
            const formData = new FormData();
            formData.append('file', file);
            
            // Add column identifiers if specified
            if (verificationDateColumn && verificationDateColumn.value.trim()) {
                formData.append('verification_date_column', verificationDateColumn.value.trim());
            }
            if (certificateNumberColumn && certificateNumberColumn.value.trim()) {
                formData.append('certificate_number_column', certificateNumberColumn.value.trim());
            }
            if (sheetName && sheetName.value.trim()) {
                formData.append('sheet_name', sheetName.value.trim());
            }
            
            // Show progress
            uploadProgress.style.display = 'block';
            progressText.textContent = '0%';
            
            // Create AJAX request
            const xhr = new XMLHttpRequest();
            
            // Update progress
            xhr.upload.addEventListener('progress', function(e) {
                if (e.lengthComputable) {
                    const percentComplete = Math.round((e.loaded / e.total) * 100);
                    progressText.textContent = percentComplete + '%';
                    
                    // Update Bootstrap progress bar
                    const progressBar = uploadProgress.querySelector('.progress-bar');
                    progressBar.style.width = percentComplete + '%';
                }
            });
            
            // Handle completion
            xhr.addEventListener('load', function() {
                if (xhr.status === 200) {
                    const response = JSON.parse(xhr.responseText);
                    
                    if (response.task_id) {
                        // Upload successful
                        uploadProgress.style.display = 'none';
                        resultDiv.style.display = 'block';
                        taskIdSpan.textContent = response.task_id;
                        statusLink.href = `/status/${response.task_id}`;
                        
                        // Save to recent tasks
                        saveRecentTask(response.task_id);
                    } else {
                        showError(response.detail || 'Upload failed');
                    }
                } else {
                    // Error response
                    try {
                        const response = JSON.parse(xhr.responseText);
                        showError(response.detail || `Upload failed with status ${xhr.status}`);
                    } catch (e) {
                        showError(`Upload failed with status ${xhr.status}`);
                    }
                }
            });
            
            // Handle errors
            xhr.addEventListener('error', function() {
                uploadProgress.style.display = 'none';
                showError('Upload failed due to network error');
            });
            
            // Send the request
            xhr.open('POST', '/api/v1/upload');
            xhr.send(formData);
        });
    }
    
    // Helper function to show error messages
    function showError(message) {
        uploadProgress.style.display = 'none';
        errorDiv.style.display = 'block';
        document.getElementById('errorMessage').textContent = message;
    }
    
    // Helper function to format file size
    function formatFileSize(bytes) {
        if (bytes === 0) return '0 Bytes';
        const k = 1024;
        const sizes = ['Bytes', 'KB', 'MB', 'GB'];
        const i = Math.floor(Math.log(bytes) / Math.log(k));
        return parseFloat((bytes / Math.pow(k, i)).toFixed(2)) + ' ' + sizes[i];
    }
    
    // Helper function to save recent task (same as in main.js)
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
});