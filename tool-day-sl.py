import time
import json
import logging
import requests
from datetime import datetime, timedelta

from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.common.action_chains import ActionChains
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import TimeoutException, NoSuchElementException, WebDriverException
from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from webdriver_manager.chrome import ChromeDriverManager 

import schedule

# --- CẤU HÌNH CHUNG ---
# Danh sách các bệnh viện/site cần xử lý
SITES = [
    {"site": "bvnguyentrai.vncare.vn", "username": "DAYSANLUONG_HISL2", "password": "SlCt2O25@A4!z-@"},
    {"site": "laophoilongan.vncare.vn", "username": "DAYSANLUONG_HISL2", "password": "SlCt2O25@A4!z-@"},
    {"site": "dakhoahanam.vncare.vn", "username": "DAYSANLUONG_HISL2", "password": "SlCt2O25@A4!z-@"},
    {"site": "phusannhiquangnam.vncare.vn", "username": "DAYSANLUONG_HISL2", "password": "SlCt2O25@A4!z-@"},
    {"site": "dakhoabuudien.vncare.vn", "username": "DAYSANLUONG_HISL2", "password": "SlCt2O25@A4!z-@"},
    {"site": "bvmathanam.vncare.vn", "username": "DAYSANLUONG_HISL2", "password": "SlCt2O25@A4!z-@"},
    {"site": "bvvinhphuc.vncare.vn", "username": "DAYSANLUONG_HISL2", "password": "SlCt2O25@A4!z-@"},
    {"site": "bvyhct.vncare.vn", "username": "DAYSANLUONG_HISL2", "password": "SlCt2O25@A4!z-@"},
    {"site": "bvtamthan.vncare.vn", "username": "DAYSANLUONG_HISL2", "password": "SlCt2O25@A4!z-@"},
    {"site": "bvphoi.vncare.vn", "username": "DAYSANLUONG_HISL2", "password": "SlCt2O25@A4!z-@"},
    {"site": "bvquany.vncare.vn", "username": "DAYSANLUONG_HISL2", "password": "SlCt2O25@A4!z-@"},
    {"site": "his.vncare.vn", "username": "DAYSANLUONG_HISL2", "password": "SlCt2O25@A4!z-@"},
    {"site": "bvnhihaiduong.vncare.vn", "username": "DAYSANLUONG_HISL2", "password": "SlCt2O25@A4!z-@"},
    {"site": "bvdakhoa.vncare.vn", "username": "DAYSANLUONG_HISL2", "password": "SlCt2O25@A4!z-@"},
    {"site": "bvlamdong.vncare.vn", "username": "DAYSANLUONG_HISL2", "password": "SlCt2O25@A4!z-@"},
    {"site": "bvthaibinh.vncare.vn", "username": "DAYSANLUONG_HISL2", "password": "SlCt2O25@A4!z-@"},
    {"site": "bvbinhduong.vncare.vn", "username": "DAYSANLUONG_HISL2", "password": "SlCt2O25@A4!z-@"},
    {"site": "bvkhanhhoa.vncare.vn", "username": "DAYSANLUONG_HISL2", "password": "SlCt2O25@A4!z-@"},
    {"site": "bvlacvietpy.vncare.vn", "username": "DAYSANLUONG_HISL2", "password": "SlCt2O25@A4!z-@"},    
    {"site": "bvhatinh.vncare.vn", "username": "DAYSANLUONG_HISL2", "password": "SlCt2O25@A4!z-@"},
    {"site": "vnpt-his.vncare.vn", "username": "DAYSANLUONG_HISL2", "password": "SlCt2O25@A4!z-@"},
    {"site": "buudienhospital.vncare.vn", "username": "DAYSANLUONG_HISL2", "password": "SlCt2O25@A4!z-@"},
    {"site": "bvbinhthuan.vncare.vn", "username": "DAYSANLUONG_HISL2", "password": "SlCt2O25@A4!z-@"},
    {"site": "bvcaobang.vncare.vn", "username": "DAYSANLUONG_HISL2", "password": "SlCt2O25@A4!z-@"},
    {"site": "bvnghean.vncare.vn", "username": "DAYSANLUONG_HISL2", "password": "SlCt2O25@A4!z-@"}
]

# URLs cho các dịch vụ
LOGIN_URL = "https://{}/vnpthis/"
DATA_URL = "https://{}/vnpthis/main/manager.jsp?func=../danhmuc/DaySanLuong"
PUSH_URL = "https://workflow-acp.vnpt.vn/webhook/tiepnhan-his"

# Cấu hình Token Service (PTS SO)
TOKEN_URL = "https://ptsso.vncare.vn/auth/realms/hsskv3/protocol/openid-connect/token"
TOKEN_CLIENT_ID = "bi-hssk"
TOKEN_USERNAME = "hisl2.sl"
TOKEN_PASSWORD = "Sanluonghisl2a@"

# Cấu hình Telegram Bot
TELEGRAM_BOT_TOKEN = "7540006303:AAGPx4NvOOpJSlshbX42W_0YtVrJDuTdznY"
TELEGRAM_CHAT_ID = "-1002611093052" # Đặt ID nhóm chat Telegram của bạn

# Cấu hình Logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(levelname)s - %(message)s"
)

# --- CÁC HÀM HỖ TRỢ ---

def push_telegram(message: str):
    """Gửi thông báo đến Telegram."""
    url = f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/sendMessage"
    data = {
        "chat_id": TELEGRAM_CHAT_ID,
        "text": message,
        "parse_mode": "HTML"
    }
    try:
        res = requests.post(url, json=data)
        res.raise_for_status()  # Ném lỗi cho phản hồi HTTP không thành công (4xx hoặc 5xx)
        logging.info("Telegram: Đã gửi thông báo thành công.")
    except requests.exceptions.RequestException as e:
        logging.error(f"Telegram: Lỗi gửi thông báo: {e}")
    except Exception as e:
        logging.error(f"Telegram: Lỗi không xác định khi gửi thông báo: {e}")

def get_access_token() -> str | None:
    """Lấy Access Token từ dịch vụ SSO."""
    payload = {
        "client_id": TOKEN_CLIENT_ID,
        "username": TOKEN_USERNAME,
        "password": TOKEN_PASSWORD,
        "grant_type": "password"
    }
    headers = {"Content-Type": "application/x-www-form-urlencoded"}
    try:
        logging.info("Đang lấy Access Token...")
        res = requests.post(TOKEN_URL, data=payload, headers=headers, timeout=15)
        res.raise_for_status()
        token = res.json().get("access_token")
        if not token:
            raise ValueError("Không nhận được 'access_token' từ phản hồi.")
        logging.info("Đã lấy Access Token thành công.")
        return token
    except requests.exceptions.RequestException as e:
        logging.error(f"Lỗi khi yêu cầu Access Token: {e}")
        return None
    except json.JSONDecodeError:
        logging.error("Lỗi giải mã JSON từ phản hồi token.")
        return None
    except ValueError as e:
        logging.error(f"Lỗi dữ liệu token: {e}")
        return None
    except Exception as e:
        logging.error(f"Lỗi không xác định khi lấy token: {e}")
        return None

def run_selenium(site: dict, ngay_day: str) -> str | None:
    """
    Sử dụng Selenium để đăng nhập, lấy dữ liệu từ trang 'DaySanLuong'.
    Trả về chuỗi JSON thô nếu thành công, ngược lại trả về None.
    """
    options = webdriver.ChromeOptions()
    options.add_argument("--headless=new")  # Chạy Chrome ở chế độ ẩn
    options.add_argument("--remote-allow-origins=*")
    options.add_argument("--no-sandbox")
    options.add_argument("--disable-dev-shm-usage")
    options.page_load_strategy = "eager" # Tăng tốc độ tải trang
    options.add_argument("--window-size=1920,1080") # Đặt kích thước cửa sổ để tránh các vấn đề về hiển thị
    options.add_argument("--log-level=3") # Chỉ hiển thị lỗi nghiêm trọng từ trình duyệt

    driver = None # Khởi tạo driver là None
    try:
        service = Service(ChromeDriverManager().install())
        driver = webdriver.Chrome(service=service, options=options)
        driver.set_page_load_timeout(90) # Tăng timeout tải trang để an toàn hơn

        login_url = LOGIN_URL.format(site["site"])
        data_url = DATA_URL.format(site["site"])

        logging.info(f"[{site['site']}] Bắt đầu: Mở trang đăng nhập: {login_url}")
        driver.get(login_url)

        # Chờ các trường nhập liệu xuất hiện
        username_field = WebDriverWait(driver, 15).until(
            EC.presence_of_element_located((By.NAME, "txtName"))
        )
        password_field = WebDriverWait(driver, 15).until(
            EC.presence_of_element_located((By.NAME, "txtPass"))
        )

        username_field.send_keys(site["username"])
        password_field.send_keys(site["password"] + Keys.RETURN)
        logging.info(f"[{site['site']}] Đã điền thông tin đăng nhập và gửi. Đang chờ chuyển hướng...")

        # Chờ đến khi URL không còn là trang SSO (nếu có) hoặc chuyển đến trang chính của HIS
        WebDriverWait(driver, 60).until(
            lambda d: not d.current_url.startswith("https://ptsso.vncare.vn") and \
                      ("vnpthis" in d.current_url or "manager.jsp" in d.current_url)
        )

        if "vnpthis/main/main.jsp" not in driver.current_url and "manager.jsp" not in driver.current_url:
            logging.error(f"[{site['site']}] Đăng nhập thất bại hoặc không chuyển hướng đến trang chính HIS. URL hiện tại: {driver.current_url}")
            return None

        logging.info(f"[{site['site']}] Đăng nhập thành công. Chuyển sang trang DaySanLuong: {data_url}")
        driver.get(data_url)

        logging.info(f"[{site['site']}] Ngày dữ liệu cần đẩy: {ngay_day}")

        # Chờ và điền ngày dữ liệu
        input_ngay = WebDriverWait(driver, 20).until(
            EC.presence_of_element_located((By.ID, "txtNGAY_DULIEU"))
        )
        input_ngay.clear()
        input_ngay.send_keys(ngay_day)
        # Đảm bảo input đã được cập nhật bằng cách gửi phím Tab ra khỏi trường
        input_ngay.send_keys(Keys.TAB)
        time.sleep(1) # Đợi một chút để script kích hoạt sự kiện onchange nếu có

        # Chờ nút "Lấy dữ liệu" và click
        btn_get = WebDriverWait(driver, 20).until(
            EC.element_to_be_clickable((By.ID, "btnGET"))
        )
        driver.execute_script("arguments[0].scrollIntoView(true);", btn_get) # Đảm bảo nút hiển thị
        logging.info(f"[{site['site']}] Đã click nút 'Lấy dữ liệu'. Chờ 2 phút để dữ liệu tải...")
        ActionChains(driver).move_to_element(btn_get).click().perform()

        # Sau đó, chờ thêm tối đa 90 giây để textarea có dữ liệu
        WebDriverWait(driver, 600).until(
            lambda d: d.find_element(By.ID, "txtKETQUA").get_attribute("value").strip() != ""
        )
        ketqua = driver.find_element(By.ID, "txtKETQUA").get_attribute("value").strip()

        if not ketqua:
            logging.warning(f"[{site['site']}] Textarea 'txtKETQUA' rỗng sau khi chờ.")
            return None

        logging.info(f"[{site['site']}] Đã lấy dữ liệu từ textarea. Độ dài: {len(ketqua)} ký tự.")
        preview = ketqua[:300] + ('...' if len(ketqua) > 300 else '')
        logging.info(f"[{site['site']}] Nội dung mẫu: {preview}")

        return ketqua

    except (TimeoutException, NoSuchElementException) as e:
        logging.error(f"[{site['site']}] Lỗi tìm phần tử hoặc timeout trong Selenium: {e}")
        # Chụp ảnh màn hình lỗi để debug
        if driver:
            driver.save_screenshot(f"error_selenium_{site['site']}_{datetime.now().strftime('%Y%m%d_%H%M%S')}.png")
        return None
    except WebDriverException as e:
        logging.error(f"[{site['site']}] Lỗi WebDriver (có thể do trình duyệt hoặc driver): {e}")
        return None
    except Exception as e:
        logging.error(f"[{site['site']}] Lỗi không xác định trong run_selenium: {e}")
        return None
    finally:
        if driver:
            driver.quit() # Đảm bảo đóng trình duyệt sau khi hoàn thành hoặc có lỗi

def push_data(raw_json: str, token: str) -> tuple[int, int, int]:
    """
    Phân tích cú pháp JSON thô và đẩy từng bản ghi đến dịch vụ workflow.
    Trả về tổng số bản ghi, số bản ghi thành công và số bản ghi thất bại.
    """
    total_records = 0
    success_pushes = 0
    failed_pushes = 0

    try:
        parsed_data = json.loads(raw_json)
        if not isinstance(parsed_data, list):
            # Nếu raw_json là một đối tượng JSON duy nhất, chuyển nó thành danh sách chứa đối tượng đó
            parsed_data = [parsed_data]

        for block in parsed_data:
            if "KETQUA" not in block or not isinstance(block["KETQUA"], list):
                logging.warning(f"Cấu trúc JSON không hợp lệ: Thiếu khóa 'KETQUA' hoặc 'KETQUA' không phải là danh sách trong block: {block}")
                continue # Bỏ qua block này

            for item in block["KETQUA"]:
                total_records += 1
                try:
                    # Chuyển đổi kiểu dữ liệu cho đúng định dạng API yêu cầu
                    payload = {
                        "DATA": item.get("DATA", ""),
                        "MA_SPDV": item.get("MA_SPDV", ""),
                        "MA_TINH": item.get("MA_TINH", ""),
                        "MA_CSYT": item.get("MA_CSYT", ""),
                        "CUM_DULIEU_ID": item.get("CUM_DULIEU_ID", ""),
                        "CO_GIUONG": int(item.get("CO_GIUONG", 0)),
                        "SO_GIUONG": int(item.get("SO_GIUONG", 0)),
                        "SO_BENHNHAN": int(item.get("SO_BENHNHAN", 0)),
                        "SO_LK_BH_NGT": int(item.get("SO_LK_BH_NGT", 0)),
                        "SO_LK_BH_NT": int(item.get("SO_LK_BH_NT", 0)),
                        "SO_LK_DV_NGT": int(item.get("SO_LK_DV_NGT", 0)),
                        "SO_LK_DV_NT": int(item.get("SO_LK_DV_NT", 0)),
                        "NGAY_SOLIEU": datetime.strptime(item["NGAY_SOLIEU"], "%d/%m/%Y").strftime("%Y-%m-%d") if item.get("NGAY_SOLIEU") else "",
                        "IS_TEST": int(item.get("IS_TEST", 0)),
                        "TRANSACTION_ID": item.get("TRANSACTION_ID", ""),
                        "PROVIDER": item.get("PROVIDER", ""),
                        "DS_CSYT": item.get("DS_CSYT", ""),
                        "CSYT": item.get("CSYT", ""),
                        "TEN_BV": item.get("TEN_BV", ""),
                        "TUYEN_BV": item.get("TUYEN_BV", ""),
                        "HANG_BV": item.get("HANG_BV", ""),
                        "SD_YTCS": item.get("SD_YTCS", ""),
                        "LT_HSSK": item.get("LT_HSSK", "")
                    }

                    logging.info(f"➡️ Push request (item {total_records}): {json.dumps(payload, ensure_ascii=False)[:200]}...") # Log 200 ký tự đầu
                    headers = {"Authorization": f"Bearer {token}", "Content-Type": "application/json"}
                    res = requests.post(PUSH_URL, json=payload, headers=headers, timeout=30)
                    logging.info(f"⬅️ Push response (item {total_records}) [{res.status_code}]: {res.text[:200]}...") # Log 200 ký tự đầu

                    if res.ok:
                        try:
                            res_data = res.json()
                            if res_data.get("TRANSACTION_ID"):
                                success_pushes += 1
                            else:
                                logging.warning(f"⚠️ Push thành công HTTP (2xx) nhưng không có TRANSACTION_ID trong response (item {total_records}).")
                                failed_pushes += 1
                        except json.JSONDecodeError:
                            logging.warning(f"⚠️ Push thành công HTTP (2xx) nhưng lỗi giải mã JSON response (item {total_records}).")
                            failed_pushes += 1
                    else:
                        logging.error(f"❌ Push thất bại HTTP status {res.status_code} (item {total_records}). Response: {res.text}")
                        failed_pushes += 1

                except ValueError as ve:
                    logging.error(f"Lỗi chuyển đổi kiểu dữ liệu cho bản ghi (item {total_records}): {ve}. Bản ghi bị bỏ qua.")
                    failed_pushes += 1
                except requests.exceptions.RequestException as re:
                    logging.error(f"Lỗi mạng/HTTP khi push bản ghi (item {total_records}): {re}. Bản ghi bị bỏ qua.")
                    failed_pushes += 1
                except Exception as ex:
                    logging.error(f"Lỗi không xác định khi xử lý hoặc push bản ghi (item {total_records}): {ex}. Bản ghi bị bỏ qua.")
                    failed_pushes += 1

    except json.JSONDecodeError:
        logging.error(f"Lỗi giải mã JSON đầu vào: Dữ liệu không phải là JSON hợp lệ hoặc có cấu trúc bất ngờ.")
        return 0, 0, 0 # Không thể parse, coi như không có bản ghi nào được xử lý
    except Exception as e:
        logging.error(f"Lỗi chung trong hàm push_data: {e}")
        return 0, 0, 0

    return total_records, success_pushes, failed_pushes

def process_sites(site_list: list[dict], token: str, ngay_day: str, is_retry: bool = False) -> list[dict]:
    """
    Xử lý danh sách các site, thu thập và đẩy dữ liệu.
    Trả về danh sách các site bị lỗi để thử lại.
    """
    failed_sites = []
    prefix = "LẦN 2 - " if is_retry else ""

    for site in site_list:
        site_name = site['site']
        try:
            logging.info(f"--- 👉 {prefix}Bắt đầu xử lý site: {site_name} ---")
            raw_data_json = run_selenium(site, ngay_day)

            if raw_data_json:
                total, success, fail = push_data(raw_data_json, token)
                status_message = (
                    f"✅ Ngày: <b>{ngay_day}</b>\n"
                    f"✅ <b>{site_name}</b> đã đẩy dữ liệu\n"
                    f"🔢 Tổng bản ghi: <b>{total}</b>\n"
                    f"✅ Thành công: <b>{success}</b>\n"
                    f"❌ Thất bại: <b>{fail}</b>\n"
                    f"🔗 URL: https://{site_name}/vnpthis/"
                )
                if fail > 0:
                    push_telegram(f"⚠️ {status_message}\nMột số bản ghi thất bại. Vui lòng kiểm tra log.")
                else:
                    push_telegram(status_message)
                logging.info(f"[{site_name}] Hoàn thành xử lý. Tổng: {total}, Thành công: {success}, Thất bại: {fail}")
            else:
                logging.warning(f"[{site_name}] Không lấy được dữ liệu hoặc lỗi trong Selenium. Thêm vào danh sách thử lại.")
                failed_sites.append(site)
                push_telegram(f"⚠️ {prefix}<b>{site_name}</b> không lấy được dữ liệu hoặc lỗi đăng nhập/thu thập. Sẽ thử lại sau.")

        except Exception as e:
            logging.error(f"[{site_name}] Lỗi không xác định khi xử lý site: {e}")
            failed_sites.append(site)
            push_telegram(f"❌ {prefix}Lỗi nghiêm trọng khi xử lý site <b>{site_name}</b>: {e}. Sẽ thử lại sau.")
    return failed_sites

# --- HÀM CHÍNH ĐƯỢC LẬP LỊCH ---

def main_task():
    """
    Hàm chính chạy hàng ngày để thu thập và đẩy dữ liệu.
    """
    logging.info("\n" + "="*80)
    logging.info("🎯 BẮT ĐẦU JOB ĐẨY DỮ LIỆU HÀNG NGÀY...")
    logging.info("="*80 + "\n")

    # 1. Lấy Access Token
    token = get_access_token()
    if not token:
        push_telegram("❌ Lỗi: Không lấy được Access Token. Dừng job.")
        logging.error("Không lấy được Access Token. Dừng toàn bộ job.")
        return

    # 2. Xác định ngày cần đẩy dữ liệu (ngày hôm qua)
    yesterday = datetime.now() - timedelta(days=1)
    ngay_day = yesterday.strftime("%Y-%m-%d") # Định dạng YYYY-MM-DD cho input

    # 3. Lần chạy đầu tiên cho tất cả các site
    logging.info(f"\n=========== BẮT ĐẦU LẦN CHẠY ĐẦU TIÊN cho ngày {ngay_day} ===========")
    failed_sites_initial = process_sites(SITES, token, ngay_day, is_retry=False)

    if failed_sites_initial:
        logging.warning(f"Có {len(failed_sites_initial)} site bị lỗi trong lần chạy đầu tiên. Đang chờ 5 phút để thử lại.")
        push_telegram(f"⚠️ Có {len(failed_sites_initial)} site bị lỗi trong lần chạy đầu tiên. Đang chờ 5 phút để thử lại.")
        time.sleep(300) # Chờ 5 phút (300 giây)

        # 4. Thử lại các site lỗi
        logging.info(f"\n=========== BẮT ĐẦU THỬ LẠI CÁC SITE LỖI (Lần 2) cho ngày {ngay_day} ===========")
        final_failed_sites = process_sites(failed_sites_initial, token, ngay_day, is_retry=True)

        if final_failed_sites:
            site_names = ", ".join([s['site'] for s in final_failed_sites])
            logging.error(f"🚨 Các site sau vẫn bị lỗi sau khi thử lại: {site_names}")
            push_telegram(f"🚨 Các site sau vẫn bị lỗi sau khi thử lại: <b>{site_names}</b>. Vui lòng kiểm tra thủ công.")
        else:
            logging.info("✅ Tất cả các site bị lỗi đã được xử lý thành công trong lần thử lại.")
            push_telegram("✅ Tất cả các site bị lỗi đã được xử lý thành công trong lần thử lại.")
    else:
        logging.info("✅ Tất cả các site đã đẩy dữ liệu thành công trong lần chạy đầu tiên.")
        push_telegram("✅ Tất cả các site đã đẩy dữ liệu thành công trong lần chạy đầu tiên.")

    logging.info("\n" + "="*80)
    logging.info("✅ JOB ĐẨY DỮ LIỆU ĐÃ KẾT THÚC.")
    logging.info("="*80 + "\n")

# --- LẬP LỊCH CHẠY HÀNG NGÀY ---
# Lập lịch chạy job vào 02:30 sáng mỗi ngày
schedule.every().day.at("17:00").do(main_task)
#main_task()
logging.info("🚀 Scheduler đã khởi động. Đang chờ job chạy lúc 17:00 mỗi ngày...")

# Vòng lặp chính để chạy các job đã được lập lịch
while True:
    schedule.run_pending()
    time.sleep(30) # Kiểm tra mỗi 30 giây



