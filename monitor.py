import os
import sys
import unicodedata
import requests
from playwright.sync_api import sync_playwright

TARGET_URL = os.environ.get("TARGET_URL")
DISCORD_WEBHOOK_URL = os.environ.get("DISCORD_WEBHOOK_URL")

# ★日曜日の監視したいチケット名を指定（両方監視したい場合は2つとも残し、片方なら不要な行を消してください）
TARGET_TICKETS = [
    "１デー - レギュラー (日曜日)",
    "1デー - プレミアム (日曜日)",
]

if not TARGET_URL or not DISCORD_WEBHOOK_URL:
    print("エラー: Secretsが正しく設定されていません。")
    sys.exit(1)

def send_discord_notification(message):
    data = {"content": message}
    requests.post(DISCORD_WEBHOOK_URL, json=data)

def normalize_text(text):
    # 全角英数字やスペース、カッコをすべて半角に統一して表記揺れをなくす
    return unicodedata.normalize("NFKC", text)

def check_ticket():
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        context = browser.new_context(
            locale="ja-JP",
            user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36"
        )
        page = context.new_page()
        
        try:
            page.goto(TARGET_URL, timeout=60000)
            page.wait_for_timeout(8000)
            
            full_text = ""
            for frame in page.frames:
                try:
                    full_text += frame.locator("body").inner_text() + "\n"
                except Exception:
                    pass

            # ページ全体のテキストを正規化（全角→半角統一）
            normalized_full_text = normalize_text(full_text)

            for ticket_name in TARGET_TICKETS:
                norm_ticket_name = normalize_text(ticket_name)

                if norm_ticket_name not in normalized_full_text:
                    print(f"⚠️ ページ内に「{ticket_name}」が見つかりません。")
                    continue

                # チケット名の位置から後ろ250文字を切り出す
                idx = normalized_full_text.find(norm_ticket_name)
                snippet = normalized_full_text[idx : idx + 250]
                
                # 次のチケット枠が混ざらないよう「販売終了日」までの範囲に絞る
                if "販売終了日" in snippet:
                    snippet = snippet.split("販売終了日")[0]

                print(f"--- [{ticket_name}] の現在の取得テキスト ---")
                print(snippet.strip())
                print("-------------------------------------------")

                if ("購入" in snippet or "Buy" in snippet) and ("完売" not in snippet and "Sold Out" not in snippet):
                    send_discord_notification(
                        f"🚨 **【ZAIKO再販検知】**\n"
                        f"**{ticket_name}** が購入可能になりました！\n"
                        f"{TARGET_URL}"
                    )
                    print(f"👉 {ticket_name} の再販通知を送信しました！")
                else:
                    print(f"👉 {ticket_name} は現在も完売中です。")

        except Exception as e:
            print(f"実行中にエラーが発生しました: {e}")
        finally:
            browser.close()

if __name__ == "__main__":
    # ▼ テスト用に追加（確認後に削除）
    send_discord_notification("✅ テスト通知：ZAIKO監視スクリプトから正常に送信できています！")

    check_ticket()
