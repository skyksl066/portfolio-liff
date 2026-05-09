import liff from '@line/liff';
import { LIFF_ID, DEV_MODE, SCRIPT_ROOT } from './config.js';

const appAuth = {
    accessToken: null,
    userId: null,
    displayName: null,
};

const _ICON_LOCK =
    '<svg aria-hidden="true" focusable="false" viewBox="0 0 24 24" fill="none" ' +
    'stroke="currentColor" stroke-width="1.5" stroke-linecap="round" stroke-linejoin="round">' +
    '<rect x="3" y="11" width="18" height="11" rx="2"/>' +
    '<path d="M7 11V7a5 5 0 0 1 10 0v4"/></svg>';

const _ICON_WARN =
    '<svg aria-hidden="true" focusable="false" viewBox="0 0 24 24" fill="none" ' +
    'stroke="currentColor" stroke-width="1.5" stroke-linecap="round" stroke-linejoin="round">' +
    '<path d="M10.29 3.86 1.82 18a2 2 0 0 0 1.71 3h16.94a2 2 0 0 0 1.71-3L13.71 3.86a2 2 0 0 0-3.42 0z"/>' +
    '<line x1="12" y1="9" x2="12" y2="13"/><line x1="12" y1="17" x2="12.01" y2="17"/></svg>';

const _ICON_CLOCK =
    '<svg aria-hidden="true" focusable="false" viewBox="0 0 24 24" fill="none" ' +
    'stroke="currentColor" stroke-width="1.5" stroke-linecap="round" stroke-linejoin="round">' +
    '<circle cx="12" cy="12" r="10"/>' +
    '<polyline points="12 6 12 12 16 14"/></svg>';

const _ICON_CLIPBOARD =
    '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" ' +
    'stroke-linecap="round" stroke-linejoin="round">' +
    '<rect x="9" y="2" width="6" height="4" rx="1"/>' +
    '<path d="M8 4H6a2 2 0 0 0-2 2v14a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V6a2 2 0 0 0-2-2h-2"/>' +
    '<line x1="12" y1="11" x2="12" y2="17"/><line x1="9" y1="14" x2="15" y2="14"/></svg>';

const _ICON_CHECK =
    '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.5" ' +
    'stroke-linecap="round" stroke-linejoin="round">' +
    '<polyline points="20 6 9 17 4 12"/></svg>';

function showSessionExpired() {
    document.body.innerHTML =
        '<div class="forbidden" role="alert">' +
            '<div class="forbidden-icon forbidden-icon--warn">' + _ICON_CLOCK + '</div>' +
            '<h2>工作階段已逾時</h2>' +
            '<p>頁面閒置過久，LINE 授權已失效<br>請重新載入以繼續使用</p>' +
            '<button class="btn-reload" type="button">重新載入</button>' +
        '</div>';
    document.querySelector('.btn-reload').addEventListener('click', () => location.reload());
}

function showForbidden(userId) {
    document.body.innerHTML =
        '<div class="forbidden" role="alert">' +
            '<div class="forbidden-icon">' + _ICON_LOCK + '</div>' +
            '<h2>無存取權限</h2>' +
            '<p>你的 LINE ID 尚未在白名單中<br>請複製下方 ID 並提供給管理員</p>' +
            '<div class="id-copy-row">' +
                '<code id="forbidden-uid">' + escapeHtml(userId) + '</code>' +
                '<button class="copy-btn" id="btn-copy-uid" type="button" aria-label="複製 ID">' +
                    _ICON_CLIPBOARD +
                '</button>' +
            '</div>' +
        '</div>';

    document.getElementById('btn-copy-uid').addEventListener('click', function () {
        const btn = document.getElementById('btn-copy-uid');
        const doSuccess = function () {
            btn.classList.add('copied');
            btn.setAttribute('aria-label', '已複製');
            btn.innerHTML = _ICON_CHECK;
            setTimeout(function () {
                btn.classList.remove('copied');
                btn.setAttribute('aria-label', '複製 ID');
                btn.innerHTML = _ICON_CLIPBOARD;
            }, 2000);
        };
        if (navigator.clipboard && navigator.clipboard.writeText) {
            navigator.clipboard.writeText(userId).then(doSuccess).catch(function () {
                _selectText(document.getElementById('forbidden-uid'));
            });
        } else {
            _selectText(document.getElementById('forbidden-uid'));
        }
    });
}

function _selectText(el) {
    try {
        const range = document.createRange();
        range.selectNodeContents(el);
        const sel = window.getSelection();
        sel.removeAllRanges();
        sel.addRange(range);
    } catch (e) { /* ignore */ }
}

function showFatal(msg) {
    document.body.innerHTML =
        '<div class="forbidden" role="alert">' +
            '<div class="forbidden-icon">' + _ICON_WARN + '</div>' +
            '<h2>無法啟動</h2>' +
            '<p>' + escapeHtml(msg) + '</p>' +
        '</div>';
}

function makeApiError(code, message) {
    const e = new Error(message);
    e.code = code;
    return e;
}

export function escapeHtml(s) {
    return String(s)
        .replace(/&/g, '&amp;')
        .replace(/</g, '&lt;')
        .replace(/>/g, '&gt;')
        .replace(/"/g, '&quot;')
        .replace(/'/g, '&#39;');
}

export async function initLiff() {
    if (DEV_MODE) {
        appAuth.accessToken = 'dev-fake-token';
        appAuth.userId = 'U_dev_test_user';
        appAuth.displayName = 'Dev User';
        return true;
    }
    if (!LIFF_ID) {
        showFatal('LIFF_ID 未設定，請聯絡管理員。');
        return false;
    }
    try {
        await liff.init({ liffId: LIFF_ID });
    } catch (e) {
        showFatal('LIFF 初始化失敗：' + (e && e.message ? e.message : e));
        return false;
    }
    if (!liff.isLoggedIn()) {
        liff.login();
        return false;
    }
    appAuth.accessToken = liff.getAccessToken();
    try {
        const profile = await liff.getProfile();
        appAuth.userId = profile.userId;
        appAuth.displayName = profile.displayName;
    } catch (e) {
        appAuth.displayName = null;
    }
    return true;
}

export async function api(path, options = {}) {
    const token = (!DEV_MODE && liff.isLoggedIn())
        ? (liff.getAccessToken() || appAuth.accessToken || '')
        : (appAuth.accessToken || '');
    const headers = {
        'Authorization': 'Bearer ' + token,
        'Content-Type': 'application/json',
        ...(options.headers || {}),
    };
    const resp = await fetch(SCRIPT_ROOT + path, { ...options, headers });
    if (resp.status === 403) {
        const body = await resp.json().catch(() => ({}));
        showForbidden(body.userId || appAuth.userId || '(未知)');
        throw makeApiError('FORBIDDEN', '不在白名單');
    }
    if (resp.status === 401) {
        showSessionExpired();
        throw makeApiError('UNAUTHORIZED', 'session expired');
    }
    if (!resp.ok) {
        const body = await resp.json().catch(() => ({}));
        throw makeApiError('HTTP_ERROR', body.message || ('HTTP ' + resp.status));
    }
    if (resp.status === 204) return null;
    return resp.json();
}
