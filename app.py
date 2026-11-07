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

        for qa