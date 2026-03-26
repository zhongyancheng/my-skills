# -*- coding: utf-8 -*-

from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.support.ui import WebDriverWait
import time
import json
import re
import hashlib
from collections import defaultdict
from datetime import datetime

BASE_URL = "https://huzhou.bqpoint.com"

KEYWORDS = [
    "可行性","可研"
]

SLEEP = 0.5


# =========================
# 时间
# =========================
def now_time():
    return datetime.now().strftime("%Y-%m-%d %H:%M:%S")


# =========================
# 初始化浏览器
# =========================
def init_driver():
    options = Options()
    options.add_argument("--start-maximized")
    return webdriver.Chrome(options=options)


# =========================
# 等待加载
# =========================
def wait_list(driver):
    WebDriverWait(driver, 10).until(
        lambda d: len(d.find_elements(By.XPATH, "//li")) > 0
    )
    time.sleep(1)


# =========================
# 提取日期（增强版）
# =========================
def extract_date(text):
    if not text:
        return None

    m = re.search(r"(\d{4})[年/-](\d{1,2})[月/-](\d{1,2})", text)
    if m:
        y, mth, d = m.groups()
        return f"{y}-{int(mth):02d}-{int(d):02d}"

    return None


# =========================
# 获取列表（含时间）
# =========================
def get_links(driver):
    items = driver.find_elements(By.XPATH, "//li")

    links = []

    for item in items:
        try:
            a = item.find_element(By.XPATH, ".//a")
            title = a.text.strip()
            url = a.get_attribute("href")

            if not title or not url:
                continue
            if "javascript" in url:
                continue

            # 👉 从列表提取时间（关键）
            publish_time = extract_date(item.text)

            links.append((title, url, publish_time))

        except:
            continue

    return links


# =========================
# 获取详情
# =========================
def get_detail(driver, url):
    try:
        driver.execute_script("window.open(arguments[0]);", url)
        driver.switch_to.window(driver.window_handles[-1])

        WebDriverWait(driver, 10).until(
            lambda d: d.find_element(By.TAG_NAME, "body")
        )

        text = driver.find_element(By.TAG_NAME, "body").text

        driver.close()
        driver.switch_to.window(driver.window_handles[0])

        return text

    except:
        try:
            driver.switch_to.window(driver.window_handles[0])
        except:
            pass
        return ""


# =========================
# 关键词匹配
# =========================
def match_keywords(text):
    return list(set([kw for kw in KEYWORDS if re.search(kw, text)]))


# =========================
# 去重
# =========================
def make_hash(title, url):
    return hashlib.md5((title + url).encode()).hexdigest()


# =========================
# 翻页
# =========================
def click_page(driver, target):
    try:
        old = driver.page_source

        elements = driver.find_elements(By.XPATH, "//a | //span")

        for el in elements:
            if el.text.strip() == str(target):
                driver.execute_script("arguments[0].click();", el)

                WebDriverWait(driver, 10).until(
                    lambda d: d.page_source != old
                )
                return True

        return False

    except:
        return False


# =========================
# 主爬虫
# =========================
def crawl():
    driver = init_driver()

    results = []
    seen = set()
    stats = defaultdict(int)

    idx = 0

    for kw in KEYWORDS:
        print(f"\n🔍 关键词: {kw}")

        driver.get(f"{BASE_URL}/search.html?content={kw}")
        wait_list(driver)

        page = 1

        while page <= 20:
            print(f"📄 第 {page} 页")

            links = get_links(driver)

            if not links:
                break

            stop_flag = False

            for title, url, publish_time in links:

                # ❗ 没时间跳过
                if not publish_time:
                    continue

                # ❗ 小于2025 → 停止翻页
                if publish_time < "2025-01-01":
                    print("⛔ 已进入2025年前数据，停止翻页")
                    stop_flag = True
                    break

                # ❗ 只保留2025
                if not publish_time.startswith("2025"):
                    continue

                h = make_hash(title, url)

                if h in seen:
                    continue
                seen.add(h)

                # 👉 只对符合条件的才进详情
                content = get_detail(driver, url)

                matched = match_keywords(title + content)

                for m in matched:
                    stats[m] += 1

                idx += 1

                results.append({
                    "index": idx,
                    "title": title,
                    "url": url,
                    "keywords": matched,
                    "search_keyword": kw,
                    "page": page,
                    "crawl_time": now_time(),
                    "publish_time": publish_time
                })

                print(f"   ✔ {idx} {title[:30]}")

                time.sleep(SLEEP)

            if stop_flag:
                break

            print(f"   翻页 -> {page + 1}")

            if not click_page(driver, page + 1):
                break

            wait_list(driver)
            page += 1

    driver.quit()
    return results, stats


# =========================
# 主函数
# =========================
def main():
    data, stats = crawl()

    output = {
        "crawl_time": now_time(),
        "total": len(data),
        "keyword_stats": dict(stats),
        "data": data
    }

    print("\n📊 结果：")
    print(f"总数: {len(data)}")

    with open("result_2025.json", "w", encoding="utf-8") as f:
        json.dump(output, f, ensure_ascii=False, indent=2)

    print("\n✅ 已保存 result_2025.json")


if __name__ == "__main__":
    main()