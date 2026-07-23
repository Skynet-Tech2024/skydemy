import os
import subprocess
from django.core.files import File
from django.core.files.temp import NamedTemporaryFile


def convert_docx_to_pdf(docx_path, pdf_path):
    """
    Convert a .docx file to .pdf using LibreOffice headless mode.
    Returns the path to the generated PDF file.
    """
    try:
        cmd = [
            'soffice',
            '--headless',
            '--convert-to',
            'pdf',
            '--outdir',
            os.path.dirname(pdf_path),
            docx_path
        ]
        subprocess.run(cmd, check=True, capture_output=True, text=True)
        expected_pdf = os.path.join(
            os.path.dirname(pdf_path),
            os.path.splitext(os.path.basename(docx_path))[0] + '.pdf'
        )
        if expected_pdf != pdf_path and os.path.exists(expected_pdf):
            os.rename(expected_pdf, pdf_path)
        return pdf_path
    except subprocess.CalledProcessError as e:
        raise Exception(f"LibreOffice conversion failed: {e.stderr}")


def convert_uploaded_file_to_pdf(uploaded_file):
    """
    Convert an uploaded .doc/.docx file to PDF and return the PDF file object.
    """
    original_name = uploaded_file.name
    ext = os.path.splitext(original_name)[1].lower()
    if ext not in ['.doc', '.docx']:
        raise ValueError("Unsupported file type. Only .doc and .docx are allowed.")

    with NamedTemporaryFile(suffix=ext, delete=False) as tmp_input:
        for chunk in uploaded_file.chunks():
            tmp_input.write(chunk)
        tmp_input.flush()
        tmp_input_path = tmp_input.name

    pdf_filename = os.path.splitext(original_name)[0] + '.pdf'
    with NamedTemporaryFile(suffix='.pdf', delete=False) as tmp_output:
        tmp_output_path = tmp_output.name

    try:
        convert_docx_to_pdf(tmp_input_path, tmp_output_path)
        pdf_file_obj = File(open(tmp_output_path, 'rb'), name=pdf_filename)
        return pdf_file_obj
    finally:
        if os.path.exists(tmp_input_path):
            os.remove(tmp_input_path)
        if os.path.exists(tmp_output_path):
            os.remove(tmp_output_path)