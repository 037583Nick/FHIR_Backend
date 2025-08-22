"""
PNG 格式報告生成器
可以整合到 STEMI.py 中，提供 PNG 格式的診斷報告
"""

from PIL import Image, ImageDraw, ImageFont
from io import BytesIO
import base64

def create_ecg_png_report(report_text, ecg_image_data, width=800, height=600):
    """
    創建 PNG 格式的 ECG 報告
    
    Args:
        report_text (str): 診斷報告文字
        ecg_image_data (bytes): ECG 圖像資料
        width (int): 圖像寬度
        height (int): 圖像高度
    
    Returns:
        str: Base64 編碼的 PNG 資料
    """
    try:
        # 創建白色背景
        img = Image.new('RGB', (width, height), 'white')
        draw = ImageDraw.Draw(img)
        
        # 載入字型
        try:
            font_title = ImageFont.truetype("C:/Windows/Fonts/arial.ttf", 16)
            font_normal = ImageFont.truetype("C:/Windows/Fonts/arial.ttf", 11)
        except:
            try:
                font_title = ImageFont.truetype("C:/Windows/Fonts/simsun.ttc", 16)
                font_normal = ImageFont.truetype("C:/Windows/Fonts/simsun.ttc", 11)
            except:
                font_title = ImageFont.load_default()
                font_normal = ImageFont.load_default()
        
        # 1. 如果有 ECG 圖像資料，插入圖像
        if ecg_image_data:
            try:
                ecg_img = Image.open(BytesIO(ecg_image_data))
                # 調整圖像大小以適合上半部
                ecg_img = ecg_img.resize((width - 40, min(250, height // 2)))
                img.paste(ecg_img, (20, 20))
                text_start_y = ecg_img.height + 40
            except Exception as e:
                print(f"⚠️  ECG 圖像處理失敗: {e}")
                text_start_y = 20
        else:
            text_start_y = 20
        
        # 2. 添加文字報告
        y_text = text_start_y
        lines = report_text.strip().split('\n')
        
        for line in lines:
            line = line.strip()
            if line:
                # 檢查是否為標題
                if any(keyword in line for keyword in ["報告", "分析", "建議", "結論"]):
                    draw.text((20, y_text), line, fill='black', font=font_title)
                    y_text += 22
                else:
                    # 一般文字，處理長行自動換行
                    if len(line) > 60:  # 如果行太長，嘗試分割
                        words = line.split(' ')
                        current_line = ""
                        for word in words:
                            if len(current_line + word) < 60:
                                current_line += word + " "
                            else:
                                if current_line:
                                    draw.text((20, y_text), current_line.strip(), fill='black', font=font_normal)
                                    y_text += 16
                                current_line = word + " "
                        if current_line:
                            draw.text((20, y_text), current_line.strip(), fill='black', font=font_normal)
                            y_text += 16
                    else:
                        draw.text((20, y_text), line, fill='black', font=font_normal)
                        y_text += 16
                
                # 防止文字超出邊界
                if y_text > height - 30:
                    draw.text((20, y_text), "...(報告內容截斷)", fill='gray', font=font_normal)
                    break
        
        # 3. 優化並轉換為 Base64
        png_buffer = BytesIO()
        img.save(png_buffer, format='PNG', optimize=True)
        png_data = base64.b64encode(png_buffer.getvalue()).decode('utf-8')
        
        return png_data
        
    except Exception as e:
        print(f"❌ PNG 報告創建失敗: {e}")
        return None

# 使用範例：
if __name__ == "__main__":
    # 測試用的報告文字
    test_report = """ECG 分析報告
    
患者編號: T37583
分析時間: 2025-08-22
心律分析: 正常竇性心律 (NSR: 85.0%)
STEMI 風險: 低風險 (15.0%)

詳細分析:
- P 波: 正常形態，規律出現
- QRS 波群: 正常寬度，形態規整
- T 波: 無異常變化
- ST 段: 無明顯偏移或抬高

建議:
- 持續監測心律狀況
- 定期追蹤檢查
- 如有胸痛或不適請立即就醫"""
    
    # 創建測試 PNG
    png_data = create_ecg_png_report(test_report, None, 800, 600)
    
    if png_data:
        # 保存測試檔案
        with open("test_png_report.png", "wb") as f:
            f.write(base64.b64decode(png_data))
        
        print(f"✅ PNG 報告創建成功")
        print(f"📊 Base64 資料長度: {len(png_data):,} 字元")
        print(f"📁 測試檔案已保存: test_png_report.png")
    else:
        print("❌ PNG 報告創建失敗")
