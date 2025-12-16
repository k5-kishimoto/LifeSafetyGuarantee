// static/service_worker.js

self.addEventListener('push', function(event) {
    if (event.data) {
        const data = event.data.json();
        const title = data.head;
        const options = {
            body: data.body,
            icon: data.icon || '/static/images/icon-192.png',
            data: data.data // ここに message_id が入っています
        };
        event.waitUntil(self.registration.showNotification(title, options));
    }
});

self.addEventListener('notificationclick', function(event) {
    event.notification.close();

    // 1. バックエンドから送られた message_id を取得
    const payloadData = event.notification.data;
    
    // ベースとなるURL (ログイン後のホーム画面など)
    // ※ 環境に合わせて '/accounts/' 等に変更してください
    let targetUrl = '/accounts/profile/'; 

    // 2. IDがある場合、URLパラメータ (?open_msg=xxxxx) を付与
    if (payloadData && payloadData.message_id) {
        // すでに?があるかどうかで連結文字を変える
        const separator = targetUrl.includes('?') ? '&' : '?';
        targetUrl += `${separator}open_msg=${payloadData.message_id}`;
    }

    event.waitUntil(
        clients.matchAll({ type: 'window', includeUncontrolled: true }).then(function(clientList) {
            // すでに開いているタブがあれば、そこをフォーカスして移動
            for (let i = 0; i < clientList.length; i++) {
                let client = clientList[i];
                // 同じサイト内なら移動
                if (client.url.includes(self.registration.scope) && 'focus' in client) {
                    return client.focus().then(c => c.navigate(targetUrl));
                }
            }
            // 開いていなければ新規ウィンドウで開く
            if (clients.openWindow) {
                return clients.openWindow(targetUrl);
            }
        })
    );
});