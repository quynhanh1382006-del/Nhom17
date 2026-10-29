import os
from datetime import date

def _fallback(question, pet, records, schedules):
    q=question.lower()
    lines=[]
    if pet:
        lines.append(f"Hồ sơ: {pet.name} ({pet.species}, {pet.breed or 'chưa cập nhật giống'}).")
    missed=[s for s in schedules if s.status=="missed"]
    upcoming=[s for s in schedules if s.status=="pending" and s.scheduled_date>=date.today()]
    if missed:
        lines.append("Cảnh báo: hệ thống phát hiện lịch chăm sóc đã bỏ sót: " + ", ".join(f"{s.care_type} ngày {s.scheduled_date.strftime('%d/%m/%Y')}" for s in missed[:3]) + ".")
    if any(x in q for x in ["tiêm", "vaccine", "vắc", "vắc-xin"]):
        lines.append("Lịch tiêm nên được theo dõi theo hồ sơ và hướng dẫn của bác sĩ thú y; không tự ý bỏ hoặc đổi lịch tiêm.")
    elif any(x in q for x in ["tắm", "groom", "cắt lông"]):
        lines.append("Lịch vệ sinh/grooming nên điều chỉnh theo giống, độ dài lông, da và môi trường sống của thú cưng.")
    elif any(x in q for x in ["ăn", "thức ăn", "dinh dưỡng"]):
        lines.append("Nên chọn khẩu phần phù hợp tuổi, cân nặng, tình trạng sức khỏe và giống; nếu có bệnh nền hãy hỏi bác sĩ thú y.")
    elif any(x in q for x in ["bệnh", "nôn", "tiêu chảy", "sốt", "đau"]):
        lines.append("Đây là thông tin tham khảo, không thay thế chẩn đoán. Nếu triệu chứng kéo dài, nặng lên hoặc thú cưng có dấu hiệu bất thường, nên liên hệ bác sĩ thú y.")
    else:
        lines.append("Tôi có thể hỗ trợ tra cứu lịch chăm sóc, tóm tắt hồ sơ và trả lời các câu hỏi chăm sóc cơ bản.")
    if upcoming:
        lines.append("Lịch sắp tới: " + ", ".join(f"{s.care_type} ngày {s.scheduled_date.strftime('%d/%m/%Y')}" for s in upcoming[:3]) + ".")
    return " ".join(lines)

def _gemini(prompt):
    key=os.getenv("GEMINI_API_KEY","").strip()
    if not key: return None
    try:
        from google import genai
        client=genai.Client(api_key=key)
        model=os.getenv("GEMINI_MODEL","gemini-2.5-flash")
        resp=client.models.generate_content(model=model, contents=prompt)
        return getattr(resp,"text",None) or None
    except Exception:
        return None

def ask_care_ai(question, pet, records, schedules):
    prompt=f"""Bạn là trợ lý chăm sóc thú cưng cho hệ thống quản lý thú cưng. Trả lời bằng tiếng Việt, ngắn gọn, dễ hiểu. Không chẩn đoán bệnh và không thay thế bác sĩ thú y. Nếu câu hỏi có dấu hiệu nguy hiểm, hãy khuyên người dùng liên hệ bác sĩ thú y.

Hồ sơ thú cưng: tên={pet.name if pet else 'chưa chọn'}, loài={pet.species if pet else ''}, giống={pet.breed if pet else ''}, cân nặng={pet.weight if pet else ''}.
Lịch sử chăm sóc gần đây: {[(r.care_type, str(r.care_date), r.description) for r in records[-8:]]}
Lịch chăm sóc: {[(s.care_type, str(s.scheduled_date), s.status) for s in schedules[:10]]}
Câu hỏi: {question}

Hãy ưu tiên dữ liệu hồ sơ trên, nêu cảnh báo lịch bỏ sót nếu có và chỉ đưa khuyến nghị chăm sóc cơ bản."""
    ai=_gemini(prompt)
    return (ai or _fallback(question,pet,records,schedules)), ("AI" if ai else "Fallback")
