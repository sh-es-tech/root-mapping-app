import os
import json
import time
import io
import html
import requests
import streamlit as st
import streamlit.components.v1 as components
from dataclasses import dataclass, field
from typing import List, Dict, Optional

# ==========================================
# 1. データモデル定義
# ==========================================
@dataclass
class Experience:
    category: str
    title: str
    period: str
    skills_acquired: List[str] = field(default_factory=list)

@dataclass
class StrategicPoint:
    title: str
    focus_experience: str
    target_skills: List[str] = field(default_factory=list)

@dataclass
class HRSystem:
    education_system: str = ""

@dataclass
class CareerVision:
    short_term_goals: List[str] = field(default_factory=list)
    mid_long_goals: List[str] = field(default_factory=list)
    private_goals: List[str] = field(default_factory=list)
    ultimate_vision: str = "仕事もプライベートもあきらめない社会人！"

@dataclass
class StudentProfile:
    target_company: str = ""
    target_job: str = "営業職・総合職"
    experiences: List[Experience] = field(default_factory=list)
    es_points: List[StrategicPoint] = field(default_factory=list)
    hr_systems: HRSystem = field(default_factory=HRSystem)
    career_vision: CareerVision = field(default_factory=CareerVision)

# ==========================================
# 📄 面接対策 Q&A 用 直接PDF生成 (ReportLab)
# ==========================================
def build_qa_pdf(company_name: str, target_job: str, qa_results: list) -> Optional[bytes]:
    """面接対策Q&Aを直接PDFバイナリとして生成"""
    try:
        from reportlab.lib.pagesizes import A4
        from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer
        from reportlab.lib.styles import ParagraphStyle
        from reportlab.pdfbase import pdfmetrics
        from reportlab.pdfbase.cidfonts import UnicodeCIDFont
        from reportlab.lib import colors

        pdfmetrics.registerFont(UnicodeCIDFont('HeiseiKakuGo-W5'))
        
        buffer = io.BytesIO()
        doc = SimpleDocTemplate(
            buffer,
            pagesize=A4,
            rightMargin=36,
            leftMargin=36,
            topMargin=36,
            bottomMargin=36
        )
        
        title_style = ParagraphStyle(
            'DocTitle',
            fontName='HeiseiKakuGo-W5',
            fontSize=16,
            leading=22,
            textColor=colors.HexColor('#0D47A1'),
            spaceAfter=4
        )
        meta_style = ParagraphStyle(
            'DocMeta',
            fontName='HeiseiKakuGo-W5',
            fontSize=9.5,
            leading=14,
            textColor=colors.HexColor('#555555'),
            spaceAfter=14
        )
        theme_style = ParagraphStyle(
            'ThemeH2',
            fontName='HeiseiKakuGo-W5',
            fontSize=11.5,
            leading=16,
            textColor=colors.HexColor('#1565C0'),
            spaceBefore=8,
            spaceAfter=4
        )
        q_style = ParagraphStyle(
            'QStyle',
            fontName='HeiseiKakuGo-W5',
            fontSize=9.5,
            leading=14,
            textColor=colors.HexColor('#0D47A1'),
            spaceAfter=3
        )
        a_style = ParagraphStyle(
            'AStyle',
            fontName='HeiseiKakuGo-W5',
            fontSize=9,
            leading=13.5,
            textColor=colors.HexColor('#212121'),
            spaceAfter=4
        )
        advice_style = ParagraphStyle(
            'AdviceStyle',
            fontName='HeiseiKakuGo-W5',
            fontSize=8.5,
            leading=12.5,
            textColor=colors.HexColor('#1B5E20'),
            spaceAfter=10
        )

        story = []
        c_name = html.escape(company_name if company_name else "キャリア設計")
        t_job = html.escape(target_job if target_job else "営業職・総合職")
        
        story.append(Paragraph("【Root Mapping】AI面接対策 Q&Aシート", title_style))
        story.append(Paragraph(f"志望企業・業界: {c_name}  |  希望職種: {t_job}", meta_style))
        story.append(Spacer(1, 4))

        for qa in qa_results:
            theme = html.escape(qa.get('theme', ''))
            question = html.escape(qa.get('question', ''))
            answer = html.escape(qa.get('answer_script', '')).replace('\n', '<br/>')
            advice = html.escape(qa.get('advice', '')).replace('\n', '<br/>')

            story.append(Paragraph(f"📌 {theme}", theme_style))
            story.append(Paragraph(f"<b>🤖 質問:</b> 「{question}」", q_style))
            story.append(Paragraph(f"<b>🗣️ 回答案:</b><br/>{answer}", a_style))
            story.append(Paragraph(f"<b>💡 アドバイス:</b><br/>{advice}", advice_style))
            story.append(Spacer(1, 4))

        doc.build(story)
        buffer.seek(0)
        return buffer.getvalue()
    except Exception:
        return None

# ==========================================
# ⚙️ 爆速・自動最適化 API 通信処理
# ==========================================
def get_available_models(api_key: str) -> List[str]:
    try:
        url = f"https://generativelanguage.googleapis.com/v1beta/models?key={api_key}"
        res = requests.get(url, timeout=5)
        if res.status_code == 200:
            data = res.json()
            models = []
            for m in data.get("models", []):
                methods = m.get("supportedGenerationMethods", [])
                name = m.get("name", "").replace("models/", "")
                if "generateContent" in methods and not any(k in name for k in ["tts", "embedding", "bison", "imagen", "audio"]):
                    models.append(name)
            
            priority_order = [
                "gemini-flash-lite-latest",
                "gemini-1.5-flash",
                "gemini-flash-latest",
                "gemini-3.8-flash",
                "gemini-2.0-flash"
            ]
            
            sorted_models = []
            for p in priority_order:
                if p in models:
                    sorted_models.append(p)
            for m in models:
                if m not in sorted_models:
                    sorted_models.append(m)
                    
            if sorted_models:
                return sorted_models
    except Exception:
        pass
    
    return ["gemini-flash-lite-latest", "gemini-1.5-flash", "gemini-flash-latest", "gemini-3.8-flash"]

def generate_text_safe(api_key: str, prompt: str, task_name: str, status_box) -> str:
    models_to_try = get_available_models(api_key)
    last_error = ""

    for model_name in models_to_try:
        status_box.write(f"🤖 モデル [{model_name}] へ接続中...")
        max_retries = 3
        wait_time = 2
        
        url = f"https://generativelanguage.googleapis.com/v1beta/models/{model_name}:generateContent?key={api_key}"
        headers = {'Content-Type': 'application/json'}
        payload = {"contents": [{"parts": [{"text": prompt}]}]}
        
        for attempt in range(max_retries):
            try:
                if attempt > 0:
                    status_box.write(f"🔄 {task_name}: [{model_name}] 再接続中... ({attempt}/{max_retries-1}回目)")
                    
                response = requests.post(url, headers=headers, json=payload, timeout=35)
                
                if response.status_code == 200:
                    data = response.json()
                    try:
                        text = data['candidates'][0]['content']['parts'][0]['text']
                        status_box.write(f"✅ {task_name}: [{model_name}] で即座に生成成功！")
                        return text.strip()
                    except (KeyError, IndexError):
                        last_error = "レスポンス解析エラー"
                        status_box.write(f"⚠️ [{model_name}] レスポンス形式エラー。")
                        break
                        
                else:
                    error_msg = response.text
                    last_error = f"HTTP {response.status_code}: {error_msg}"
                    
                    if response.status_code in [503, 500]:
                        if attempt < max_retries - 1:
                            time.sleep(wait_time)
                            wait_time *= 2
                            continue
                        else:
                            status_box.write(f"⚠️ [{model_name}] 混雑のため次のモデルへ切り替えます。")
                            break
                    elif response.status_code == 429:
                        status_box.write(f"⚠️ [{model_name}] 利用制限超過のためスキップします。")
                        break
                    elif response.status_code in [404, 403, 400]:
                        status_box.write(f"⚠️ [{model_name}] HTTP {response.status_code} スキップ。")
                        break
                    else:
                        status_box.write(f"⚠️ [{model_name}] 通信エラー ({response.status_code})。")
                        break
                        
            except requests.exceptions.RequestException as e:
                last_error = f"ネットワークエラー: {str(e)}"
                if attempt < max_retries - 1:
                    time.sleep(wait_time)
                    wait_time *= 2
                    continue
                else:
                    status_box.write(f"⚠️ [{model_name}] タイムアウト。次へ。")
                    break

    raise Exception(f"すべてのAIモデルで通信に失敗しました。\n最後のエラー詳細: {last_error}")

# ==========================================
# 2. Gemini API 連携 (Mermaid図解 ＆ Q&A生成)
# ==========================================
def generate_interview_qa(api_key: str, profile: StudentProfile, status_box) -> List[Dict[str, str]]:
    exp_text = "\n".join([f"- {e.category} ({e.period}): {e.title} / 得た強み: {', '.join(e.skills_acquired)}" for e in profile.experiences])
    es_text = "\n".join([f"- ES軸: {es.title} / 関連経験: {es.focus_experience}" for es in profile.es_points])
    hr_text = f"活用したい社内制度: {profile.hr_systems.education_system}" if profile.hr_systems.education_system else "活用したい社内制度: 一般的な制度（異動制度、研修制度、キャリア開発・配置換えなど）"
    st_goals_str = ', '.join(profile.career_vision.short_term_goals)
    ml_goals_str = ', '.join(profile.career_vision.mid_long_goals)

    prompt_lines = [
        "あなたはプロのキャリアアドバイザーです。以下の学生のプロフィールをもとに、面接官がしそうな質問と、学生が答えるべき回答案、およびアドバイスを生成してください。",
        "必ず以下の8つのテーマ全てについて生成し、指定のJSON配列（[ { ... } ]）形式で出力してください。",
        "※AIの挨拶や補足説明は一切不要です。JSONデータのみを出力してください。",
        "",
        "【学生プロフィール】",
        f"志望企業・業界: {profile.target_company}",
        f"希望職種: {profile.target_job}",
        "経験・原体験:",
        exp_text,
        "アピールポイント(ES軸):",
        es_text,
        f"短期目標(1〜2年目): {st_goals_str}",
        f"中長期目標(5〜10年後): {ml_goals_str}",
        f"入社後の制度活用: {hr_text}",
        f"最終ビジョン: {profile.career_vision.ultimate_vision}",
        "",
        "【出力テーマ】",
        "1. 自己PR（強みと再現性）",
        "2. ガクチカ（課題解決力）",
        "3. 挫折・困難の経験",
        "4. 志望動機（マッチング度）",
        "5. 入社後の短期目標（1〜2年目）",
        "6. 中長期キャリア（5〜10年後）",
        "7. 最終ビジョン",
        "8. 逆質問・貢献意欲",
        "",
        "【出力JSONフォーマット】",
        "[",
        "  {",
        "    \"theme\": \"1. 自己PR（強みと再現性）\",",
        "    \"question\": \"面接官からの質問文\",",
        "    \"answer_script\": \"学生の経験を活かした具体的な回答スクリプト案（150字程度）\",",
        "    \"advice\": \"回答時のポイントやアドバイス（80字程度）\"",
        "  }",
        "]"
    ]
    prompt = "\n".join(prompt_lines)

    text = generate_text_safe(api_key, prompt, "Q&Aの生成", status_box)
    
    start_idx = text.find('[')
    end_idx = text.rfind(']')
    
    if start_idx != -1 and end_idx != -1:
        json_str = text[start_idx:end_idx+1]
        try:
            return json.loads(json_str)
        except json.JSONDecodeError as e:
            raise Exception(f"JSONの解析に失敗しました。\n詳細: {e}")
    else:
        raise Exception("AIの回答からJSONデータが見つかりませんでした。")

def generate_mermaid_by_ai(api_key: str, profile: StudentProfile, status_box) -> str:
    exp_text = "\n".join([f"- {e.title} / 得た強み: {', '.join(e.skills_acquired)}" for e in profile.experiences])
    es_text = "\n".join([f"- {es.title} / 関連経験: {es.focus_experience}" for es in profile.es_points])
    hr_text = profile.hr_systems.education_system if profile.hr_systems.education_system else "一般的な社内制度（異動制度、研修制度、配置換え）"
    st_goals = ', '.join(profile.career_vision.short_term_goals)
    ml_goals = ', '.join(profile.career_vision.mid_long_goals)
    vision = profile.career_vision.ultimate_vision
    
    prompt_lines = [
        "あなたはキャリア設計のプロであり、Mermaid記法（flowchart BT）を用いた図解の専門家です。",
        "学生のプロフィールを分析し、経験、強み、入社後の目標、最終ビジョンがどのように有機的に結びついているかを、因果関係を踏まえてMermaidのコードで出力してください。",
        "",
        "【学生プロフィール】",
        f"志望企業・職種: {profile.target_company} / {profile.target_job}",
        "■過去の経験（原体験）",
        exp_text,
        "■ESのメインテーマ",
        es_text,
        "■入社後のイメージと目標",
        f"1〜2年目の目標: {st_goals}",
        f"活用したい制度: {hr_text}",
        f"5〜10年後の目標: {ml_goals}",
        "■最終ビジョン",
        vision,
        "",
        "【Mermaid作成の厳格なルール】",
        "1. 冒頭に以下のクラス定義を必ず含めること：",
        "%%{init: {'flowchart': {'curve': 'basis'}}}%%",
        "flowchart BT",
        "    classDef level1 fill:#f9f9f9,stroke:#6c757d,stroke-width:1px,rx:15,ry:15;",
        "    classDef level2 fill:#e3f2fd,stroke:#1976d2,stroke-width:2px,rx:20,ry:20;",
        "    classDef level3 fill:#fff3e0,stroke:#f57c00,stroke-width:2px,rx:20,ry:20;",
        "    classDef level4 fill:#e8f5e9,stroke:#388e3c,stroke-width:2px,rx:25,ry:25;",
        "    classDef level5 fill:#f3e5f5,stroke:#8e24aa,stroke-width:3px,font-weight:bold,rx:30,ry:30;",
        "",
        "2. 各ノード定義時のクラス適用ルール（※必ず全ノードの文末に :::levelX をつけること！）",
        " - 「過去の経験」ノード: 末尾に :::level1 を付与（例: Exp1[\"塾講師\"]:::level1）",
        " - 「ESテーマ（ガクチカ・自己PR）」ノード: 末尾に :::level2 を付与（例: ES1[\"課題解決力\"]:::level2）",
        " - 「入社後1〜2年目の目標・制度」ノード: 末尾に :::level3 を付与（例: Goal1[\"業務習得\"]:::level3）",
        " - 「5〜10年後の目標」ノード: 末尾に :::level4 を付与（例: Goal2[\"リーダー挑戦\"]:::level4）",
        " - 「最終ビジョン」ノード: 末尾に :::level5 を付与（例: Vision1[\"理想の社会人\"]:::level5）",
        "",
        "3. きめ細やかな繋がり",
        " - 文脈を読み取り、論理的に繋がる要素間には積極的に矢印（-->）を引くこと。",
        " - 矢印には必ずラベル（テキスト）をつけること。",
        "",
        "4. 記述構文の注意",
        " - ノードのIDは半角英数字のみ（例: Exp1, Goal2）。",
        " - ノードのラベルはダブルクォーテーションで囲むこと。シングルクォーテーションは使用不可。",
        " - 改行は `<br/>` を使用。",
        "",
        "Mermaidのコード（純粋なテキスト）のみを出力してください。Markdownのコードブロック(```mermaid)は含めないでください。"
    ]
    prompt = "\n".join(prompt_lines)

    text = generate_text_safe(api_key, prompt, "図解の生成", status_box)
    
    if text.startswith("```mermaid"):
        text = text[10:]
    elif text.startswith("```"):
        text = text[3:]
        
    if text.endswith("```"):
        text = text[:-3]
        
    return text.strip()

# ==========================================
# 3. Streamlit UI構築
# ==========================================
def main():
    st.set_page_config(page_title="Root Mapping & AI Career Coach", layout="wide")

    logo_filename = None
    possible_logos = ["logo.jepeg", "logo.jpeg", "logo.jpg", "logo.png", "logo.JEPEG", "logo.JPEG", "logo.JPG", "logo.PNG"]
    for fn in possible_logos:
        if os.path.exists(fn):
            logo_filename = fn
            break

    if logo_filename:
        st.image(logo_filename, width=500)

    st.title("Root Mapping（ルート航図）作成ツール")
    st.caption("※「ルート航図」「Root Mapping」は登録商標（35類、41類、42類）出願中です。")

    st.markdown("---")

    st.subheader("🔑 アクセス認証")
    user_password = st.text_input("パスワードを入力してください", type="password", key="main_pass")

    if user_password != "hizume_lab":
        if user_password:
            st.error("❌ パスワードが違います")
        else:
            st.info("💡 ご利用には管理者から案内されたパスワードの入力が必要です。")
        st.stop()
    else:
        st.success("✅ 認証完了（ご利用いただけます）")

    st.markdown("---")

    # 🔒 安全対策済み APIキー制御処理（管理者キーをHTML上に一切描画させない）
    secrets_api_key = st.secrets.get("GEMINI_API_KEY", "") if hasattr(st, "secrets") else ""

    with st.sidebar:
        st.header("⚙️ API設定")
        user_api_key = st.text_input(
            "個人のGemini APIキー (任意)", 
            type="password", 
            placeholder="自分個人のキーを使う場合のみ入力"
        )
        st.info("💡 未入力の場合はシステム共有のAPIキーが自動適用されます。")

    # 入力があれば優先、なければ Secrets 内の管理者キーを使用
    api_key = user_api_key.strip() if user_api_key.strip() else secrets_api_key

    if "generated" not in st.session_state:
        st.session_state.generated = False
        st.session_state.mermaid_code = ""
        st.session_state.qa_results = []
        st.session_state.target_company = ""
        st.session_state.target_job = ""

    st.header("1. 基本情報・プロファイル入力")
    with st.form("profile_form"):
        target_company = st.text_input("志望企業名 / 志望業界", placeholder="例：株式会社イノベーション / IT・通信業界")
        target_job_input = st.text_input(
            "希望職種（※未入力の場合は「営業職・総合職」を前提として作成します）", 
            placeholder="例：システムエンジニア（SE）、企画営業職など"
        )
        
        st.subheader("2. 過去の経験（原体験）")
        exp_inputs = []
        for i in range(1, 6):
            with st.expander(f"経験 {i} " + ("（※入力推奨）" if i <= 3 else "（※任意）"), expanded=(i<=2)):
                t = st.text_input(f"経験{i}: タイトル", placeholder="例：個別指導塾でのアルバイト（リーダー）", key=f"exp_title_{i}")
                p = st.text_input(f"経験{i}: 期間", placeholder="例：大学1年から現在", key=f"exp_period_{i}")
                s = st.text_input(f"経験{i}: 身についた強み（カンマ区切り）", placeholder="例：傾聴力, 課題解決力", key=f"exp_skills_{i}")
                exp_inputs.append((t, p, s))
        
        st.subheader("3. ESのメインテーマ（ガクチカ・自己PR）")
        st.markdown("**【ガクチカ（学生時代に最も打ち込んだこと）】**")
        gaku_title = st.text_input("ガクチカのアピールポイント", placeholder="例：チームの課題を分析し、退会率を半減させた経験")
        gaku_focus = st.text_input("ベースとなる経験", placeholder="例：個別指導塾でのアルバイト")
        
        st.markdown("**【自己PR（あなたの最大の強み）】**")
        pr_title = st.text_input("自己PRのアピールポイント", placeholder="例：目標達成に向けた粘り強さと行動力")
        pr_focus = st.text_input("ベースとなる経験", placeholder="例：フットサルサークルでの合宿企画")
        
        st.subheader("4. 入社後のイメージ & 5. 人生全体のゴール")
        st_goal = st.text_input("入社1〜2年目の目標", placeholder="例：未経験の業務でも自律的に学び業務フローを習得する")
        hr_system_input = st.text_input(
            "活用したい社内制度（※未入力の場合は一般制度を前提とします）", 
            placeholder="例：若手向けの海外研修制度、ジョブローテーション制度など"
        )
        ml_goal = st.text_input("5〜10年後の目標", placeholder="例：現場で実績を積み、将来はリーダーに挑戦したい")
        vision_ultimate = st.text_input("最終ビジョン", placeholder="例：クライアントの成長を支え、週末はキャンプを楽しむ社会人")
        
        submit_btn = st.form_submit_button("AIにルート航図と面接対策を作らせる！")

    if submit_btn:
        clean_api_key = api_key.strip() if api_key else ""
        if not clean_api_key:
            st.error("⚠️ Gemini APIキーを入力するか、Secretsに登録してください。")
            return

        target_job = target_job_input.strip() if target_job_input.strip() else "営業職・総合職"

        if not hr_system_input.strip():
            st.warning("💡 **会社理解のアドバイス:** 「活用したい社内制度」が未入力のため、今回は一般的な「異動制度・研修制度・配置換え」を前提に組み立てています。")

        profile = StudentProfile(
            target_company=target_company, 
            target_job=target_job,
            hr_systems=HRSystem(education_system=hr_system_input.strip())
        )
        
        for t, p, s in exp_inputs:
            if t.strip():
                skills = [skill.strip() for skill in s.split(",")] if s else []
                profile.experiences.append(Experience(category="経験", title=t, period=p, skills_acquired=skills))
                
        if gaku_title:
            profile.es_points.append(StrategicPoint(title=f"ガクチカ: {gaku_title}", focus_experience=gaku_focus, target_skills=[gaku_title]))
        if pr_title:
            profile.es_points.append(StrategicPoint(title=f"自己PR: {pr_title}", focus_experience=pr_focus, target_skills=[pr_title]))
            
        profile.career_vision.short_term_goals = [st_goal] if st_goal else []
        profile.career_vision.mid_long_goals = [ml_goal] if ml_goal else []
        if vision_ultimate: profile.career_vision.ultimate_vision = vision_ultimate

        st.markdown("---")
        status_box = st.status("🚀 処理を開始します...", expanded=True)
        
        # --- ステップ1 実行 ---
        status_box.write("⚙️ ステップ 1/2: ルート航図（Mermaid図解）を設計中...")
        try:
            mermaid_res = generate_mermaid_by_ai(clean_api_key, profile, status_box)
        except Exception as e1:
            status_box.update(label="❌ ステップ1でエラーが発生しました", state="error", expanded=True)
            st.error(f"図解の生成に失敗しました。\n詳細: {e1}")
            st.stop()

        # --- ステップ2 実行 ---
        status_box.write("⚙️ ステップ 2/2: AI面接対策 8つのQ&Aを生成中...")
        try:
            qa_res = generate_interview_qa(clean_api_key, profile, status_box)
        except Exception as e2:
            status_box.update(label="❌ ステップ2でエラーが発生しました", state="error", expanded=True)
            st.error(f"Q&Aの生成に失敗しました。\n詳細: {e2}")
            st.stop()

        # --- 完了 ---
        status_box.update(label="✅ 生成完了！", state="complete", expanded=False)

        st.session_state.mermaid_code = mermaid_res
        st.session_state.qa_results = qa_res
        st.session_state.target_company = target_company.strip()
        st.session_state.target_job = target_job
        st.session_state.generated = True

    # ==========================================
    # 4. 生成結果の表示エリア（図解 ＆ Q&A）
    # ==========================================
    if st.session_state.generated:
        mermaid_code = st.session_state.mermaid_code
        qa_results = st.session_state.qa_results
        saved_company = st.session_state.target_company
        saved_job = st.session_state.target_job
        company_label = saved_company if saved_company else 'キャリア設計'

        st.success("🎉 あなた専用のオリジナル・ルート航図が完成しました！")
        st.info("💡 **アドバイス:** 出力されたルート航図（Root Mapping）を頭に入れて、想定外の質問にも一貫性をもって答えましょう！")
        
        if logo_filename:
            st.image(logo_filename, width=350)

        # ------------------------------------------
        # 🗺️ セクション1: ルート航図（Mermaid図解）
        # ------------------------------------------
        st.subheader("🗺️ ルート航図（Mermaid図解）")
        st.markdown("```mermaid\n" + mermaid_code + "\n```")

        # 📄 ワンクリックで画面のPDF保存を直接呼び出す埋め込みボタン
        components.html(
            """
            <button onclick="window.parent.print()" style="
                width: 100%;
                padding: 12px 24px;
                background-color: #1976D2;
                color: white;
                border: none;
                border-radius: 8px;
                font-weight: bold;
                cursor: pointer;
                font-size: 15px;
                box-shadow: 0 2px 5px rgba(0,0,0,0.15);
            ">📄 ワンクリックで画面（図解＆Q&A）をPDF保存する</button>
            """,
            height=50
        )

        st.markdown("---")

        # ------------------------------------------
        # 💡 セクション2: AI面接対策 Q&A
        # ------------------------------------------
        st.header("💡 AI面接対策 Q&A（8つの主要テーマ）")
        
        download_text = f"【Root Mapping キャリアシート】\n志望企業: {saved_company}\n希望職種: {saved_job}\n\n■ 面接対策Q&A\n"

        if isinstance(qa_results, list) and len(qa_results) > 0:
            for i, qa in enumerate(qa_results):
                theme = qa.get('theme', f'テーマ {i+1}')
                question = qa.get('question', '質問が生成されませんでした。')
                answer = qa.get('answer_script', '回答案が生成されませんでした。')
                advice = qa.get('advice', 'アドバイスが生成されませんでした。')

                st.subheader(f"📌 {theme}")
                st.markdown(f"**🤖 面接官:**\n「{question}」")
                st.markdown(f"**🗣️ 回答案:**\n{answer}")
                st.info(f"**💡 アドバイス:**\n{advice}")
                st.markdown("---")
                    
                download_text += f"\n--- {theme} ---\n質問: {question}\n回答: {answer}\nアドバイス: {advice}\n"
        else:
            st.error("面接対策データの読み込みに失敗しました。リトライしてください。")

        # 📄 面接対策Q&Aの直接PDFデータ作成 (ReportLab)
        qa_pdf_bytes = build_qa_pdf(saved_company, saved_job, qa_results)

        # ⬇️ 【全8つのQ&A出力完了の直下に配置】面接対策PDF ＆ テキスト保存ボタン
        col_qa_1, col_qa_2 = st.columns(2)
        with col_qa_1:
            if qa_pdf_bytes:
                st.download_button(
                    label="📄 「面接対策Q&Aのみ」をPDFで直接ダウンロード",
                    data=qa_pdf_bytes,
                    file_name=f"ルート航図_面接対策_{company_label}.pdf",
                    mime="application/pdf",
                    use_container_width=True
                )
            else:
                st.warning("💡 PDF保存を利用するには requirements.txt に `reportlab` を記載してください。")
        with col_qa_2:
            st.download_button(
                label="📥 面接対策Q&A（テキスト版）を保存する",
                data=download_text,
                file_name=f"ルート航図_面接対策_{company_label}.txt",
                mime="text/plain",
                use_container_width=True
            )

if __name__ == "__main__":
    main()