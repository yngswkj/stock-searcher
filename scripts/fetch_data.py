import yfinance as yf
import pandas as pd
import json
import time
import os

# --- 設定 ---
# 米国株: 本来はS&P600等の全リストを使うが、ここではデモ用リスト
US_TICKERS = ["RUM", "IONQ", "HIMS", "PLTR", "SOFI", "APPS", "CROX"]

# 日本株: 取得したい市場区分
TARGET_JP_MARKETS = ['グロース', 'スタンダード']

# 【運用設定】
# デバッグモード: 環境変数 GITHUB_ACTIONS があれば False (本番)、なければ True (デバッグ)
DEBUG_MODE = os.getenv('GITHUB_ACTIONS') != 'true'
DEBUG_LIMIT = 50

# 本番での銘柄数上限（yfinanceのAPI制限・時間制約対策）
# グロース: 全銘柄、スタンダード: 時価総額が小さい順で上限まで
PRODUCTION_LIMIT_STANDARD = 300  # スタンダード市場の上限

# 事前フィルタリング基準 (JSONサイズ削減のため)
# これを超える時価総額の銘柄は保存しない (単位: USD)
# ここでは200億ドル(約3兆円)を上限とする
FILTER_MAX_MARKET_CAP_USD = 20_000_000_000 

def get_jpx_tickers(limit_standard=None):
    """
    JPXから日本株全銘柄を取得し、対象市場のティッカー(.T)を返す
    
    抽出ルール:
    - グロース市場: 全銘柄（小型成長株が多いため優先）
    - スタンダード市場: 時価総額の小さい順で上限まで（小型株優先）
    """
    print("Fetching JPX ticker list...")
    try:
        url = "https://www.jpx.co.jp/markets/statistics-equities/misc/tvdivq0000001vg2-att/data_j.xls"
        df = pd.read_excel(url)
        
        tickers = []
        
        # グロース市場: 全銘柄取得（小型成長株が多い）
        growth_mask = df['市場・商品区分'].str.contains('グロース', na=False)
        growth_tickers = (df[growth_mask]['コード'].astype(str) + ".T").tolist()
        print(f"  Growth market: {len(growth_tickers)} tickers")
        tickers.extend(growth_tickers)
        
        # スタンダード市場: 時価総額順でソートし上限まで取得
        standard_mask = df['市場・商品区分'].str.contains('スタンダード', na=False)
        standard_df = df[standard_mask].copy()
        
        # 時価総額列があればソート（なければそのまま）
        if '時価総額' in standard_df.columns:
            standard_df = standard_df.sort_values('時価総額', ascending=True)
            print(f"  Standard market: sorted by market cap (ascending)")
        
        standard_tickers = (standard_df['コード'].astype(str) + ".T").tolist()
        
        if limit_standard and len(standard_tickers) > limit_standard:
            standard_tickers = standard_tickers[:limit_standard]
            print(f"  Standard market: {limit_standard} tickers (limited from {len(df[standard_mask])})")
        else:
            print(f"  Standard market: {len(standard_tickers)} tickers")
        
        tickers.extend(standard_tickers)
        
        return tickers
    except Exception as e:
        print(f"Error fetching JPX: {e}")
        return []

def main():
    data_list = []
    
    # 1. リスト作成
    if DEBUG_MODE:
        # デバッグ時は上限なしで取得し、後で制限
        jp_tickers = get_jpx_tickers()
        print(f"DEBUG MODE: Limiting JP tickers to first {DEBUG_LIMIT}")
        jp_tickers = jp_tickers[:DEBUG_LIMIT]
    else:
        # 本番時はスタンダード市場に上限を設ける
        jp_tickers = get_jpx_tickers(limit_standard=PRODUCTION_LIMIT_STANDARD)
        
    all_tickers = US_TICKERS + jp_tickers
    
    print(f"Processing {len(all_tickers)} tickers...")

    for symbol in all_tickers:
        try:
            ticker = yf.Ticker(symbol)
            info = ticker.info
            
            market_cap = info.get('marketCap')
            
            # 必須データのチェック
            if market_cap:
                # 通貨判定と単位変換
                currency = info.get('currency', 'USD')
                is_jp = currency == 'JPY'
                
                # フィルタ用: ドル換算の時価総額 (1ドル=150円換算)
                if is_jp:
                    mcap_sort_usd = market_cap / 150_000_000_000 # Billion USD
                    mcap_display = round(market_cap / 100_000_000, 2) # 億円
                else:
                    mcap_sort_usd = market_cap / 1_000_000_000 # Billion USD
                    mcap_display = round(market_cap / 1_000_000_000, 2) # Billion USD

                # 【事前フィルタリング】
                # 時価総額が大きすぎる銘柄は、このアプリの対象外なので保存しない
                # これによりJSONサイズを削減する
                raw_mcap_usd = mcap_sort_usd * 1_000_000_000
                if raw_mcap_usd > FILTER_MAX_MARKET_CAP_USD:
                    print(f"Skipped {symbol}: Market Cap too large (${mcap_sort_usd:.2f}B)")
                    continue

                # FCF利回り計算
                fcf = info.get('freeCashflow')
                fcf_yield = round((fcf / market_cap) * 100, 2) if fcf else 0
                
                # ROE
                roe = round(info.get('returnOnEquity', 0) * 100, 2) if info.get('returnOnEquity') else 0

                # 追加指標
                pbr = info.get('priceToBook', 0)
                revenue_growth = round(info.get('revenueGrowth', 0) * 100, 2) if info.get('revenueGrowth') else 0
                profit_margin = round(info.get('profitMargins', 0) * 100, 2) if info.get('profitMargins') else 0

                data_list.append({
                    "ticker": symbol,
                    "name": info.get('shortName', symbol),
                    "country": "JP" if is_jp else "US",
                    "price": info.get('currentPrice'),
                    "mcap_display": mcap_display,      # 表示用数値 (単位は国による)
                    "mcap_sort": mcap_sort_usd,        # フィルタ用数値 (USD統一)
                    "fcf_yield": fcf_yield,
                    "roe": roe,
                    "pe": info.get('trailingPE', 0),
                    "pbr": pbr,
                    "revenue_growth": revenue_growth,
                    "profit_margin": profit_margin
                })
                print(f"Fetched: {symbol}")
            else:
                print(f"Skipped {symbol}: No Market Cap")
                
            time.sleep(1.5) # API制限回避のため待機時間を確保
            
        except Exception as e:
            print(f"Error {symbol}: {e}")

    # ディレクトリが存在しない場合は作成
    os.makedirs("public", exist_ok=True)

    # 日米別々のリストに分割
    us_stocks = [s for s in data_list if s['country'] == 'US']
    jp_stocks = [s for s in data_list if s['country'] == 'JP']

    # JSON出力 (日米別ファイル)
    with open("public/us_stocks.json", "w", encoding='utf-8') as f:
        json.dump(us_stocks, f, indent=2, ensure_ascii=False)
    print(f"Saved {len(us_stocks)} US stocks to public/us_stocks.json")

    with open("public/jp_stocks.json", "w", encoding='utf-8') as f:
        json.dump(jp_stocks, f, indent=2, ensure_ascii=False)
    print(f"Saved {len(jp_stocks)} JP stocks to public/jp_stocks.json")

if __name__ == "__main__":
    main()
