import os
import json
import re
import time
import streamlit as st
from google import genai
from dataclasses import dataclass, field
from typing import List, Dict

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
# ⚙️ 完全自動：利用可能モデルの自動判定＆取得
# ==========================================
def get_available_models(client: genai.Client) -> List[str]:
    try:
        models = client.models.list()
        valid_models = []
        for m in models:
            name = m.name.replace("models/", "")
            if "flash" in name and "embedding" not in name and "imagen" not in name and "tts" not in name:
                valid_models.append(name)
        
        valid_models.sort(reverse=True)
        if valid_models:
            return valid_models
    except Exception:
        pass
    
    return ["gemini-2.5-flash", "gemini-2.0-flash"]

def generate_text_with_auto_model(client: genai.Client, prompt: str) -> str:
    candidate_models = get_available_models(client)
    last_exception = None

    for model_name in candidate_models:
        try:
            response = client.models.generate_content(
                model=model_name,
                contents=prompt
            )
            if response and response.text:
                return response.text.strip()
        except Exception as e:
            last_exception = e
            time.sleep(1)
            continue
            
    raise Exception(f"すべての自動試行モデルでの生成に失敗しました: {last_exception}")

# ==========================================
# 2. Gemini API 連携 (Mermaid図解 ＆ Q&A生成)
# ==========================================
def generate_interview_qa(api_key: str, profile: StudentProfile) -> List[Dict[str, str]]:
    client = genai.Client(api_key=api_key)
    
    exp_text = "\n".join([f"- {e.category} ({e.period}): {e.title} / 得た強み: {', '.join(e.skills_acquired)}" for e in profile.experiences])
    es_text = "\n".join([f"- ES軸: {es.title} / 関連経験: {es.focus_experience}" for es in profile.es_points])
    hr_text = f"活用したい社内制度: {profile.hr_systems.education_system}" if profile.hr_systems.education_system else "活用したい社内制度: 一般的な制度（異動制度、研修制度、キャリア開発・配置換えなど）"
    st_goals_str = ', '.join(profile.career_vision.short_term_goals)
    ml_goals_str = ', '.join(profile.career_vision.mid_long_goals)

    prompt_lines = [
        "あなたはプロのキャリアアドバイザーです。以下の学生のプロフィールをもとに、面接官がしそうな質問と、学生が答えるべき回答案、およびアドバイスを生成してください。",
        "必ず以下の8つのテーマ全てについて生成し、指定のJSON形式で出力してください。Markdownのコードブロック(```json ... ```)で囲まないで、純粋なJSON配列のみを出力してください。",
        "",
        "【学生プロフィール】",