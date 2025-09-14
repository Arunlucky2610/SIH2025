// Offline functionality and PWA utilities

class OfflineManager {
    constructor() {
        this.dbName = 'RuralEduDB';
        this.dbVersion = 1;
        this.init();
    }
    
    // Initialize IndexedDB
    init() {
        const request = indexedDB.open(this.dbName, this.dbVersion);
        
        request.onerror = (event) => {
            console.error('Database error:', event.target.error);
        };
        
        request.onupgradeneeded = (event) => {
            const db = event.target.result;
            
            // Create object stores
            if (!db.objectStoreNames.contains('quiz-submissions')) {
                db.createObjectStore('quiz-submissions', { keyPath: 'id' });
            }
            
            if (!db.objectStoreNames.contains('progress-updates')) {
                db.createObjectStore('progress-updates', { keyPath: 'id' });
            }
            
            if (!db.objectStoreNames.contains('cached-lessons')) {
                db.createObjectStore('cached-lessons', { keyPath: 'id' });
            }
        };
        
        request.onsuccess = (event) => {
            this.db = event.target.result;
            console.log('Database initialized successfully');
        };
    }
    
    // Store quiz submission for later sync
    storeQuizSubmission(quizId, answer, url, headers) {
        return new Promise((resolve, reject) => {
            const transaction = this.db.transaction(['quiz-submissions'], 'readwrite');
            const store = transaction.objectStore('quiz-submissions');
            
            const submission = {
                id: Date.now().toString(),
                quizId: quizId,
                url: url,
                headers: headers,
                body: JSON.stringify({ answer: answer }),
                timestamp: new Date().toISOString()
            };
            
            const request = store.add(submission);
            
            request.onsuccess = () => {
                resolve(submission);
                // Register background sync
                this.registerBackgroundSync('quiz-submission');
            };
            
            request.onerror = () => {
                reject(request.error);
            };
        });
    }
    
    // Store progress update for later sync
    storeProgressUpdate(lessonId, completed, url, headers) {
        return new Promise((resolve, reject) => {
            const transaction = this.db.transaction(['progress-updates'], 'readwrite');
            const store = transaction.objectStore('progress-updates');
            
            const update = {
                id: Date.now().toString(),
                lessonId: lessonId,
                completed: completed,
                url: url,
                headers: headers,
                body: JSON.stringify({ completed: completed }),
                timestamp: new Date().toISOString()
            };
            
            const request = store.add(update);
            
            request.onsuccess = () => {
                resolve(update);
                // Register background sync
                this.registerBackgroundSync('progress-update');
            };
            
            request.onerror = () => {
                reject(request.error);
            };
        });
    }
    
    // Cache lesson content for offline access
    cacheLessonContent(lessonId, content) {
        return new Promise((resolve, reject) => {
            const transaction = this.db.transaction(['cached-lessons'], 'readwrite');
            const store = transaction.objectStore('cached-lessons');
            
            const cachedLesson = {
                id: lessonId,
                content: content,
                cachedAt: new Date().toISOString()
            };
            
            const request = store.put(cachedLesson);
            
            request.onsuccess = () => {
                resolve(cachedLesson);
            };
            
            request.onerror = () => {
                reject(request.error);
            };
        });
    }
    
    // Get cached lesson content
    getCachedLessonContent(lessonId) {
        return new Promise((resolve, reject) => {
            const transaction = this.db.transaction(['cached-lessons'], 'readonly');
            const store = transaction.objectStore('cached-lessons');
            const request = store.get(lessonId);
            
            request.onsuccess = () => {
                resolve(request.result);
            };
            
            request.onerror = () => {
                reject(request.error);
            };
        });
    }
    
    // Register background sync
    registerBackgroundSync(tag) {
        if ('serviceWorker' in navigator && 'sync' in window.ServiceWorkerRegistration.prototype) {
            navigator.serviceWorker.ready.then((registration) => {
                return registration.sync.register(tag);
            });
        }
    }
    
    // Check if online
    isOnline() {
        return navigator.onLine;
    }
}

// Network status manager
class NetworkStatus {
    constructor() {
        this.callbacks = [];
        this.init();
    }
    
    init() {
        window.addEventListener('online', () => {
            this.updateStatus(true);
        });
        
        window.addEventListener('offline', () => {
            this.updateStatus(false);
        });
        
        // Initial status
        this.updateStatus(navigator.onLine);
    }
    
    updateStatus(isOnline) {
        const indicator = document.getElementById('offline-indicator');
        if (indicator) {
            if (isOnline) {
                indicator.classList.add('d-none');
            } else {
                indicator.classList.remove('d-none');
            }
        }
        
        // Notify callbacks
        this.callbacks.forEach(callback => callback(isOnline));
    }
    
    onStatusChange(callback) {
        this.callbacks.push(callback);
    }
}

// Download manager for lessons
class DownloadManager {
    constructor() {
        this.downloads = new Map();
        this.offlineManager = new OfflineManager();
    }
    
    // Download lesson for offline use
    async downloadLesson(lessonId, lessonUrl) {
        if (this.downloads.has(lessonId)) {
            return; // Already downloading
        }
        
        this.downloads.set(lessonId, { status: 'downloading', progress: 0 });
        this.updateDownloadUI(lessonId, 'downloading', 0);
        
        try {
            const response = await fetch(lessonUrl);
            if (!response.ok) {
                throw new Error('Download failed');
            }
            
            const content = await response.text();
            
            // Cache the lesson content
            await this.offlineManager.cacheLessonContent(lessonId, content);
            
            this.downloads.set(lessonId, { status: 'completed', progress: 100 });
            this.updateDownloadUI(lessonId, 'completed', 100);
            
            // Show success message
            this.showNotification('Lesson downloaded successfully!', 'success');
            
        } catch (error) {
            console.error('Download failed:', error);
            this.downloads.set(lessonId, { status: 'failed', progress: 0 });
            this.updateDownloadUI(lessonId, 'failed', 0);
            
            // Show error message
            this.showNotification('Download failed. Please try again.', 'error');
        }
    }
    
    // Update download UI
    updateDownloadUI(lessonId, status, progress) {
        const downloadBtn = document.querySelector(`[data-lesson-id="${lessonId}"] .download-btn`);
        if (!downloadBtn) return;
        
        switch (status) {
            case 'downloading':
                downloadBtn.innerHTML = `<i class="bi bi-arrow-down-circle"></i> Downloading... ${progress}%`;
                downloadBtn.disabled = true;
                break;
            case 'completed':
                downloadBtn.innerHTML = `<i class="bi bi-check-circle"></i> Downloaded`;
                downloadBtn.classList.remove('btn-outline-success');
                downloadBtn.classList.add('btn-success');
                downloadBtn.disabled = false;
                break;
            case 'failed':
                downloadBtn.innerHTML = `<i class="bi bi-x-circle"></i> Failed`;
                downloadBtn.classList.remove('btn-outline-success');
                downloadBtn.classList.add('btn-outline-danger');
                downloadBtn.disabled = false;
                break;
        }
    }
    
    // Show notification
    showNotification(message, type) {
        const alertClass = type === 'success' ? 'alert-success' : 'alert-danger';
        const icon = type === 'success' ? 'bi-check-circle' : 'bi-x-circle';
        
        const notification = document.createElement('div');
        notification.className = `alert ${alertClass} alert-dismissible fade show position-fixed`;
        notification.style.cssText = 'top: 20px; right: 20px; z-index: 1050; min-width: 300px;';
        notification.innerHTML = `
            <i class="bi ${icon}"></i> ${message}
            <button type="button" class="btn-close" data-bs-dismiss="alert"></button>
        `;
        
        document.body.appendChild(notification);
        
        // Auto-remove after 5 seconds
        setTimeout(() => {
            if (notification.parentNode) {
                notification.remove();
            }
        }, 5000);
    }
}

// Initialize managers
let offlineManager, networkStatus, downloadManager;

document.addEventListener('DOMContentLoaded', function() {
    offlineManager = new OfflineManager();
    networkStatus = new NetworkStatus();
    downloadManager = new DownloadManager();
    
    // Enhanced quiz submission with offline support
    window.submitQuizOffline = function(quizId, answer, url, headers) {
        if (networkStatus.isOnline()) {
            // Submit normally
            return fetch(url, {
                method: 'POST',
                headers: headers,
                body: JSON.stringify({ answer: answer })
            });
        } else {
            // Store for later sync
            return offlineManager.storeQuizSubmission(quizId, answer, url, headers);
        }
    };
    
    // Enhanced progress update with offline support
    window.updateProgressOffline = function(lessonId, completed, url, headers) {
        if (networkStatus.isOnline()) {
            // Update normally
            return fetch(url, {
                method: 'POST',
                headers: headers,
                body: JSON.stringify({ completed: completed })
            });
        } else {
            // Store for later sync
            return offlineManager.storeProgressUpdate(lessonId, completed, url, headers);
        }
    };
    
    // Add download functionality to lesson cards
    document.querySelectorAll('.download-btn').forEach(btn => {
        btn.addEventListener('click', function(e) {
            e.preventDefault();
            const lessonId = this.closest('[data-lesson-id]').getAttribute('data-lesson-id');
            const lessonUrl = this.getAttribute('href');
            downloadManager.downloadLesson(lessonId, lessonUrl);
        });
    });
    
    // Sync when coming back online
    networkStatus.onStatusChange(function(isOnline) {
        if (isOnline) {
            console.log('Back online - syncing data');
            // Trigger background sync
            if ('serviceWorker' in navigator) {
                navigator.serviceWorker.ready.then(registration => {
                    registration.sync.register('quiz-submission');
                    registration.sync.register('progress-update');
                });
            }
        }
    });
});