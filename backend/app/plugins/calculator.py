from pydantic import BaseModel, Field
import math
from typing import Optional

def calculate_dismissal_notice_allowance(monthly_salary: int) -> dict:
    """해고예고수당을 계산합니다 (통상임금 30일분 이상). 
    단순화를 위해 월급을 기준으로 1일 통상임금을 근사치(월급/209 * 8)로 산정하여 30일분을 계산."""
    
    # 209시간 (보통 주 40시간 근로자의 월 소정근로시간 기준)
    hourly_wage = monthly_salary / 209
    daily_wage = hourly_wage * 8
    allowance = math.floor(daily_wage * 30)
    
    return {
        "calculator_name": "해고예고수당",
        "assumed_monthly_salary": monthly_salary,
        "estimated_allowance": allowance,
        "note": "이 계산은 주 40시간 근로자를 가정하여 '월급 ÷ 209시간 × 8시간 × 30일'로 단순화한 근사치입니다. 정확한 금액은 연장수당 등 고정수당 여부에 따라 달라집니다."
    }

def calculate_severance_pay(average_monthly_salary: int, worked_days: int) -> dict:
    """퇴직금을 계산합니다. (1일 평균임금 * 30일 * (근무일수 / 365))"""
    
    # 퇴직금은 평균임금을 기준으로 함 (최근 3개월 총 취득금액 / 그 기간의 총 일수)
    # 단순화를 위해 (월급 * 3) / 90일 정도로 가정.
    daily_average_wage = (average_monthly_salary * 3) / 90
    
    severance = math.floor(daily_average_wage * 30 * (worked_days / 365))
    
    return {
        "calculator_name": "퇴직금",
        "assumed_monthly_salary": average_monthly_salary,
        "worked_days": worked_days,
        "estimated_severance_pay": severance,
        "note": "이 계산은 평균임금(3개월 총액/총일수)을 단순 근사한 수치이며, 상여금 및 연차수당이 포함될 경우 실제 지급액은 더 높을 수 있습니다."
    }
