import logging
import os
import unicodedata
from datetime import date

logger = logging.getLogger(__name__)

_COMPLETED_STATUSES = {"done", "completed"}
_EMERGENCY_TERMS = (
    "khó thở", "khong tho duoc", "không thở được", "thở gấp",
    "co giật", "chảy máu nhiều", "chảy máu", "chay mau nhieu",
    "ngộ độc", "ngo doc", "bất tỉnh", "bat tinh", "cấp cứu", "cap cuu",
    "nôn nhiều", "nôn liên tục", "nôn nhiều lần", "non nhieu",
    "bỏ ăn", "bo an", "đau dữ dội", "đau đớn dữ dội", "dau du doi",
    "xấu đi nhanh", "tình trạng xấu đi nhanh", "tinh trang xau di nhanh",
    "difficulty breathing", "cannot breathe", "can't breathe", "not breathing",
    "seizure", "heavy bleeding", "bleeding heavily", "poisoning",
    "unconscious", "emergency", "repeated vomiting", "vomiting repeatedly",
    "not eating", "severe pain", "rapidly getting worse",
)

_DISCLAIMER = "Đây chỉ là thông tin tham khảo, không phải chẩn đoán y khoa và không thay thế bác sĩ thú y."


def _normalize_text(value):
    normalized=unicodedata.normalize("NFD",value.casefold())
    return "".join(
        character for character in normalized
        if unicodedata.category(character)!="Mn"
    ).replace("đ","d")


def _is_emergency(question):
    question_normalized=_normalize_text(question)
    return any(_normalize_text(term) in question_normalized for term in _EMERGENCY_TERMS)


def _generate(prompt):
    provider=os.getenv("AI_PROVIDER","mock").strip().lower()
    if provider!="gemini":
        if provider not in {"mock",""}:
            logger.warning("Unsupported AI_PROVIDER value; using local fallback")
        return None,"Fallback"

    key=os.getenv("GEMINI_API_KEY","").strip()
    if not key:
        logger.info("Gemini is configured but no API key is available; using local fallback")
        return None,"Fallback"

    try:
        from google import genai
        client=genai.Client(api_key=key)
        model=os.getenv("GEMINI_MODEL","gemini-2.5-flash")
        response=client.models.generate_content(model=model,contents=prompt)
        text=getattr(response,"text",None)
        if text and text.strip():
            return text.strip(),"AI"
        logger.warning("Gemini returned an empty response; using local fallback")
    except Exception as error:
        logger.warning("Gemini request failed; using local fallback (%s)",type(error).__name__)
    return None,"Fallback"


def _schedule_date(schedule):
    return schedule.scheduled_date.strftime("%d/%m/%Y")


def _schedule_groups(schedules):
    today=date.today()
    missed=[
        schedule for schedule in schedules
        if schedule.status.casefold()=="missed"
        or (
            schedule.scheduled_date<today
            and schedule.status.casefold() not in _COMPLETED_STATUSES
        )
    ]
    upcoming=[
        schedule for schedule in schedules
        if schedule.status.casefold()=="pending"
        and schedule.scheduled_date>=today
    ]
    return missed,upcoming


def _pet_description(pet):
    if pet is None:
        return "Chưa chọn thú cưng."
    breed=pet.breed.strip() if pet.breed else ""
    return f"{pet.name} ({pet.species}{', '+breed if breed else ''})"


def _fallback(question,pet,records,schedules):
    lines=[f"Thông tin thú cưng: {_pet_description(pet)}"]
    if pet and pet.weight is not None:
        lines.append(f"Cân nặng trong hồ sơ: {pet.weight} kg.")
    if not records:
        lines.append("Hồ sơ chăm sóc gần đây: Chưa có dữ liệu.")
    else:
        items=[
            f"{record.care_type} ngày {record.care_date.strftime('%d/%m/%Y')}"
            + (f" — {record.description.strip()}" if record.description and record.description.strip() else "")
            for record in records[-5:]
        ]
        lines.append("Hồ sơ chăm sóc gần đây: "+"; ".join(items)+".")

    missed,upcoming=_schedule_groups(schedules)
    if missed:
        lines.append("Lịch đã quá hạn/chưa hoàn thành: "+", ".join(
            f"{schedule.care_type} ngày {_schedule_date(schedule)}" for schedule in missed[:5]
        )+".")
    else:
        lines.append("Lịch đã quá hạn/chưa hoàn thành: Chưa có dữ liệu.")
    if upcoming:
        lines.append("Lịch sắp tới: "+", ".join(
            f"{schedule.care_type} ngày {_schedule_date(schedule)}" for schedule in upcoming[:5]
        )+".")
    else:
        lines.append("Lịch sắp tới: Chưa có dữ liệu.")

    question_lower=question.casefold()
    if any(term in question_lower for term in ("tiêm","vaccine","vắc")):
        lines.append("Việc tiêm phòng cần theo dõi theo hồ sơ và hướng dẫn của bác sĩ thú y; không tự ý đổi lịch.")
    elif any(term in question_lower for term in ("tắm","groom","cắt lông")):
        lines.append("Hãy trao đổi với cơ sở chăm sóc để chọn lịch vệ sinh phù hợp với thú cưng.")
    elif any(term in question_lower for term in ("ăn","thức ăn","dinh dưỡng")):
        lines.append("Nên hỏi bác sĩ thú y về khẩu phần phù hợp nếu thú cưng có bệnh nền hoặc biểu hiện bất thường.")
    else:
        lines.append("Tôi chỉ có thể hỗ trợ thông tin chăm sóc cơ bản dựa trên hồ sơ và lịch hiện có.")
    return " ".join(lines)


def _emergency_fallback(question,pet,records,schedules):
    profile=_fallback(question,pet,records,schedules)
    urgent_guidance=(
        "Vì bạn mô tả dấu hiệu nguy hiểm, không tự ý mua hoặc sử dụng thuốc cho thú cưng. "
        "Hãy liên hệ bác sĩ thú y hoặc đưa thú cưng đến cơ sở thú y sớm; nếu dấu hiệu nghiêm trọng "
        "hoặc đang diễn tiến, ưu tiên cơ sở thú y khẩn cấp ngay. Tôi không thể chẩn đoán tình trạng này."
    )
    return f"{profile}\n\n{urgent_guidance}\n\n{_DISCLAIMER}"


def ask_care_ai(question,pet,records,schedules):
    if _is_emergency(question):
        return _emergency_fallback(question,pet,records,schedules),"Fallback"

    prompt=f"""Bạn là trợ lý chăm sóc thú cưng. Trả lời bằng tiếng Việt, dựa trên đúng dữ liệu hồ sơ được cung cấp; không thêm dữ kiện hoặc suy đoán.
Không chẩn đoán, không khẳng định kết luận y khoa và không thay thế bác sĩ thú y. Với mọi câu hỏi về sức khỏe, nêu rõ đây chỉ là thông tin tham khảo và khuyến nghị hỏi bác sĩ thú y khi có triệu chứng, tình trạng kéo dài hoặc nặng lên. Với dấu hiệu cấp cứu, yêu cầu liên hệ cơ sở thú y ngay.

Dữ liệu thú cưng: {_pet_description(pet)}
Cân nặng: {pet.weight if pet and pet.weight is not None else 'Chưa có dữ liệu'}
Ghi chú y tế: {pet.medical_note if pet and pet.medical_note else 'Chưa có dữ liệu'}
Hồ sơ chăm sóc: {[(str(r.care_date),r.care_type,r.description) for r in records[-10:]] or 'Chưa có dữ liệu'}
Lịch chăm sóc: {[(str(s.scheduled_date),s.care_type,s.status,s.service.name if s.service else None) for s in schedules[:15]] or 'Chưa có dữ liệu'}
Câu hỏi: {question}

Trả lời ngắn gọn, phân biệt rõ dữ liệu hồ sơ với thông tin tham khảo."""
    answer,source=_generate(prompt)
    if not answer:
        answer=_fallback(question,pet,records,schedules)
    if _DISCLAIMER.casefold() not in answer.casefold():
        answer+="\n\n"+_DISCLAIMER
    return answer,source


def _age_description(birth_date):
    if birth_date is None:
        return "Chưa có dữ liệu"
    if birth_date>date.today():
        return f"Ngày sinh: {birth_date.strftime('%d/%m/%Y')}; chưa thể xác định tuổi từ ngày này."
    years=date.today().year-birth_date.year
    months=date.today().month-birth_date.month
    if date.today().day<birth_date.day:
        months-=1
    if months<0:
        years-=1
        months+=12
    age_parts=[]
    if years:
        age_parts.append(f"{years} tuổi")
    if months:
        age_parts.append(f"{months} tháng")
    age=", ".join(age_parts) if age_parts else "dưới 1 tháng"
    return f"{age} (ngày sinh: {birth_date.strftime('%d/%m/%Y')})"


def _summary_context(pet,records,schedules):
    missed,upcoming=_schedule_groups(schedules)
    return {
        "name":pet.name,
        "species":pet.species,
        "breed":pet.breed or None,
        "birth_date":str(pet.birth_date) if pet.birth_date else None,
        "weight":pet.weight,
        "medical_note":pet.medical_note or None,
        "care_records":[{
            "care_type":record.care_type,
            "date":str(record.care_date),
            "description":record.description or None,
            "provider":record.provider or None,
            "next_due_date":str(record.next_due_date) if record.next_due_date else None,
        } for record in records],
        "upcoming_schedules":[{
            "care_type":schedule.care_type,
            "date":str(schedule.scheduled_date),
            "status":schedule.status,
            "service":schedule.service.name if schedule.service else None,
        } for schedule in upcoming],
        "overdue_schedules":[{
            "care_type":schedule.care_type,
            "date":str(schedule.scheduled_date),
            "status":schedule.status,
            "service":schedule.service.name if schedule.service else None,
        } for schedule in missed],
    }


def _fallback_summary(pet,records,schedules):
    missed,upcoming=_schedule_groups(schedules)
    lines=[
        f"Tên thú cưng: {pet.name or 'Chưa có dữ liệu'}",
        f"Loài: {pet.species or 'Chưa có dữ liệu'}",
        f"Giống: {pet.breed.strip() if pet.breed and pet.breed.strip() else 'Chưa có dữ liệu'}",
        f"Tuổi/ngày sinh: {_age_description(pet.birth_date)}",
        f"Cân nặng: {str(pet.weight)+' kg' if pet.weight is not None else 'Chưa có dữ liệu'}",
        f"Ghi chú y tế: {pet.medical_note.strip() if pet.medical_note and pet.medical_note.strip() else 'Chưa có dữ liệu'}",
    ]
    if records:
        lines.append("Hồ sơ chăm sóc đã thực hiện:")
        lines.extend(
            f"- {record.care_date.strftime('%d/%m/%Y')} — {record.care_type}"
            + (f": {record.description.strip()}" if record.description and record.description.strip() else "")
            + (f" (Đơn vị/người thực hiện: {record.provider.strip()})" if record.provider and record.provider.strip() else "")
            for record in records
        )
    else:
        lines.append("Hồ sơ chăm sóc đã thực hiện: Chưa có dữ liệu")
    if upcoming:
        lines.append("Lịch chăm sóc sắp tới:")
        lines.extend(
            f"- {schedule.scheduled_date.strftime('%d/%m/%Y')} — "
            f"{schedule.service.name if schedule.service else schedule.care_type}"
            for schedule in upcoming
        )
    else:
        lines.append("Lịch chăm sóc sắp tới: Chưa có dữ liệu")
    if missed:
        lines.append("Lịch chăm sóc đã quá hạn:")
        lines.extend(
            f"- {schedule.scheduled_date.strftime('%d/%m/%Y')} — "
            f"{schedule.service.name if schedule.service else schedule.care_type}"
            for schedule in missed
        )
    else:
        lines.append("Lịch chăm sóc đã quá hạn: Chưa có dữ liệu")
    lines.append("Cảnh báo: Đây là bản tóm tắt hỗ trợ quản lý, không phải chẩn đoán y khoa.")
    return "\n".join(lines)


def summarize_pet(pet,records,schedules):
    context=_summary_context(pet,records,schedules)
    prompt=f"""Tạo bản tóm tắt hồ sơ thú cưng bằng tiếng Việt, có các mục: tên; loài/giống; tuổi hoặc ngày sinh; cân nặng; ghi chú y tế; hồ sơ chăm sóc đã thực hiện; lịch sắp tới; lịch quá hạn.
Chỉ sử dụng dữ liệu JSON bên dưới. Không suy luận hoặc bịa thông tin. Với trường hoặc danh sách rỗng/null, ghi đúng "Chưa có dữ liệu". Cuối bản tóm tắt phải ghi: "Đây là bản tóm tắt hỗ trợ quản lý, không phải chẩn đoán y khoa."

Dữ liệu hồ sơ:
{context}"""
    summary,source=_generate(prompt)
    if not summary:
        summary=_fallback_summary(pet,records,schedules)
    elif "không phải chẩn đoán y khoa" not in summary.casefold():
        summary+="\n\nĐây là bản tóm tắt hỗ trợ quản lý, không phải chẩn đoán y khoa."
    return summary,source


def _fallback_reminder(schedule,pet):
    service_name=schedule.service.name if schedule.service else None
    care=service_name or schedule.care_type
    pet_name=pet.name or "thú cưng"
    return (
        f"Nhắc lịch chăm sóc cho {pet_name}: lịch {care} vào ngày "
        f"{schedule.scheduled_date.strftime('%d/%m/%Y')}."
        " Bạn có thể chuẩn bị hồ sơ chăm sóc liên quan trước khi đến."
        " Nếu cần thay đổi lịch, vui lòng liên hệ cơ sở thú y/chăm sóc đã đặt lịch."
    )


def create_reminder_message(schedule,pet):
    service_name=schedule.service.name if schedule.service else None
    care=service_name or schedule.care_type
    prompt=f"""Soạn một tin nhắn nhắc lịch ngắn gọn, thân thiện bằng tiếng Việt.
Chỉ sử dụng dữ liệu dưới đây; không tự thêm giờ hẹn, địa chỉ, tên cơ sở hoặc yêu cầu chuẩn bị chuyên môn không có trong dữ liệu.
Tin nhắn phải nêu tên thú cưng, loại chăm sóc/dịch vụ, ngày lịch; gợi ý chuẩn bị hồ sơ chăm sóc liên quan; và nhắc liên hệ cơ sở đã đặt lịch nếu cần đổi lịch.
Tên thú cưng: {pet.name}
Loại chăm sóc trong lịch: {schedule.care_type}
Dịch vụ: {service_name or 'Không có dịch vụ liên kết'}
Ngày lịch: {schedule.scheduled_date.strftime('%d/%m/%Y')}
Ghi chú lịch: {schedule.notes or 'Chưa có dữ liệu'}"""
    message,source=_generate(prompt)
    if not message:
        message=_fallback_reminder(schedule,pet)
    return message,source
