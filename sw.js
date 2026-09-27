// sw.js - Service Worker for Push Notifications

self.addEventListener('push', function(event) {
    let data = { title: 'نیوز الرٹ', body: 'نئی خبر آ گئی ہے!', url: '/' };
    
    if (event.data) {
        data = event.data.json();
    }
    
    const options = {
        body: data.body,
        icon: data.icon || '/favicon.ico',
        badge: '/favicon.ico',
        data: { url: data.url },
        vibrate: [200, 100, 200],
        requireInteraction: true,
        dir: 'rtl',
        lang: 'ur'
    };
    
    event.waitUntil(
        self.registration.showNotification(data.title, options)
    );
});

self.addEventListener('notificationclick', function(event) {
    event.notification.close();
    event.waitUntil(
        clients.openWindow(event.notification.data.url || '/')
    );
});
