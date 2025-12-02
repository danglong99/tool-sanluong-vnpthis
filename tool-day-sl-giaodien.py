import time
import json
import logging
import requests
from datetime import datetime, timedelta
import threading
import tkinter as tk
from tkinter import messagebox, scrolledtext, simpledialog

from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.common.action_chains import ActionChains
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import TimeoutException, WebDriverException

import schedule

# ========= CONFIG (giữ nguyên hoặc chuyển vào GUI) =========
# Các biến cấu hình này sẽ được khởi tạo từ GUI
SITES = []
LOGIN_URL = "https://{}/vnpthis/"
DATA_URL = "https://{}/vnpthis/main/manager.jsp?func=../danhmuc/DaySanLuong"
PUSH_URL = "https://workflow-acp.vnpt.vn/webhook/tiepnhan-his"

TOKEN_URL = "https://ptsso.vncare.vn/auth/realms/hsskv3/protocol/openid-connect/token"
TOKEN_CLIENT_ID = "bi-hssk"
TOKEN_USERNAME = "hisl2.sl"
TOKEN_PASSWORD = "Sanluonghisl2a@"

TELEGRAM_BOT_TOKEN = "7540006303:AAGPx4NvOOpJSlshbX42W_0YtVrJDuTdznY"
TELEGRAM_CHAT_ID = "-1002611093052"

# --- Logger cho GUI ---
class TextHandler(logging.Handler):
    def __init__(self, text_widget):
        super().__init__()
        self.text_widget = text_widget
        self.setFormatter(logging.Formatter("%(asctime)s - %(levelname)s - %(message)s"))

    def emit(self, record):
        msg = self.format(record)
        def append_text():
            self.text_widget.insert(tk.END, msg + "\n")
            self.text_widget.see(tk.END) # Auto scroll to the end
        self.text_widget.after(0, append_text) # Schedule append_text in the main thread

# Khởi tạo logger
logger = logging.getLogger()
logger.setLevel(logging.INFO)
# Các handler cũ nếu có sẽ bị xóa để tránh log ra console 2 lần khi dùng GUI
for handler in logger.handlers[:]:
    logger.removeHandler(handler)

# --- Các hàm Selenium và Request (giữ nguyên) ---

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
        logger.info("Đã gửi thông báo Telegram.")
    except Exception as e:
        logger.error(f"Lỗi gửi Telegram: {e}")

def get_access_token():
    payload = {
        "client_id": TOKEN_CLIENT_ID,
        "username": TOKEN_USERNAME,
        "password": TOKEN_PASSWORD,
        "grant_type": "password"
    }
    headers = {"Content-Type": "application/x-www-form-urlencoded"}
    try:
        res = requests.post(TOKEN_URL, data=payload, headers=headers)
        res.raise_for_status()
        token = res.json().get("access_token")
        if not token:
            raise Exception("Không nhận được access_token")
        logger.info("Đã lấy access_token OK.")
        return token
    except Exception as e:
        logger.error(f"Lỗi lấy token: {e}")
        return None

def run_selenium(site, ngay_day):
    options = webdriver.ChromeOptions()
    options.add_argument("--headless")
    options.add_argument("--no-sandbox")
    options.add_argument("--disable-dev-shm-usage")
    options.page_load_strategy = "eager"

    driver = webdriver.Chrome(options=options)
    driver.set_page_load_timeout(600)

    try:
        login_url = LOGIN_URL.format(site["site"])
        data_url = DATA_URL.format(site["site"])

        logger.info(f"[{site['site']}] Mở trang đăng nhập: {login_url}")
        driver.get(login_url)

        driver.find_element(By.NAME, "txtName").send_keys(site["username"])
        driver.find_element(By.NAME, "txtPass").send_keys(site["password"] + Keys.RETURN)
        logger.info(f"[{site['site']}] Đã điền tài khoản, mật khẩu. Đợi login...")

        time.sleep(2)
        # Kiểm tra xem có chuyển hướng thành công sang trang chính không
        if driver.current_url.startswith("https://ptsso.vncare.vn"):
            logger.error(f"[{site['site']}] Đăng nhập thất bại hoặc chuyển hướng sai trang SSO. URL hiện tại: {driver.current_url}")
            return None

        logger.info(f"[{site['site']}] Đăng nhập thành công, chuyển sang trang DaySanLuong: {data_url}")
        driver.get(data_url)

        logger.info(f"[{site['site']}] Ngày đẩy: {ngay_day}")

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
        logger.info(f"[{site['site']}] Đã click nút Lấy dữ liệu")

        # Tăng thời gian chờ cho kết quả (đây là điểm đã thảo luận)
        WebDriverWait(driver, 600).until( # Tăng thời gian chờ lên 90 giây
            lambda d: d.find_element(By.ID, "txtKETQUA").get_attribute("value").strip() != ""
        )
        ketqua = driver.find_element(By.ID, "txtKETQUA").get_attribute("value").strip()

        logger.info(f"[{site['site']}] Lấy dữ liệu OK, độ dài: {len(ketqua)} ký tự.")
        preview = ketqua[:300] + ('...' if len(ketqua) > 300 else '')
        logger.info(f"[{site['site']}] Nội dung mẫu: {preview}")

        return ketqua

    except TimeoutException as te:
        logger.error(f"[{site['site']}] Lỗi Timeout trong run_selenium: {te}. Có thể do tải trang hoặc chờ phần tử quá lâu.")
        return None
    except WebDriverException as we:
        logger.error(f"[{site['site']}] Lỗi WebDriver trong run_selenium (ví dụ: trình duyệt crash): {we}")
        return None
    except Exception as e:
        logger.error(f"[{site['site']}] Lỗi không xác định trong run_selenium: {e}")
        return None
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

                logger.info(f"➡️ Push request: {json.dumps(payload, ensure_ascii=False)}")
                headers = {"Authorization": f"Bearer {token}"}
                res = requests.post(PUSH_URL, json=payload, headers=headers, timeout=20)
                logger.info(f"⬅️ Push response [{res.status_code}]: {res.text}")

                if res.ok:
                    try:
                        res_data = res.json()
                        if res_data.get("TRANSACTION_ID"):
                            success += 1
                        else:
                            logger.warning("⚠️ Không có TRANSACTION_ID trong response.")
                            fail += 1
                    except Exception as parse_err:
                        logger.error(f"❌ Lỗi parse response JSON: {parse_err}")
                        fail += 1
                else:
                    fail += 1

        return len(parsed), success, fail

    except Exception as e:
        logger.error(f"Lỗi push_data: {e}")
        return 0, 0, 0

def process_sites(site_list, token, ngay_day, is_retry=False):
    failed_sites = []
    prefix = "Lần 2 - " if is_retry else ""

    for site in site_list:
        try:
            logger.info(f"👉 {prefix}Bắt đầu xử lý site: {site['site']}")
            raw = run_selenium(site, ngay_day)

            if raw:
                total, success, fail = push_data(raw, token)
                push_telegram(
                    f"✅ Ngày: {ngay_day}\n"
                    f"✅ <b>{site['site']}</b> đã đẩy dữ liệu\n"
                    f"🔢 Tổng bản ghi: <b>{total}</b>\n"
                    f"✅ Thành công: <b>{success}</b>\n"
                    f"❌ Thất bại: <b>{fail}</b>\n"
                    f"🔗 URL: https://{site['site']}/vnpthis/"
                )
            else:
                logger.warning(f"[{site['site']}] Không có dữ liệu hoặc lỗi Selenium, thêm vào danh sách retry.")
                failed_sites.append(site)
                push_telegram(f"⚠️ {prefix}<b>{site['site']}</b> không có dữ liệu hoặc lỗi trong quá trình thu thập/đăng nhập. Sẽ thử lại sau.")

        except Exception as e:
            logger.error(f"Lỗi {prefix}site {site['site']}: {e}")
            failed_sites.append(site)
            push_telegram(f"❌ {prefix}Lỗi site <b>{site['site']}</b>: {e}. Sẽ thử lại sau.")
    return failed_sites

def main_task_logic(target_date_str=None):
    """Logic chính của tác vụ đẩy dữ liệu."""
    global SITES # Sử dụng biến SITES global

    if not SITES:
        logger.error("Danh sách site rỗng. Vui lòng nhập danh sách site vào giao diện.")
        push_telegram("❌ Danh sách site rỗng. Vui lòng cấu hình tool.")
        return

    logger.info("🎯 Bắt đầu job đẩy dữ liệu...")
    token = get_access_token()
    if not token:
        push_telegram("❌ Lỗi không lấy được token. Dừng job.")
        return

    if target_date_str:
        ngay_day = target_date_str # Sử dụng ngày người dùng nhập
        logger.info(f"Ngày đẩy được chọn từ GUI: {ngay_day}")
    else:
        yesterday = datetime.now() - timedelta(days=1)
        ngay_day = yesterday.strftime("%Y-%m-%d")
        logger.info(f"Ngày đẩy mặc định (hôm qua): {ngay_day}")


    # Lần chạy đầu tiên cho tất cả các site
    logger.info("=========== BẮT ĐẦU LẦN CHẠY ĐẦU TIÊN ===========")
    failed_sites = process_sites(SITES, token, ngay_day, is_retry=False)

    if failed_sites:
        logger.warning(f"Có {len(failed_sites)} site bị lỗi trong lần chạy đầu tiên. Sẽ thử lại sau 5 phút.")
        # Chờ 5 phút trước khi thử lại
        time.sleep(300) # 300 giây = 5 phút

        logger.info("=========== BẮT ĐẦU THỬ LẠI CÁC SITE LỖI ===========")
        final_failed_sites = process_sites(failed_sites, token, ngay_day, is_retry=True)

        if final_failed_sites:
            site_names = ", ".join([s['site'] for s in final_failed_sites])
            push_telegram(f"🚨 Các site sau vẫn bị lỗi sau khi thử lại: <b>{site_names}</b>")
        else:
            push_telegram("✅ Tất cả các site bị lỗi đã được xử lý thành công trong lần thử lại.")
    else:
        push_telegram("✅ Tất cả các site đã đẩy dữ liệu thành công trong lần chạy đầu tiên.")
    logger.info("Hoàn thành job đẩy dữ liệu.")


# --- Giao diện Tkinter ---
class App:
    def __init__(self, master):
        self.master = master
        master.title("VNPT-HIS Data Pusher")
        master.geometry("800x700")

        self.scheduler_thread = None
        self.stop_scheduler_event = threading.Event()

        # Frame cho cấu hình
        config_frame = tk.LabelFrame(master, text="Cấu hình", padx=10, pady=10)
        config_frame.pack(padx=10, pady=10, fill="x", expand=False)

        # Sites Input
        tk.Label(config_frame, text="Danh sách Sites (JSON):").grid(row=0, column=0, sticky="nw", pady=(0, 5))
        self.sites_text = scrolledtext.ScrolledText(config_frame, wrap=tk.WORD, width=70, height=10, font=("TkFixedFont", 10))
        self.sites_text.grid(row=1, column=0, columnspan=2, padx=5, pady=5, sticky="nsew")

        # Ví dụ định dạng JSON
        default_sites_json = """[
    {"site": "bvnguyentrai.vncare.vn", "username": "BVNT.ADMIN", "password": "If9I8R@_Ox6!t"},
    {"site": "laophoilongan.vncare.vn", "username": "LPLAN.ADMIN", "password": "WG)NU75q+h-6z"}
]"""
        self.sites_text.insert(tk.END, default_sites_json)

        # Ngày đẩy
        tk.Label(config_frame, text="Ngày đẩy (YYYY-MM-DD, trống nếu đẩy ngày hôm qua):").grid(row=2, column=0, sticky="w", pady=(10, 5))
        self.date_entry = tk.Entry(config_frame, width=30)
        self.date_entry.grid(row=3, column=0, sticky="w", padx=5, pady=5)
        self.date_entry.insert(0, "") # Mặc định để trống để dùng ngày hôm qua

        # Thời gian đẩy
        tk.Label(config_frame, text="Thời gian đẩy (HH:MM, ví dụ 17:40):").grid(row=2, column=1, sticky="w", pady=(10, 5))
        self.time_entry = tk.Entry(config_frame, width=20)
        self.time_entry.grid(row=3, column=1, sticky="w", padx=5, pady=5)
        self.time_entry.insert(0, "17:40") # Mặc định 17:40

        # Nút chức năng
        button_frame = tk.Frame(master)
        button_frame.pack(pady=5)

        self.start_button = tk.Button(button_frame, text="Bắt đầu Scheduler", command=self.start_scheduler, bg="green", fg="white")
        self.start_button.pack(side=tk.LEFT, padx=5)

        self.stop_button = tk.Button(button_frame, text="Dừng Scheduler", command=self.stop_scheduler, bg="red", fg="white", state=tk.DISABLED)
        self.stop_button.pack(side=tk.LEFT, padx=5)

        self.run_now_button = tk.Button(button_frame, text="Chạy ngay", command=self.run_manual, bg="blue", fg="white")
        self.run_now_button.pack(side=tk.LEFT, padx=5)

        # Log Console
        log_frame = tk.LabelFrame(master, text="Log", padx=10, pady=10)
        log_frame.pack(padx=10, pady=10, fill="both", expand=True)

        self.log_text_widget = scrolledtext.ScrolledText(log_frame, wrap=tk.WORD, width=80, height=20, font=("TkFixedFont", 9), bg="black", fg="white")
        self.log_text_widget.pack(fill="both", expand=True)

        # Đặt logger để ghi vào widget
        self.text_handler = TextHandler(self.log_text_widget)
        logger.addHandler(self.text_handler)

        logger.info("Giao diện đã sẵn sàng. Vui lòng cấu hình và bấm 'Bắt đầu Scheduler'.")


    def parse_sites(self):
        try:
            sites_str = self.sites_text.get("1.0", tk.END).strip()
            if not sites_str:
                messagebox.showerror("Lỗi cấu hình", "Danh sách sites không được để trống.")
                return None
            parsed_sites = json.loads(sites_str)
            if not isinstance(parsed_sites, list):
                messagebox.showerror("Lỗi cấu hình", "Dữ liệu sites phải là một mảng JSON.")
                return None
            for site in parsed_sites:
                if not all(k in site for k in ["site", "username", "password"]):
                    messagebox.showerror("Lỗi cấu hình", "Mỗi site phải có 'site', 'username' và 'password'.")
                    return None
            return parsed_sites
        except json.JSONDecodeError as e:
            messagebox.showerror("Lỗi định dạng JSON", f"Lỗi parse JSON: {e}")
            return None
        except Exception as e:
            messagebox.showerror("Lỗi", f"Lỗi không xác định khi parse sites: {e}")
            return None

    def start_scheduler(self):
        global SITES # Cập nhật biến SITES global
        SITES = self.parse_sites()
        if SITES is None:
            return

        schedule_time = self.time_entry.get().strip()
        if not schedule_time:
            messagebox.showerror("Lỗi", "Thời gian đẩy không được để trống.")
            return

        try:
            # Kiểm tra định dạng thời gian HH:MM
            datetime.strptime(schedule_time, "%H:%M")
        except ValueError:
            messagebox.showerror("Lỗi", "Thời gian đẩy không đúng định dạng HH:MM.")
            return

        self.start_button.config(state=tk.DISABLED)
        self.stop_button.config(state=tk.NORMAL)
        self.run_now_button.config(state=tk.DISABLED)

        logger.info(f"🚀 Scheduler sẽ chạy tác vụ vào lúc {schedule_time} mỗi ngày.")

        schedule.clear() # Xóa các job cũ nếu có
        schedule.every().day.at(schedule_time).do(self.run_scheduled_task)

        # Chạy scheduler trong một luồng riêng
        self.stop_scheduler_event.clear()
        self.scheduler_thread = threading.Thread(target=self._run_scheduler_loop)
        self.scheduler_thread.daemon = True # Cho phép thread dừng khi ứng dụng chính đóng
        self.scheduler_thread.start()

    def _run_scheduler_loop(self):
        while not self.stop_scheduler_event.is_set():
            schedule.run_pending()
            time.sleep(1) # Sleep 1 giây để không lãng phí CPU

    def stop_scheduler(self):
        self.stop_scheduler_event.set()
        if self.scheduler_thread and self.scheduler_thread.is_alive():
            self.scheduler_thread.join(timeout=5) # Chờ thread dừng
            if self.scheduler_thread.is_alive():
                logger.warning("Scheduler thread không dừng đúng cách.")
        schedule.clear()
        self.start_button.config(state=tk.NORMAL)
        self.stop_button.config(state=tk.DISABLED)
        self.run_now_button.config(state=tk.NORMAL)
        logger.info("⛔ Scheduler đã dừng.")

    def run_scheduled_task(self):
        """Hàm được scheduler gọi."""
        selected_date = self.date_entry.get().strip()
        self.master.after(0, lambda: logger.info("Đang chạy tác vụ theo lịch..."))
        # Chạy logic chính trong một luồng riêng để không block GUI
        task_thread = threading.Thread(target=main_task_logic, args=(selected_date if selected_date else None,))
        task_thread.start()

    def run_manual(self):
        """Chạy tác vụ một lần ngay lập tức."""
        global SITES
        SITES = self.parse_sites()
        if SITES is None:
            return

        selected_date = self.date_entry.get().strip()
        confirm = messagebox.askyesno("Xác nhận", f"Bạn có muốn chạy tác vụ đẩy dữ liệu cho ngày {selected_date if selected_date else 'hôm qua'} ngay bây giờ không?")
        if confirm:
            self.run_now_button.config(state=tk.DISABLED)
            self.start_button.config(state=tk.DISABLED)
            self.stop_button.config(state=tk.DISABLED) # Tạm thời disable khi đang chạy
            logger.info("Đang chạy tác vụ thủ công...")
            # Chạy logic chính trong một luồng riêng để không block GUI
            task_thread = threading.Thread(target=self._run_manual_task_wrapper, args=(selected_date if selected_date else None,))
            task_thread.start()

    def _run_manual_task_wrapper(self, selected_date):
        try:
            main_task_logic(selected_date)
        finally:
            self.master.after(0, lambda: self.run_now_button.config(state=tk.NORMAL))
            self.master.after(0, lambda: self.start_button.config(state=tk.NORMAL))
            self.master.after(0, lambda: self.stop_button.config(state=tk.NORMAL if self.scheduler_thread and self.scheduler_thread.is_alive() else tk.DISABLED))


# --- Chạy ứng dụng GUI ---
if __name__ == "__main__":
    root = tk.Tk()
    app = App(root)
    root.mainloop()