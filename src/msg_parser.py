import os
import re
import copy
import email
import logging
import subprocess
import pyocr
import pyocr.builders
import requests
from PIL import Image, ImageFilter
from pdfrw import PdfReader
from tika import parser
import tensorflow
import params

def parse(file_name, model):
    try:
        with open(file_name, encoding = "utf-8", errors = "surrogateescape") as f:
            msg = email.message_from_file(f)
    except FileNotFoundError:
        return 1
    content_list = search_body_content(msg)
    str_content = '\n'.join(content_list)
    logging.basicConfig(format = "%(asctime)s - %(message)s", filemode = 'a', level = logging.DEBUG)
    score = match_score(str_content, model)
    logging.info("Score: %f", score)
    if score >= params.MODEL_THRESHOLD:
        requests.post("http://" + params.FLASK_HOST + ":5000", data = { "data": str_content })
        return 1
    return 0

def tika_content(string, file_name, server_endpoint = "http://" + params.TIKA_HOST + ":9998"):
    def convert_to_pdf(file_path):
        if not os.path.isfile(file_path):
            return None
        try:
            libre_exec = subprocess.check_output(["which", "libreoffice"])
            libre_exec = libre_exec.rstrip().decode()
            subprocess.call([libre_exec, "--headless", "--convert-to", "pdf", file_path, "--outdir", "/tmp"])
            pdf_file = os.path.splitext(file_path)[0] + ".pdf"
            if os.path.isfile(pdf_file):
                return True
            return None
        except:
            return None
    def is_office_file(file_path):
        ext = os.path.splitext(file_path)[1]
        return any(ext in _ext for _ext in [".xlsx", ".docx", ".pptx", ".ppsx"])

    file_name = clean_str(file_name)
    try:
        parsed = parser.from_buffer(string, server_endpoint)
    except:
        return None
    if not isinstance(parsed, dict):
        return None
    if isinstance(parsed, dict) and len(parsed) == 0 and is_office_file(file_name):
        attachment = "/tmp/" + file_name
        with open(attachment, "wb") as f:
            f.write(string)
        res = convert_to_pdf(attachment)
        if res is None:
            return None
        attachment_pdf = os.path.splitext(attachment)[0] + ".pdf"
        if res:
            parsed = parser.from_file(attachment_pdf, server_endpoint)
            return parsed["content"]
        return None
    if isinstance(parsed, dict) and len(parsed) == 0:
        return None
    return (parsed["content"], parsed["metadata"]["Content-Type"])

def clean_str(mystr, str_rep = '', remove_non_unicode = False):
    if isinstance(mystr, str) or mystr is not None:
        if remove_non_unicode:
            return re.sub(r"\W+", str_rep, mystr)
        return re.sub(r"[^A-Za-z0-9._]+", '', mystr)
    return mystr

def get_pdf_rotation(file_path):
    if not os.path.exists(file_path):
        return None
    if os.path.splitext(file_path)[1] != ".pdf":
        return None
    reader = PdfReader(file_path)
    pg_rotation = 0
    for pg in reader.pages:
        if pg.Rotate != 0 or pg.Rotate != '':
            pg_rotation = pg.Rotate
            break
    if pg_rotation is None:
        return 0
    return int(pg_rotation)

def extract_image_pdf(file_path):
    if not os.path.exists("/usr/bin/pdfimages"):
        return None
    pdf_name = clean_str(file_path.rsplit('/', 1)[-1].split('.')[0])
    img_root = params.IMG_PATH + "/_img_" + pdf_name
    pdf_rotation = get_pdf_rotation(file_path)
    img_rotation = 0
    if isinstance(pdf_rotation, int) and pdf_rotation != 0:
        img_rotation = pdf_rotation - 180
    ret = subprocess.call(["/usr/bin/pdfimages", "-j", file_path, img_root])
    if ret == 0:
        files = [os.path.join(params.IMG_PATH, f) for f in os.listdir(params.IMG_PATH) if "_img_" + pdf_name in f]
        pbm_files = [p for p in files if ".pbm" in p]
        if len(pbm_files) > 0:
            for img_path in pbm_files:
                with Image.open(img_path) as im:
                    new_file = os.path.splitext(img_path)[0] + ".jpg"
                    im.save(new_file)
            files2 = [x.replace(".pbm", ".jpg") if ".pbm" in x else x for x in files]
            files = list(set(files2))
        if img_rotation != 0:
            for img_path in files:
                if os.path.exists(img_path):
                    with Image.open(img_path) as im:
                        im.rotate(img_rotation).save(img_path)
        return files
    return None

def ocr_content(files, lang):
    if files is None or len(files) == 0:
        return None
    tools = pyocr.get_available_tools()
    if len(tools) == 0:
        return None
    tool = tools[0]
    langs = tool.get_available_languages()
    if lang not in langs:
        return None
    content_list = []
    for img_file in files:
        try:
            with Image.open(img_file) as ifds:
                ifds.filter(ImageFilter.SHARPEN)
        except FileNotFoundError:
            continue
        txt = tool.image_to_string(ifds, lang = lang, builder = pyocr.builders.TextBuilder())
        content_list.append(txt)
    return '\n'.join(content_list)

def remove_blank_lines(str_content):
    if isinstance(str_content, str) and str_content is not None:
        return os.linesep.join([s for s in str_content.splitlines() if s])
    return ''

def get_attachment_content(part):
    sub_type = part.get_content_subtype()
    file_name = part.get_filename()
    if sub_type in ("octet-stream", "pdf") or "officedocument" in sub_type or "msword" in sub_type or "excel" in sub_type or "opendocument" in sub_type:
        str_attachment = part.get_payload(decode = True)
        content_attachment_tuple = tika_content(str_attachment, file_name)
        if content_attachment_tuple is None:
            return None
        t1 = remove_blank_lines(content_attachment_tuple[0])
        t2 = content_attachment_tuple[1]
        return (t1, t2)
    return None

def search_body_content(msg, clist = None):
    def find_parent(lst, part_tuple):
        if len(lst) == 0:
            return False
        if lst[-1] == part_tuple:
            return True
        lst_copy = copy.copy(lst)
        lst_copy.pop()
        return find_parent(lst_copy, part_tuple)
    if clist is None:
        clist = []
    if msg.is_multipart():
        walked_parts_stack = []
        for part in msg.walk():
            part_type = (part.get_content_maintype(), part.get_content_subtype())
            walked_parts_stack.append(part_type)
            if part_type[0] == "text" and part_type[1] == "html":
                if find_parent(walked_parts_stack, ("multipart", "alternative")):
                    continue
            if part.get_content_maintype() == "text":
                if part.get("Content-Transfer-Encoding") == "base64":
                    if part.get_content_maintype() == "text":
                        clist.append(part.get_payload(decode = True). decode("utf-8", errors = "surrogateescape"))
                    else:
                        attachment_content = get_attachment_content(part)[0]
                        clist.append(attachment_content)
                else:
                    try:
                        clist.append(part.get_payload(decode = True). decode("utf-8", errors = "surrogateescape"))
                    except UnicodeDecodeError:
                        clist.append(part.get_payload(decode = True). decode("utf-8", errors = "replace"))
                    except UnicodeEncodeError:
                        pass
            elif part.get_content_maintype() == "application":
                attachment_content_tuple = get_attachment_content(part)
                if attachment_content_tuple is not None:
                    attachment_content = attachment_content_tuple[0]
                    attachment_content_type = attachment_content_tuple[1]
                else:
                    attachment_content = ''
                    attachment_content_type = ''
                if attachment_content_type == "application/pdf" and attachment_content == '':
                    filename = part.get_filename()
                    str_attachment = part.get_payload(decode = True)
                    pdf_file_path = "/tmp/" + clean_str(filename)
                    with open(pdf_file_path, "wb") as f:
                        f.write(str_attachment)
                    img_files = extract_image_pdf(pdf_file_path)
                    attachment_content = ocr_content(img_files, params.OCR_LANG)
                    attachment_content = remove_blank_lines(attachment_content)
                if attachment_content is not None:
                    clist.append(attachment_content)
    else:
        try:
            if msg.get_content_type() != "text/calendar":
                clist.append(msg.get_payload(decode = True).decode("utf-8", errors = "surrogateescape"))
        except UnicodeEncodeError:
            pass
    return clist

def match_score(content, model):
    return model.predict(tensorflow.expand_dims(content, axis = 0))
