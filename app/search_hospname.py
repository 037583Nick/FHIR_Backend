from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from webdriver_manager.chrome import ChromeDriverManager
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC


def search_hospname(hosp_id):
    # 設置Chrome驅動
    service = Service(ChromeDriverManager().install())
    options = webdriver.ChromeOptions()
    options.add_argument('--headless')  # 在無痕模式下運行
    options.add_argument('--no-sandbox')
    options.add_argument('--disable-dev-shm-usage')
    driver = webdriver.Chrome(service=service, options=options)


    # code = 1336010015
    url = f'https://openinfo.mohw.gov.tw/web/c01?type=1&areaCode=&basName=&basAgencyId={hosp_id}&kind=&depList=&searchmoreList='
    # 訪問URL
    driver.get(url)

    try:
        # 等待表格加载
        table_body = WebDriverWait(driver, 10).until(
            EC.presence_of_element_located((By.ID, "queryListContainer"))
        )
        # 提取所有的行
        rows = table_body.find_elements(By.TAG_NAME, "tr")

        # 疊帶每一行並提取醫療機構名稱
        for row in rows:
            cols = row.find_elements(By.TAG_NAME, "td")
            institution_name = cols[3].text.strip()  # 第四列是醫療機構名稱
            return institution_name
    finally:
        # 關閉瀏覽器
        driver.quit()