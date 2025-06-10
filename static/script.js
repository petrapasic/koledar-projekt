// Global variables for drag and drop
let draggedElement = null;
let draggedTaskId = null;
let draggedDuration = null;
let dragOffset = { x: 0, y: 0 };

// Update task via AJAX with improved error handling
async function updateTaskPosition(taskId, newDate, newStartTime, newEndTime, newMemberName = null) {
    try {
        const response = await fetch('/update-task-position', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
                'X-Requested-With': 'XMLHttpRequest'
            },
            body: JSON.stringify({
                task_id: taskId,
                new_date: newDate,
                new_start_time: newStartTime,
                new_end_time: newEndTime,
                new_member_name: newMemberName
            })
        });
        
        if (!response.ok) {
            console.error('HTTP Error:', response.status, response.statusText);
            const errorText = await response.text();
            console.error('Error response:', errorText);
            alert(`HTTP Error ${response.status}: ${response.statusText}`);
            return false;
        }
        
        const contentType = response.headers.get('content-type');
        if (!contentType || !contentType.includes('application/json')) {
            console.error('Expected JSON response, got:', contentType);
            const responseText = await response.text();
            console.error('Response body:', responseText);
            alert('Server returned non-JSON response. Check console for details.');
            return false;
        }
        
        const result = await response.json();
        
        if (!result.success) {
            console.error('Failed to update task:', result.error);
            alert('Failed to update task: ' + result.error);
            return false;
        }
        
        console.log('Task updated successfully:', result);
        return true;
        
    } catch (error) {
        console.error('Error updating task:', error);
        
        if (error instanceof SyntaxError) {
            alert('Server returned invalid JSON. This usually means an error page was returned instead of data.');
        } else if (error instanceof TypeError && error.message.includes('fetch')) {
            alert('Network error: Could not connect to server.');
        } else {
            alert('Error updating task: ' + error.message);
        }
        
        return false;
    }
}

// Convert minutes to time string (e.g., 390 -> "06:30")
function minutesToTime(minutes) {
    const hours = Math.floor(minutes / 60);
    const mins = minutes % 60;
    return `${hours.toString().padStart(2, '0')}:${mins.toString().padStart(2, '0')}`;
}

// Convert time string to minutes (e.g., "06:30" -> 390)
function timeToMinutes(timeString) {
    const [hours, minutes] = timeString.split(':').map(Number);
    return hours * 60 + minutes;
}

// Snap time to nearest 15-minute interval
function snapToInterval(minutes, interval = 15) {
    return Math.round(minutes / interval) * interval;
}

// Get member name from drop zone
function getMemberFromDropZone(dropZone) {
    return dropZone.dataset.memberName || null;
}

// Get date from drop zone
function getDateFromDropZone(dropZone) {
    return dropZone.dataset.date || null;
}

// Calculate new time based on drop position
function calculateNewTime(dropZone, clientY) {
    const rect = dropZone.getBoundingClientRect();
    const relativeY = clientY - rect.top;
    
    // Each pixel represents 1 minute, starting from 5:00 AM (300 minutes)
    const newStartMinutes = snapToInterval(300 + relativeY);
    
    // Ensure time is within bounds (5:00 AM to 11:59 PM)
    const boundedStartMinutes = Math.max(300, Math.min(1439, newStartMinutes));
    const boundedEndMinutes = Math.max(300, Math.min(1439, boundedStartMinutes + draggedDuration));
    
    return {
        start: minutesToTime(boundedStartMinutes),
        end: minutesToTime(boundedEndMinutes)
    };
}

// Initialize drag and drop functionality
function initializeDragAndDrop() {
    // Add drag event listeners to all task blocks
    document.querySelectorAll('.task-block').forEach(taskBlock => {
        taskBlock.addEventListener('dragstart', handleDragStart);
        taskBlock.addEventListener('dragend', handleDragEnd);
    });
    
    // Add drop event listeners to all drop zones
    document.querySelectorAll('.drop-zone').forEach(dropZone => {
        dropZone.addEventListener('dragover', handleDragOver);
        dropZone.addEventListener('drop', handleDrop);
        dropZone.addEventListener('dragenter', handleDragEnter);
        dropZone.addEventListener('dragleave', handleDragLeave);
    });
}

// Handle drag start
function handleDragStart(e) {
    draggedElement = e.target;
    draggedTaskId = parseInt(e.target.dataset.taskId);
    draggedDuration = parseInt(e.target.dataset.duration);
    
    // Calculate offset from mouse to top-left of element
    const rect = e.target.getBoundingClientRect();
    dragOffset.x = e.clientX - rect.left;
    dragOffset.y = e.clientY - rect.top;
    
    // Add dragging class for visual feedback
    e.target.classList.add('dragging');
    
    // Set drag data
    e.dataTransfer.effectAllowed = 'move';
    e.dataTransfer.setData('text/plain', draggedTaskId.toString());
    
    console.log('Drag started for task:', draggedTaskId, 'Duration:', draggedDuration);
}

// Handle drag end
function handleDragEnd(e) {
    // Remove visual feedback
    e.target.classList.remove('dragging');
    
    // Clean up drag state
    draggedElement = null;
    draggedTaskId = null;
    draggedDuration = null;
    dragOffset = { x: 0, y: 0 };
    
    // Remove any remaining drag-over classes
    document.querySelectorAll('.drag-over').forEach(el => {
        el.classList.remove('drag-over');
    });
}

// Handle drag over
function handleDragOver(e) {
    e.preventDefault(); // Allow drop
    e.dataTransfer.dropEffect = 'move';
}

// Handle drag enter
function handleDragEnter(e) {
    e.preventDefault();
    e.target.classList.add('drag-over');
}

// Handle drag leave
function handleDragLeave(e) {
    // Only remove drag-over if we're actually leaving the drop zone
    if (!e.target.contains(e.relatedTarget)) {
        e.target.classList.remove('drag-over');
    }
}

// Handle drop
async function handleDrop(e) {
    e.preventDefault();
    e.target.classList.remove('drag-over');
    
    if (!draggedTaskId) {
        console.error('No dragged task ID');
        return;
    }
    
    const dropZone = e.target.closest('.drop-zone');
    if (!dropZone) {
        console.error('Drop target is not a drop zone');
        return;
    }
    
    // Get new position data
    const newMemberName = getMemberFromDropZone(dropZone);
    const newDate = getDateFromDropZone(dropZone);
    const newTime = calculateNewTime(dropZone, e.clientY);
    
    console.log('Drop data:', {
        taskId: draggedTaskId,
        newMemberName,
        newDate,
        newStartTime: newTime.start,
        newEndTime: newTime.end
    });
    
    // Show loading state
    if (draggedElement) {
        draggedElement.style.opacity = '0.5';
        draggedElement.style.pointerEvents = 'none';
    }
    
    // Update task position
    const success = await updateTaskPosition(
        draggedTaskId,
        newDate,
        newTime.start,
        newTime.end,
        newMemberName
    );
    
    if (success) {
        // Reload the page to show updated calendar
        window.location.reload();
    } else {
        // Restore original state on failure
        if (draggedElement) {
            draggedElement.style.opacity = '1';
            draggedElement.style.pointerEvents = 'auto';
        }
    }
}

// Add some CSS for drag and drop visual feedback
function addDragDropStyles() {
    const style = document.createElement('style');
    style.textContent = `
        .task-block.dragging {
            opacity: 0.7;
            transform: rotate(2deg);
            box-shadow: 0 4px 8px rgba(0,0,0,0.3);
            z-index: 1000;
        }
        
        .drop-zone.drag-over {
            background-color: rgba(99, 102, 241, 0.1);
            border: 2px dashed #6366f1;
        }
        
        .task-block {
            cursor: move;
            transition: opacity 0.2s, transform 0.2s;
        }
        
        .task-block:hover {
            opacity: 0.9;
            transform: translateY(-1px);
        }
    `;
    document.head.appendChild(style);
}

// Initialize everything when DOM is ready
document.addEventListener('DOMContentLoaded', function() {
    console.log('Initializing drag and drop functionality...');
    
    // Add CSS styles
    addDragDropStyles();
    
    // Initialize drag and drop
    initializeDragAndDrop();
    
    console.log('Drag and drop initialized successfully');
});

// Reinitialize drag and drop after dynamic content changes
function reinitializeDragAndDrop() {
    initializeDragAndDrop();
}