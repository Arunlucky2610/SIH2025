const CACHE_NAME = 'rural-edu-v2';
const OFFLINE_CACHE = 'rural-edu-offline-v2';
const RUNTIME_CACHE = 'rural-edu-runtime-v2';

const urlsToCache = [
    '/',
    '/static/favicon.svg',
    '/static/icons/icon-192x192.svg',
    '/static/icons/icon-512x512.svg',
    '/manifest.json',
    '/login/',
    '/student/',
    '/teacher/',
    '/parent/',
    'https://cdn.jsdelivr.net/npm/bootstrap@5.3.2/dist/css/bootstrap.min.css',
    'https://cdn.jsdelivr.net/npm/bootstrap-icons@1.11.1/font/bootstrap-icons.css',
    'https://cdn.jsdelivr.net/npm/bootstrap@5.3.2/dist/js/bootstrap.bundle.min.js',
    'https://fonts.googleapis.com/css2?family=Inter:wght@300;400;500;600;700&display=swap'
];

const offlinePages = [
    '/',
    '/login/',
    '/student/',
    '/teacher/',
    '/parent/'
];

// Enhanced install event with better error handling
self.addEventListener('install', function(event) {
    console.log('[SW] Installing Rural Edu Service Worker v2');
    
    event.waitUntil(
        Promise.all([
            // Cache core resources
            caches.open(CACHE_NAME).then(function(cache) {
                console.log('[SW] Caching core resources');
                return cache.addAll(urlsToCache).catch(function(error) {
                    console.error('[SW] Failed to cache some resources:', error);
                    // Continue installation even if some resources fail
                    return Promise.resolve();
                });
            }),
            
            // Cache offline pages
            caches.open(OFFLINE_CACHE).then(function(cache) {
                console.log('[SW] Caching offline pages');
                return Promise.all(
                    offlinePages.map(function(url) {
                        return fetch(url).then(function(response) {
                            if (response.ok) {
                                return cache.put(url, response);
                            }
                        }).catch(function(error) {
                            console.warn('[SW] Failed to cache:', url, error);
                        });
                    })
                );
            })
        ]).then(function() {
            console.log('[SW] Installation complete, taking control');
            return self.skipWaiting();
        })
    );
});

// Activate event - cleanup old caches
self.addEventListener('activate', function(event) {
    console.log('[SW] Activating Rural Edu Service Worker v2');
    
    event.waitUntil(
        Promise.all([
            // Clean up old caches
            caches.keys().then(function(cacheNames) {
                return Promise.all(
                    cacheNames.map(function(cacheName) {
                        if (cacheName !== CACHE_NAME && cacheName !== OFFLINE_CACHE && cacheName !== RUNTIME_CACHE) {
                            console.log('[SW] Deleting old cache:', cacheName);
                            return caches.delete(cacheName);
                        }
                    })
                );
            }),
            
            // Take control of all clients
            self.clients.claim()
        ]).then(function() {
            console.log('[SW] Activation complete, now controlling all pages');
        })
    );
});

// Enhanced fetch event with smart caching strategies
self.addEventListener('fetch', function(event) {
    // Skip non-GET requests and external requests
    if (event.request.method !== 'GET' || !event.request.url.startsWith(self.location.origin)) {
        return;
    }

    event.respondWith(
        caches.match(event.request)
            .then(function(response) {
                if (response) {
                    return response;
                }
                
                return fetch(event.request).then(function(response) {
                    // Don't cache if not a valid response
                    if (!response || response.status !== 200 || response.type !== 'basic') {
                        return response;
                    }
                    
                    // Clone the response for caching
                    var responseToCache = response.clone();
                    
                    // Smart caching strategy
                    var cacheName = CACHE_NAME;
                    if (event.request.url.includes('/static/')) {
                        cacheName = CACHE_NAME; // Static assets
                    } else if (event.request.destination === 'document') {
                        cacheName = RUNTIME_CACHE; // HTML pages
                    }
                    
                    caches.open(cacheName).then(function(cache) {
                        // Avoid caching admin/sensitive routes
                        if (!event.request.url.includes('/admin/') && 
                            !event.request.url.includes('/api/auth/')) {
                            cache.put(event.request, responseToCache);
                        }
                    });
                    
                    return response;
                }).catch(function() {
                    // Network failed - serve appropriate fallback
                    if (event.request.destination === 'document' || event.request.mode === 'navigate') {
                        return caches.match('/offline/').then(function(offlineResponse) {
                            return offlineResponse || caches.match('/');
                        });
                    }
                    
                    // For images, return a placeholder
                    if (event.request.destination === 'image') {
                        return new Response(
                            '<svg xmlns="http://www.w3.org/2000/svg" width="200" height="150" fill="#e9ecef"><rect width="100%" height="100%" fill="#f8f9fa" stroke="#dee2e6"/><text x="50%" y="50%" dominant-baseline="central" text-anchor="middle" fill="#6c757d" font-family="system-ui" font-size="12">Image unavailable offline</text></svg>',
                            { headers: { 'Content-Type': 'image/svg+xml' } }
                        );
                    }
                    
                    // Default offline response
                    return new Response('Content unavailable offline', {
                        status: 503,
                        statusText: 'Service Unavailable',
                        headers: { 'Content-Type': 'text/plain' }
                    });
                });
            })
    );
});

// Activate event - clean up old caches
self.addEventListener('activate', function(event) {
    event.waitUntil(
        caches.keys().then(function(cacheNames) {
            return Promise.all(
                cacheNames.map(function(cacheName) {
                    if (cacheName !== CACHE_NAME) {
                        console.log('Deleting old cache:', cacheName);
                        return caches.delete(cacheName);
                    }
                })
            );
        })
    );
});

// Background sync for offline form submissions
self.addEventListener('sync', function(event) {
    if (event.tag === 'quiz-submission') {
        event.waitUntil(syncQuizSubmissions());
    }
    
    if (event.tag === 'progress-update') {
        event.waitUntil(syncProgressUpdates());
    }
});

// Sync quiz submissions when back online
function syncQuizSubmissions() {
    return getStoredSubmissions('quiz-submissions')
        .then(function(submissions) {
            return Promise.all(
                submissions.map(function(submission) {
                    return fetch(submission.url, {
                        method: 'POST',
                        headers: submission.headers,
                        body: submission.body
                    }).then(function(response) {
                        if (response.ok) {
                            removeStoredSubmission('quiz-submissions', submission.id);
                        }
                        return response;
                    });
                })
            );
        });
}

// Sync progress updates when back online
function syncProgressUpdates() {
    return getStoredSubmissions('progress-updates')
        .then(function(updates) {
            return Promise.all(
                updates.map(function(update) {
                    return fetch(update.url, {
                        method: 'POST',
                        headers: update.headers,
                        body: update.body
                    }).then(function(response) {
                        if (response.ok) {
                            removeStoredSubmission('progress-updates', update.id);
                        }
                        return response;
                    });
                })
            );
        });
}

// Helper functions for IndexedDB operations
function getStoredSubmissions(storeName) {
    return new Promise(function(resolve, reject) {
        var request = indexedDB.open('RuralEduDB', 1);
        
        request.onerror = function() {
            reject(request.error);
        };
        
        request.onsuccess = function() {
            var db = request.result;
            var transaction = db.transaction([storeName], 'readonly');
            var store = transaction.objectStore(storeName);
            var getAllRequest = store.getAll();
            
            getAllRequest.onsuccess = function() {
                resolve(getAllRequest.result);
            };
            
            getAllRequest.onerror = function() {
                reject(getAllRequest.error);
            };
        };
        
        request.onupgradeneeded = function() {
            var db = request.result;
            if (!db.objectStoreNames.contains(storeName)) {
                db.createObjectStore(storeName, { keyPath: 'id' });
            }
        };
    });
}

function removeStoredSubmission(storeName, id) {
    return new Promise(function(resolve, reject) {
        var request = indexedDB.open('RuralEduDB', 1);
        
        request.onsuccess = function() {
            var db = request.result;
            var transaction = db.transaction([storeName], 'readwrite');
            var store = transaction.objectStore(storeName);
            var deleteRequest = store.delete(id);
            
            deleteRequest.onsuccess = function() {
                resolve();
            };
            
            deleteRequest.onerror = function() {
                reject(deleteRequest.error);
            };
        };
    });
}

// Push notification handling
self.addEventListener('push', function(event) {
    const options = {
        body: 'New lesson available for download!',
        icon: '/static/icons/icon-192x192.png',
        badge: '/static/icons/badge-72x72.png',
        tag: 'new-lesson'
    };
    
    event.waitUntil(
        self.registration.showNotification('Rural Digital Learning', options)
    );
});

// Notification click handling
self.addEventListener('notificationclick', function(event) {
    event.notification.close();
    
    event.waitUntil(
        clients.openWindow('/')
    );
});