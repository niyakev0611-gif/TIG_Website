/* Waline comment system initialisation (post pages only) */
import { init } from 'https://unpkg.com/@waline/client@v3/dist/waline.js';

init({
  el: '#waline',
  serverURL: 'https://waline-server-lemon.vercel.app',
  lang: 'zh-TW',
  dark: 'html[data-theme="dark"]',
  emoji: false,
  login: 'disable',
  requiredMeta: ['nick'],
  wordLimit: 1000,
  pageSize: 10,
  locale: {
    nick: '名字',
    nickError: '請輸入名字',
    mail: 'Email（可選）',
    mailError: 'Email 格式不正確',
    link: '網址（可選）',
    optional: '可選',
    placeholder: '說點什麼吧…',
    sofa: '還沒有留言，來當第一個吧！',
    submit: '送出',
    reply: '回覆',
    cancelReply: '取消回覆',
    comment: '留言',
    refresh: '重新整理',
    more: '載入更多',
  },
});
