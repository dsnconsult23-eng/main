# services/pdf_service.py
from typing import Optional            # ✅ for Optional[...] syntax
from SendMailAgent import gen_pdf       # make sure this import path is correct

months = [
    "Јануари", "Февруари", "Март", "Април",
    "Мај", "Јуни", "Јули", "Август",
    "Септември", "Октомври", "Ноември", "Декември"
]

def GenerirajPdf(
    mesec: str,
    godina: int,
    par_teamid: Optional[int] = None,
    par_regionuid: Optional[int] = None,
    par_agentid: Optional[int] = None,
    result_label=None
):
    """
    Generates the PDF and optionally updates a Tkinter label.
    In API context `result_label` is None and will be ignored.
    """
    month_number = int(mesec) 
    #month_number = months.index(mesec) + 1
    print("Month number:", month_number)

    OK, rez = gen_pdf(
        month_number,
        godina,
        par_teamid,
        par_regionuid,
        par_agentid
    )

    # If called from desktop GUI, update label text
    if result_label is not None:
        if not OK:
            result_label.config(text=f"Грешка при пребарување број 1: {rez}", fg="red")
        else:
            result_label.config(text=f"Операцијата е успешна! Резултат: {rez}", fg="green")

    return OK, rez
