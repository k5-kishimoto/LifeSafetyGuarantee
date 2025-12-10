// static/service_worker.js

self.addEventListener('push', function(event) {
    if (event.data) {
        const data = event.data.json();
        const title = data.head;
        const options = {
            body: data.body,
            icon: data.icon || '/static/images/icon-192.png',
            badge: '/static/images/badge.png',
            data: data.data // message_id がここに入っています
        };
        event.waitUntil(self.registration.showNotification(title, options));
    }
});

self.addEventListener('notificationclick', function(event) {
    event.notification.close();

    // 1. Backendから送られた message_id を取得
    const payloadData = event.notification.data;
    let targetUrl = '/accounts/'; // 基本のURL (必要に応じて変更)

    // 2. IDがある場合、URLパラメータを付与 (?open_msg=xxxxx)
    if (payloadData && payloadData.message_id) {
        // すでに?があるかどうかで連結文字を変える
        const separator = targetUrl.includes('?') ? '&' : '?';
        targetUrl += `${separator}open_msg=${payloadData.message_id}`;
    }

    event.waitUntil(
        clients.matchAll({ type: 'window', includeUncontrolled: true }).then(function(clientList) {
            // 3. すでに開いているタブがあればフォーカスして移動
            for (let i = 0; i < clientList.length; i++) {
                let client = clientList[i];
                // 同じサイトを開いているか確認
                if (client.url.includes('/accounts/') && 'focus' in client) {
                    return client.focus().then(c => c.navigate(targetUrl));
                }
            }
            // 4. 開いていなければ新規ウィンドウで開く
            if (clients.openWindow) {
                return clients.openWindow(targetUrl);
            }
        })
    );
});