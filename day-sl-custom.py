import time
import json
import logging
import requests
from datetime import datetime, timedelta

import schedule

from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.common.action_chains import ActionChains
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC

# ========= CONFIG =========

SITES = [
    {"site": "bvnguyentrai.vncare.vn", "username": "BVNT.ADMIN", "password": "If9I8R@_Ox6!t"},
    {"site": "laophoilongan.vncare.vn", "username": "LPLAN.ADMIN", "password": "WG)NU75q+h-6z"},
    {"site": "dakhoahanam.vncare.vn", "username": "DKHNM.ADMIN", "password": "Yjt@7)Uy1ME-0"},
    {"site": "phusannhiquangnam.vncare.vn", "username": "NHQNM.ADMIN", "password": "DuM7!G0(x1Oi_"},
    {"site": "dakhoabuudien.vncare.vn", "username": "BVBDHCM.ADMIN", "password": "bdhcVp_69469#Hv"},
    {"site": "bvmathanam.vncare.vn", "username": "MATHNM.ADMIN", "password": "I42lBn_d2T(O#"},
    {"site": "bvvinhphuc.vncare.vn", "username": "PHCNVPC.ADMIN", "password": "B92b@nD1Te)F-"},
    {"site": "bvyhct.vncare.vn", "username": "YDGLI.ADMIN", "password": "QD9@6llOa(H1@"},
    {"site": "bvtamthan.vncare.vn", "username": "TTKHA_ADMIN", "password": "K0ygYD))61)Vw"},
    {"site": "bvphoi.vncare.vn", "username": "LPGLI.ADMIN", "password": "CBdv8)N53yJ)#"},
    {"site": "bvquany.vncare.vn", "username": "QUANY15.ADMIN", "password": "Q1#2fY_q(3iKA"},
    {"site": "his.vncare.vn", "username": "DKVD.ADMIN", "password": "MG8!qL7-vu3D#"},
    {"site": "bvnhihaiduong.vncare.vn", "username": "NHIHDG.ADMIN", "password": "Gn76)C6+eE#Po"},
    {"site": "bvdakhoa.vncare.vn", "username": "DKDHTNN.ADMIN", "password": "FDe#@F@b364qJ"},
    {"site": "bvlamdong.vncare.vn", "username": "DILINH.ADMIN", "password": "Dd_XuF7!5R1#g"},
    {"site": "bvthaibinh.vncare.vn", "username": "DHYTB.ADMIN", "password": "A0hOe8#fN_+V2"},
    {"site": "bvbinhduong.vncare.vn", "username": "DKCSDT.ADMIN", "password": "JdAR)8#fNk+19"},
    {"site": "bvkhanhhoa.vncare.vn", "username": "DKKHA.ADMIN", "password": "F#@stIJ50-n5B"},
    {"site": "bvlacviet.vncare.vn", "username": "LVVPC.ADMIN", "password": "EiZm9O2@A4!z-"},
    {"site": "bvhatinh.vncare.vn", "username": "DKHTH.ADMIN", "password": "FM!(2_3gAmw5X"},
    {"site": "vnpt-his.vncare.vn", "username": "TKHDG.ADMIN", "password": "WZm8S7_k5+n)L"},
    {"site": "buudienhospital.vncare.vn", "username": "BVBD.ADMIN", "password": "S-v+6Y2yEFb79"},
    {"site": "bvbinhthuan.vncare.vn", "username": "DKBTN.ADMIN", "password": "YI+Bjz9(X1(8x"},
    {"site": "bvcaobang.vncare.vn", "username": "DKCBG.ADMIN", "password": "Vp!Koo@4Q8M3!"},
    {"site": "bvnghean.vncare.vn", "username": "PHCNNAN.ADMIN", "password": "Y#YK03mf@r+1X"},
    # 👉 Thêm các site khác như bạn đã có
]

LOGIN_URL = "https://{}/vnpthis/"
DATA_URL = "https://{}/vnpthis/main/manager.jsp?func=../danhmuc/DaySanLuong"
PUSH_URL = "https://workflow-acp.vnpt.vn/webhook/tiepnhan-his"

TELEGRAM_BOT_TOKEN = "7540006303:AAGPx4NvOOpJSlshbX42W_0YtVrJDuTdznY"
TELEGRAM_CHAT_ID = "-1002611093052"

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(levelname)s - %(message)s"
)


def push_telegram(message):
    url = f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/sendMessage"
    data = {
        "chat_id": TELEGRAM_CHAT_ID,
        "text": message,
        "parse_mode": "HTML"
    }
    try:
        res = requests.post(url, json=data)
        res.raise_for_status()
        logging.info("Đã gửi thông báo Telegram.")
    except Exception as e:
        logging.error(f"Lỗi gửi Telegram: {e}")


def get_access_token():
    logging.info("Lấy access_token ...")
    url = "https://ptsso.vncare.vn/auth/realms/hsskv3/protocol/openid-connect/token"
    headers = {"Content-Type": "application/x-www-form-urlencoded"}
    data = {
        "client_id": "bi-hssk",
        "username": "hisl2.sl",
        "password": "Hisl2@2025",
        "grant_type": "password"
    }
    res = requests.post(url, headers=headers, data=data)
    res.raise_for_status()
    token = res.json()["access_token"]
    logging.info("Lấy token OK.")
    return token


def run_selenium(site, ngay_day):
    options = webdriver.ChromeOptions()
    options.add_argument("--headless")
    options.add_argument("--no-sandbox")
    options.add_argument("--disable-dev-shm-usage")

    driver = webdriver.Chrome(options=options)

    try:
        login_url = LOGIN_URL.format(site["site"])
        data_url = DATA_URL.format(site["site"])

        logging.info(f"[{site['site']}] Mở trang đăng nhập: {login_url}")
        driver.get(login_url)

        driver.find_element(By.NAME, "txtName").send_keys(site["username"])
        driver.find_element(By.NAME, "txtPass").send_keys(site["password"] + Keys.RETURN)
        logging.info(f"[{site['site']}] Đã điền tài khoản, mật khẩu. Đợi login...")

        time.sleep(2)
        logging.info(f"[{site['site']}] Đăng nhập thành công, chuyển sang trang DaySanLuong: {data_url}")
        driver.get(data_url)

        logging.info(f"[{site['site']}] Ngày đẩy: {ngay_day}")

        input_ngay = WebDriverWait(driver, 15).until(
            EC.presence_of_element_located((By.ID, "txtNGAY_DULIEU"))
        )
        input_ngay.clear()
        input_ngay.send_keys(ngay_day)

        btn_get = WebDriverWait(driver, 15).until(
            EC.element_to_be_clickable((By.ID, "btnGET"))
        )
        driver.execute_script("arguments[0].scrollIntoView(true);", btn_get)
        time.sleep(1)
        ActionChains(driver).move_to_element(btn_get).click().perform()
        logging.info(f"[{site['site']}] Đã click nút Lấy dữ liệu")

        WebDriverWait(driver, 30).until(
            lambda d: d.find_element(By.ID, "txtKETQUA").get_attribute("value").strip() != ""
        )
        ketqua = driver.find_element(By.ID, "txtKETQUA").get_attribute("value").strip()

        logging.info(f"[{site['site']}] Lấy dữ liệu OK, độ dài: {len(ketqua)} ký tự.")
        preview = ketqua[:300] + ('...' if len(ketqua) > 300 else '')
        logging.info(f"[{site['site']}] Nội dung mẫu: {preview}")

        return ketqua

    finally:
        driver.quit()


def push_data(raw_json, token):
    try:
        parsed = json.loads(raw_json)
        if not isinstance(parsed, list):
            parsed = [parsed]

        success = 0
        fail = 0

        for block in parsed:
            for item in block["KETQUA"]:
                # Chuyển kiểu dữ liệu chuẩn:
                payload = {
                    "DATA": item["DATA"],
                    "MA_SPDV": item["MA_SPDV"],
                    "MA_TINH": item["MA_TINH"],
                    "MA_CSYT": item["MA_CSYT"],
                    "CUM_DULIEU_ID": item.get("CUM_DULIEU_ID") or "",
                    "CO_GIUONG": int(item["CO_GIUONG"]),
                    "SO_GIUONG": int(item["SO_GIUONG"]),
                    "SO_BENHNHAN": int(item["SO_BENHNHAN"]),
                    "SO_LK_BH_NGT": int(item["SO_LK_BH_NGT"]),
                    "SO_LK_BH_NT": int(item["SO_LK_BH_NT"]),
                    "SO_LK_DV_NGT": int(item["SO_LK_DV_NGT"]),
                    "SO_LK_DV_NT": int(item["SO_LK_DV_NT"]),
                    "NGAY_SOLIEU": datetime.strptime(item["NGAY_SOLIEU"], "%d/%m/%Y").strftime("%Y-%m-%d"),
                    "IS_TEST": int(item["IS_TEST"]),
                    "TRANSACTION_ID": item["TRANSACTION_ID"],
                    "PROVIDER": item["PROVIDER"],
                    "DS_CSYT": item["DS_CSYT"],
                    "CSYT": item["CSYT"],
                    "TEN_BV": item["TEN_BV"],
                    "TUYEN_BV": item["TUYEN_BV"],
                    "HANG_BV": item["HANG_BV"],
                    "SD_YTCS": item["SD_YTCS"],
                    "LT_HSSK": item["LT_HSSK"]
                }

                logging.info(f"➡️ Push request: {json.dumps(payload, ensure_ascii=False)}")
                headers = {"Authorization": f"Bearer {token}"}
                res = requests.post(PUSH_URL, json=payload, headers=headers, timeout=20)
                logging.info(f"⬅️ Push response [{res.status_code}]: {res.text}")

                if res.ok:
                    try:
                        res_data = res.json()
                        if res_data.get("TRANSACTION_ID"):
                            success += 1
                        else:
                            logging.warning("⚠️ Không có TRANSACTION_ID trong response.")
                            fail += 1
                    except Exception as parse_err:
                        logging.error(f"❌ Lỗi parse response JSON: {parse_err}")
                        fail += 1
                else:
                    fail += 1

        return len(parsed), success, fail

    except Exception as e:
        logging.error(f"Lỗi push_data: {e}")
        return 0, 0, 0


def job():
    logging.info("🚀 Bắt đầu job chạy nhiều ngày")
    token = get_access_token()

    start_date = datetime(2025, 6, 1)
    end_date = datetime(2025, 6, 30)

    for site in SITES:
        current = start_date
        while current.date() <= end_date.date():
            ngay_day = current.strftime("%Y-%m-%d")
            logging.info(f"👉 Xử lý {site['site']} ngày {ngay_day}")

            try:
                raw = run_selenium(site, ngay_day)
                if raw:
                    total, success, fail = push_data(raw, token)
                    push_telegram(
                        f"✅ <b>{site['site']}</b> | Ngày: {ngay_day}\n"
                        f"🔢 Tổng: <b>{total}</b> | ✅ Thành công: <b>{success}</b> | ❌ Lỗi: <b>{fail}</b>"
                    )
                else:
                    push_telegram(f"⚠️ {site['site']} không có dữ liệu ngày {ngay_day}")

            except Exception as e:
                logging.error(f"Lỗi site {site['site']}: {e}")
                push_telegram(f"❌ Lỗi site <b>{site['site']}</b>: {e}")

            current += timedelta(days=1)


if __name__ == "__main__":
    # schedule.every().day.at("09:49").do(job)
    job()
    logging.info("⏰ Scheduler đã sẵn sàng! Chờ đến 3h sáng ...")

    while True:
        schedule.run_pending()
        time.sleep(60)
