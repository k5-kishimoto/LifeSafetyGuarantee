// static/js/service_worker.js

// 通知を受信したときの処理
self.addEventListener('push', function(event) {
    const data = event.data.json();
    const title = data.title || '新しいお知らせ';
    const options = {
        body: data.body || '新しい通知があります。',
        icon: '/static/icons/notification_icon.png', // アイコンパスを設定
        badge: '/static/icons/badge_icon.png'
    };
    
    // 通知を表示
    event.waitUntil(
        self.registration.showNotification(title, options)
    );
});

// 通知をクリックしたときの処理 (アプリを前面に表示するなど)
self.addEventListener('notificationclick', function(event) {
    event.notification.close();
    event.waitUntil(
        clients.openWindow('/') // ホーム画面を開く
    );
});