import time
import json
import datetime
import db
import tg_ad_actions

def _parse_date(date_str):
    if not date_str:
        return None
    try:
        return datetime.datetime.strptime(date_str, '%Y-%m-%d').date()
    except Exception:
        return None

def check_and_send_ads():
    now = datetime.datetime.now()
    today = now.date()

    for ad in db.get_active_ads():
        start_date = _parse_date(ad.get('start_date'))
        end_date = _parse_date(ad.get('end_date'))

        if start_date and today < start_date:
            continue
        if end_date and today > end_date:
            db.deactivate_ad(ad['id'])
            continue

        total_limit = ad.get('total_limit')
        if total_limit and ad.get('sent_count', 0) >= total_limit:
            db.deactivate_ad(ad['id'])
            continue

        repeat_hours = ad.get('repeat_hours') or 24
        last_sent_at = ad.get('last_sent_at')

        should_send = False
        if not last_sent_at:
            # Hic gonderilmemis: send_time'a gelmis mi kontrol et
            send_time_str = ad.get('send_time')
            if send_time_str:
                try:
                    send_hour, send_min = map(int, send_time_str.split(':'))
                    if now.hour == send_hour and now.minute == send_min:
                        should_send = True
                except Exception:
                    should_send = True
            else:
                should_send = True
        else:
            elapsed_hours = (time.time() - last_sent_at) / 3600
            if elapsed_hours >= repeat_hours:
                should_send = True

        if not should_send:
            continue

        try:
            target_chat_ids = json.loads(ad['target_chat_ids'])
        except Exception:
            target_chat_ids = [x.strip() for x in ad['target_chat_ids'].split(',') if x.strip()]

        for chat_id in target_chat_ids:
            ok, result = tg_ad_actions.send_ad(
                chat_id=chat_id,
                text=ad['text'],
                image_path=ad.get('image_path'),
                button_text=ad.get('button_text'),
                button_url=ad.get('button_url')
            )
            db.mark_sent(ad['id'], chat_id, ok, None if ok else str(result))
            print(f"[ILAN] '{ad['title']}' -> {chat_id}: {'basarili' if ok else 'HATA: ' + str(result)}")

if __name__ == '__main__':
    from apscheduler.schedulers.blocking import BlockingScheduler
    scheduler = BlockingScheduler(timezone="Europe/Istanbul")
    scheduler.add_job(check_and_send_ads, 'interval', minutes=1)
    print("Oto-reklam zamanlayici baslatildi (her 1 dakikada kontrol).")
    check_and_send_ads()
    scheduler.start()
