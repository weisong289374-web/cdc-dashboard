import requests
from bs4 import BeautifulSoup
import re
import json
import datetime
import time

# ==========================================
# 1. 真实网络抓取模块
# ==========================================
def fetch_cdc_article_text():
    """
    步骤 A：访问疾控中心网站，获取最新周报的纯文本内容。
    (注意：由于政府网站可能变动网址，这里以常见的防爬虫请求方式编写)
    """
    # 假设这是疾控中心发布“全国急性呼吸道传染病哨点监测情况”的列表页或文章页URL
    # 实际部署时，如果 CDC 网址变更，你只需要修改这里的 URL 即可
    target_url = "https://www.chinacdc.cn/jksj/jksj04_14275/" 
    
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/114.0.0.0 Safari/537.36"
    }
    
    try:
        print("正在连接中国疾病预防控制中心官网...")
        response = requests.get(target_url, headers=headers, timeout=15)
        response.encoding = 'utf-8' # 防止中文乱码
        
        # 使用 BeautifulSoup 解析网页
        soup = BeautifulSoup(response.text, 'html.parser')
        
        # 提取网页中所有的文字内容（去除多余的回车和空格）
        page_text = soup.get_text(separator=' ', strip=True)
        return page_text
        
    except Exception as e:
        print(f"网络抓取失败，请检查网络或网址是否变更: {e}")
        return ""

# ==========================================
# 2. 核心：自然语言数字提取模块 (正则表达式)
# ==========================================
def extract_pathogen_data(text, pathogen_keywords):
    """
    步骤 B：在长篇文字中，利用“正则表达式”雷达寻找阳性率数字。
    例如雷达规则：寻找关键词，往后找“阳性率”或“检出率”，再提取紧跟着的数字。
    """
    # 这个规则的意思是：匹配关键词，中间可以隔着几个字，然后是阳性率/检出率/占比，提取百分号前面的数字
    pattern = rf"{pathogen_keywords}.*?(?:阳性率|检出率|占比).*?([0-9]+\.[0-9]+|[0-9]+)\s*%"
    
    match = re.search(pattern, text)
    if match:
        return float(match.group(1)) # 提取成功，返回数字（如 12.5）
    else:
        return None # 没找到，返回空值

# ==========================================
# 3. 数据组装与历史合并模块
# ==========================================
def process_weekly_data():
    """
    步骤 C：将抓取到的最新数字，追加到我们现有的历史数据中。
    """
    article_text = fetch_cdc_article_text()
    
    if not article_text:
        print("⚠️ 未能获取到网页文本，爬虫跳过本次更新。")
        return None

    print("网页抓取成功，正在解析 10 大呼吸道病原体阳性率...")

    # 从文章中动态提取“第X周”的信息
    week_match = re.search(r"(202\d)\s*年\s*第\s*(\d{1,2})\s*周", article_text)
    if week_match:
        current_week_str = f"{week_match.group(1)}年第{week_match.group(2)}周"
    else:
        # 如果文章里没写是第几周，就用当前时间自动生成
        current_year = datetime.datetime.now().year
        current_week_num = datetime.datetime.now().isocalendar()[1]
        current_week_str = f"{current_year}年第{current_week_num}周"

    # 执行智能提取（这里的关键词可以根据 CDC 的行文习惯随时调整）
    new_data = {
        "covid": extract_pathogen_data(article_text, "(?:新冠|新型冠状病毒)"),
        "fluA": extract_pathogen_data(article_text, "甲型流感"),
        "fluB": extract_pathogen_data(article_text, "乙型流感"),
        "rsv": extract_pathogen_data(article_text, "(?:RSV|呼吸道合胞病毒)"),
        "mycoplasma": extract_pathogen_data(article_text, "(?:肺炎支原体|MP)"),
        "adenovirus": extract_pathogen_data(article_text, "(?:腺病毒|ADV)"),
        "rhinovirus": extract_pathogen_data(article_text, "(?:鼻病毒|HRV)"),
        "parainfluenza": extract_pathogen_data(article_text, "(?:副流感|PIV)"),
        "hmpv": extract_pathogen_data(article_text, "(?:偏肺病毒|HMPV)"),
        "coronavirus": extract_pathogen_data(article_text, "(?:普通冠状病毒|季节性冠状病毒)")
    }

    print(f"本周 ({current_week_str}) 解析结果：", new_data)

    # =====================================
    # ⚠️ 历史数据池 (你需要在这里保留过往数据)
    # =====================================
    # 真实运转时，爬虫每次运行只是抓取“本周”的 1 个数字。
    # 以前的数字保存在这里，新抓到的数字会自动追加到这些数组的最后面。
    history = {
        "updateTime": "",
        "weeks": ["2026年第1周", "2026年第2周"],
        "covid": [8.5, 9.2],
        "fluA": [20.1, 22.5],
        "fluB": [3.5, 4.2],
        "rsv": [11.5, 12.8],
        "mycoplasma": [4.8, 5.2],
        "adenovirus": [4.2, 4.8],
        "rhinovirus": [10.0, 9.8],
        "parainfluenza": [4.5, 4.1],
        "hmpv": [4.0, 3.8],
        "coronavirus": [3.5, 3.9]
    }

    # 如果本周的数据尚未收录，则进行追加 (防止重复运行导致数据重复)
    if current_week_str not in history["weeks"]:
        history["weeks"].append(current_week_str)
        # 将新提取的数据加入数组，如果没提取到(None)，则填入 0 或上一周的数据
        for key in new_data:
            val = new_data[key] if new_data[key] is not None else (history[key][-1] if len(history[key]) > 0 else 0)
            history[key].append(val)
    
    history["updateTime"] = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S") + " (自动抓取更新)"
    
    return history

# ==========================================
# 4. 生成 HTML 引擎
# ==========================================
def build_dashboard():
    # 1. 启动爬虫，获取合并后的完整数据
    data = process_weekly_data()
    
    if not data:
        print("未生成新数据，页面更新终止。")
        return

    # 2. 转为 JSON 字符串
    json_str = json.dumps(data, ensure_ascii=False)
    
    # 3. 读取前端模板
    try:
        with open('index_template.html', 'r', encoding='utf-8') as f:
            template = f.read()
    except FileNotFoundError:
        print("❌ 找不到 index_template.html！请确保它和 main.py 在同一个文件夹。")
        return
        
    # 4. 核心替换逻辑：将数据注入前端大屏
    final_html = template.replace("'{{ CDC_DATA_PLACEHOLDER }}'", json_str)
    
    # 5. 保存最终部署文件
    with open('index.html', 'w', encoding='utf-8') as f:
        f.write(final_html)
        
    print("✅ 成功生成最新全国急性呼吸道传染病数字驾驶舱：index.html")

if __name__ == "__main__":
    build_dashboard()