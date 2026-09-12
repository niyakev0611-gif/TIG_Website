# -*- coding: utf-8 -*-
"""BahnCard 25 九月半價 — 主題圖卡產生器
================================================================
六張 Seedling Flat 資訊卡：
  1 促銷快訊／2 回本門檻（金額）／3 幾趟回本（趟次）
  4 誰該買（版本比價）／5 五個陷阱／6 mydealz 平台入門

用法：
  python3 scripts/cardgen/make_bahncard_cards.py <輸出資料夾>
"""
import os
import sys

from make_weekly_cards import make_card, check_glyphs, check_states

LABEL = 'BahnCard 25'
DATE_RANGE = '9/1–9/30'  # footer 空間有限，勿放長日期（會撞到右側品牌字）

CARDS = [
 dict(
  theme='#C0392B', badges=[('省錢情報', True), ('9/30 截止', False)], illu='train',
  title='BahnCard 25 九月半價 29.99 €',
  subtitle='德國鐵路（DB）官方促銷：9/1–9/30 購買，長途車票一年打 75 折',
  stats=[('29.99 €', '二等艙（原 62.90 €）'),
         ('59.99 €', '一等艙（原 125 €）')],
  bullets=[
   ('買的時間就是這個月', 'DB 官方促銷從 9 月 1 日到 30 日；最晚啟用日同樣是 9 月 30 日，10 月起就恢復原價。'),
   ('折什麼、折多少', '德國境內長途 ICE、IC／EC 的 Flexpreis、Sparpreis、Super Sparpreis 全部再折 25%，有效期整整 12 個月。'),
   ('6 到 18 歲現在免費', 'Jugend BahnCard 25 同步免費到 9/30（原一年 7.90 €），最晚 10/31 啟用，到期自動失效免退訂。'),
  ],
  takeaway=('搶購提醒', 'DB 官方新聞稿標題就寫「只在九月，BahnCard 25 半價」——這是一年一度的檔期，錯過要等明年。'),
  file='BahnCard25_圖卡1_九月半價29歐.png'),
 dict(
  theme='#2E8B57', badges=[('回本試算', True), ('金額門檻', False)], illu='coins',
  title='卡費 × 4 ＝ 回本門檻',
  subtitle='折扣 25% 的意思是：每買 4 € 的原價車票，就省下 1 €',
  stats=[('120 €', '二等艙回本門檻'),
         ('240 €', '一等艙回本門檻')],
  bullets=[
   ('公式只有一條', '回本門檻 ＝ 卡費 ÷ 25%，也就是卡費乘以 4。29.99 € × 4 等於 119.96 €，抓整數就是 120 €。'),
   ('換算成實際支出', '原價 120 € 的票，打折後實付 90 €；換句話說，一年內長途車票只要花掉 90 €，卡費就回來了。'),
   ('和正價卡差多少', '正價 62.90 € 的門檻是 251.60 €，九月買等於把回本線砍掉一半以上。'),
  ],
  takeaway=('數據解讀', '門檻算的是「沒有 BahnCard 時的原價票款」，不是你刷卡的金額——訂票頁上打折前那個價格才是基準。'),
  file='BahnCard25_圖卡2_回本門檻120歐.png'),
 dict(
  theme='#2563EB', badges=[('回本試算', True), ('要搭幾趟', False)], illu='piggybank',
  title='搭幾趟、多久才回本？',
  subtitle='以「原價票款累積到 120 €」換算，票價越高回本越快',
  stats=[('1 趟', '長途 Flexpreis 全票'),
         ('6 趟', '單程 20 € 的特價票')],
  bullets=[
   ('一趟就回本', '跨半個德國的 Flexpreis 全票（不綁車次）常在 150 € 上下，一趟就超過門檻，出發當天卡費就賺回來。'),
   ('一次來回就回本', '單程原價 60 € 的中長途 Sparpreis，來回剛好 120 €——一年只要出遠門一次就打平。'),
   ('小額票要湊幾趟', '單程 40 € 要 3 趟、30 € 要 4 趟、20 € 要 6 趟；等於每兩個月搭一次 20 € 的長途就回本。'),
  ],
  takeaway=('適合誰', '一年內有一趟長途來回、或六趟短程長途就值得買；只搭市內與區域交通的人，這張卡幫不上忙。'),
  file='BahnCard25_圖卡3_幾趟回本.png'),
 dict(
  theme='#7C3AED', badges=[('買前確認', True), ('版本比一比', False)], illu='checklist',
  title='誰該買、誰不用買',
  subtitle='促銷價比青年版與敬老版都便宜；每天通勤的人另有工具',
  stats=[('39.90 €', 'My BahnCard 25 未滿 27'),
         ('40.90 €', '敬老版 65 歲以上')],
  bullets=[
   ('促銷價通殺各版本', '29.99 € 比 27 歲以下的 My BahnCard 25（39.90 €）與 65 歲以上的敬老版（40.90 €）都便宜，且不限年齡。'),
   ('比三個月試用卡划算', 'Probe BahnCard 25 要 19.90 € 卻只給三個月；多花 10 € 就能買到整整 12 個月。'),
   ('通勤族看這裡', 'BahnCard 折的是長途；每天搭市內與區域交通的人，該比較的是 Deutschlandticket（每月 63 €）。'),
  ],
  takeaway=('決策建議', '一年會出遠門一次以上就買；完全不搭長途、或年底要離開德國又不想處理退訂的人可以跳過。'),
  file='BahnCard25_圖卡4_誰該買.png'),
 dict(
  theme='#D4740E', badges=[('注意事項', True), ('別踩雷', False)], illu='contract',
  title='買之前先看這幾行小字',
  subtitle='最貴的一條是自動續約：忘了退訂，明年就是正價 62.90 €',
  stats=[('4 週', '到期前退訂期限'),
         ('14 天', '線上購買撤回權')],
  bullets=[
   ('會自動續約', '到期前 4 週要以文字形式退訂，否則自動轉成正價卡；續約版本依年齡與資格而定，一般成人是 62.90 €。'),
   ('後悔還有 14 天', '線上或電話買的 BahnCard 25 可在 14 天內撤回；但已用它買過折扣票的話，DB 可扣抵已享的折扣。'),
   ('折扣有邊界', 'City-Ticket 不打折、跨國票只折德國段、區域交通看各邦交通聯盟認不認；卡片只有數位版，須有 DB 帳號。'),
  ],
  takeaway=('行事曆提醒', '買完立刻在手機設「到期前五週」的提醒——這是唯一能避免白白多付一整年卡費的方法。'),
  file='BahnCard25_圖卡5_注意事項.png'),
 dict(
  theme='#0D9488', badges=[('平台介紹', True), ('德國省錢', False)], illu='dealtag',
  title='mydealz：德國最大的省錢社群',
  subtitle='這波半價消息就是在這裡先傳開的——它是怎麼運作的？',
  stats=[('2007', '創站年份'),
         ('100 度', '進入熱門榜門檻')],
  bullets=[
   ('人人可貼、社群投票', '2007 年由 Fabian Spielberger 創立，約 300 萬註冊用戶；貼出的優惠由社群按讚或倒讚，總分顯示為「溫度」。'),
   ('平台靠聯盟行銷賺錢', '你點連結去買，平台抽佣金；官方聲明佣金不影響描述與投票，付費曝光一律標示 Gesponsert。'),
   ('留言區才是精華', '運費、能不能疊優惠、退訂陷阱、商家評價，通常都在留言裡先被問出來——下手前務必往下滑。'),
  ],
  takeaway=('使用提醒', '不是每則都真便宜，有些只折 1–4%；最大的風險是「因為便宜而買了不需要的東西」。'),
  file='BahnCard25_圖卡6_mydealz平台.png'),
]

if __name__ == '__main__':
    OUT = sys.argv[1] if len(sys.argv) > 1 else '.'
    os.makedirs(OUT, exist_ok=True)
    for c in CARDS:
        check_states(c)
        check_glyphs(c)
        make_card(c, os.path.join(OUT, c['file']), LABEL, DATE_RANGE)
