import re
import time
import streamlit as st
from google import genai

# アプリのタイトル
st.title("Amazon商品比較 & サクラチェッカー AI")

st.write("AmazonのURLを複数入力（1行に1つ）して、商品の要約と一覧比較を行います。")

# APIキーを secrets.toml から自動取得
api_key = st.secrets.get("GEMINI_API_KEY")

with st.sidebar:
    st.header("設定")
    if not api_key:
        api_key = st.text_input("Gemini API Key", type="password")
    else:
        st.success("APIキーは自動読み込みされました")
    st.markdown("[👉 APIキーの取得はこちら (Google AI Studio)](https://aistudio.google.com/)")

# メイン画面の入力フォーム
urls_input = st.text_area("AmazonのURLを入力してください（複数ある場合は改行）", "", height=150)

if urls_input:
    url_list = [u.strip() for u in urls_input.split("\n") if u.strip()]
    asins = []

    st.subheader("🔗 サクラチェッカー確認")
    for idx, url in enumerate(url_list, 1):
        asin_match = re.search(r'/(?:dp|gp/product)/([A-Z0-9]{10})', url)
        if asin_match:
            asin = asin_match.group(1)
            asins.append(asin)
            sakura_url = f"https://sakura-checker.jp/search/{asin}/"
            st.markdown(f"**商品 {idx} (ASIN: {asin})**: [👉 サクラチェッカーで確認]({sakura_url})")
        else:
            st.error(f"商品 {idx}: 有効なAmazon URLが見つかりませんでした。")

if st.button("🤖 Geminiで商品を要約・比較する"):
        if not api_key:
            st.error("APIキーが設定されていません。")
            st.stop()

        # 試すモデルのリスト（混雑時は次のモデルに自動切替）
        models_to_try = ["gemini-3.8-flash", "gemini-2.5-pro"]
        response = None
        used_model = ""

        with st.spinner("AIが商品を比較分析中...（混雑時は自動で別モデルに切り替えます）"):
            client = genai.Client(api_key=api_key)
            prompt = f"""
以下のAmazon商品URLリストの製品について概要を収集・要約し、分かりやすく比較分析してください。

対象URLリスト:
{chr(10).join(url_list)}

出力フォーマット:
1. **各商品の概要と特徴**（箇条書き）
2. **比較表**（主な特徴、メリット、注意点を表形式で整理）
3. **こんな人におすすめ**（商品ごとのターゲット像）
"""
            for target_model in models_to_try:
                # 各モデルで最大2回までリトライ
                for attempt in range(2):
                    try:
                        response = client.models.generate_content(
                            model=target_model,
                            contents=prompt
                        )
                        used_model = target_model
                        break  # 成功したらループ脱出
                    except Exception as e:
                        if "503" in str(e) or "UNAVAILABLE" in str(e):
                            time.sleep(3)  # 混雑の場合は少し待って再試行
                        else:
                            # 503以外のエラー（404等）は即次のモデルへ
                            break
                
                if response:
                    break  # 成功していればモデル切替ループも脱出

        if response:
            st.subheader("💡 AI比較・分析結果")
            st.caption(f"使用モデル: {used_model}")
            st.markdown(response.text)
        else:
            st.error("サーバーが大変混雑しているため、時間をおいて再度お試しください。")
