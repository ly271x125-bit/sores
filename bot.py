import asyncio
import pytz
import time
import os
import uuid
import random
from datetime import datetime, timedelta
import re
from yt_dlp import YoutubeDL
import platform
import telethon
import sys
from deep_translator import GoogleTranslator

from telethon import TelegramClient, events, Button
from telethon.sessions import StringSession
from telethon.errors import FloodWaitError
from telethon.tl.functions.account import UpdateProfileRequest, UpdateUsernameRequest
from telethon.tl.types import PeerUser, PeerChat, PeerChannel, MessageEntityMentionName, InputMessageEntityMentionName, ChatBannedRights, MessageActionChatAddUser, MessageActionChatJoinedByLink, MessageActionChannelCreate, MessageActionChatDeleteUser, MessageActionChatEditTitle, MessageActionChatEditPhoto, MessageActionChatDeletePhoto, MessageActionPinMessage
from telethon.tl.functions.messages import SendMessageRequest
from telethon.tl.functions.channels import LeaveChannelRequest, DeleteChannelRequest, EditBannedRequest
from telethon.tl.functions.messages import DeleteChatUserRequest, DeleteHistoryRequest
from telethon.tl.functions.messages import SetTypingRequest
from telethon.tl.types import SendMessageTypingAction, SendMessageRecordVideoAction, SendMessageRecordAudioAction, SendMessageUploadVideoAction, SendMessageUploadAudioAction, SendMessageUploadPhotoAction, SendMessageUploadDocumentAction
from telethon.tl.functions.photos import UploadProfilePhotoRequest, DeletePhotosRequest, GetUserPhotosRequest
from telethon.tl.functions.users import GetFullUserRequest
from telethon.tl.functions import PingRequest

API_ID = 37979088
API_HASH = "125e4f6e134fe787ff7ae30688092b3b"
BOT_TOKEN = "8701627334:AAEOGp34HAJ5ev9Kj8mzjCxmnBd_lTRDZtw"
OWNER_ID = 869343078
bot = TelegramClient("manager", API_ID, API_HASH).start(bot_token=BOT_TOKEN)

allowed_users = set()
banned_users = set()
waiting_sessions = {}
all_clients = []
user_clients = {}
waiting_user_add = set()
waiting_user_ban = set()
waiting_user_unban = set()

pending_requests = {}
request_notified = {}

source_enabled = {}
waiting_phone = {}
waiting_code = {}
waiting_2fa = {}
phone_clients = {}

START_TIME = datetime.now(pytz.UTC)

time_styles = {
    "1": "𝟎𝟏𝟐𝟑𝟒𝟓𝟔𝟕𝟖𝟗",
    "2": "𝟶𝟷𝟸𝟹𝟺𝟻𝟼𝟽𝟾𝟿",
    "3": "𝟢𝟣𝟤𝟥𝟦𝟧𝟨𝟩𝟪𝟫",
    "4": "𝟬𝟭𝟮𝟯𝟰𝟱𝟲𝟳𝟴𝟵",
    "5": "0123456789",
    "6": "۰۱۲۳۴۵۶۷۸۹",
    "7": "٠١٢٣٤٥٦٧٨٩",
    "8": "₀₁₂₃₄₅₆₇₈₉",
    "9": "⓪①②③④⑤⑥⑦⑧⑨",
    "10": "⁰¹²³⁴⁵⁶⁷⁸⁹",
    "11": "𝟘𝟙𝟚𝟛𝟜𝟝𝟞𝟟𝟠𝟡",
    "12": "⓿❶❷❸❹❺❻❼❽❾"
}

user_copy_data = {}

def apply_fancy_time_style(time_str, style_num):
    style = time_styles.get(str(style_num), time_styles["1"])
    result = []
    for char in time_str:
        if char.isdigit():
            idx = int(char)
            if idx < len(style):
                result.append(style[idx])
            else:
                result.append(char)
        else:
            result.append(char)
    return ''.join(result)

country_timezones = {
    # الدول العربية
    "مصر": "Africa/Cairo",
    "السعودية": "Asia/Riyadh",
    "الامارات": "Asia/Dubai",
    "الكويت": "Asia/Kuwait",
    "قطر": "Asia/Qatar",
    "البحرين": "Asia/Bahrain",
    "عمان": "Asia/Muscat",
    "الاردن": "Asia/Amman",
    "فلسطين": "Asia/Gaza",
    "لبنان": "Asia/Beirut",
    "سوريا": "Asia/Damascus",
    "العراق": "Asia/Baghdad",
    "ليبيا": "Africa/Tripoli",
    "تونس": "Africa/Tunis",
    "الجزائر": "Africa/Algiers",
    "المغرب": "Africa/Casablanca",
    "موريتانيا": "Africa/Nouakchott",
    "السودان": "Africa/Khartoum",
    "الصومال": "Africa/Mogadishu",
    "جيبوتي": "Africa/Djibouti",
    "جزر القمر": "Indian/Comoro",
    "اليمن": "Asia/Aden",
    # آسيا
    "تركيا": "Europe/Istanbul",
    "ايران": "Asia/Tehran",
    "افغانستان": "Asia/Kabul",
    "باكستان": "Asia/Karachi",
    "الهند": "Asia/Kolkata",
    "الصين": "Asia/Shanghai",
    "اليابان": "Asia/Tokyo",
    "كوريا": "Asia/Seoul",
    "كوريا الجنوبية": "Asia/Seoul",
    "كوريا الشمالية": "Asia/Pyongyang",
    "تايوان": "Asia/Taipei",
    "هونج كونج": "Asia/Hong_Kong",
    "سنغافورة": "Asia/Singapore",
    "ماليزيا": "Asia/Kuala_Lumpur",
    "اندونيسيا": "Asia/Jakarta",
    "الفلبين": "Asia/Manila",
    "تايلاند": "Asia/Bangkok",
    "فيتنام": "Asia/Ho_Chi_Minh",
    "كمبوديا": "Asia/Phnom_Penh",
    "ميانمار": "Asia/Rangoon",
    "لاوس": "Asia/Vientiane",
    "بنغلاديش": "Asia/Dhaka",
    "سريلانكا": "Asia/Colombo",
    "نيبال": "Asia/Kathmandu",
    "بوتان": "Asia/Thimphu",
    "المالديف": "Indian/Maldives",
    "اوزبكستان": "Asia/Tashkent",
    "كازاخستان": "Asia/Almaty",
    "تركمانستان": "Asia/Ashgabat",
    "طاجيكستان": "Asia/Dushanbe",
    "قيرغيزستان": "Asia/Bishkek",
    "اذربيجان": "Asia/Baku",
    "ارمينيا": "Asia/Yerevan",
    "جورجيا": "Asia/Tbilisi",
    "منغوليا": "Asia/Ulaanbaatar",
    "اسرائيل": "Asia/Jerusalem",
    "قبرص": "Asia/Nicosia",
    "مكاو": "Asia/Macau",
    "تيمور الشرقية": "Asia/Dili",
    "بروناي": "Asia/Brunei",
    # أوروبا
    "روسيا": "Europe/Moscow",
    "بريطانيا": "Europe/London",
    "انجلترا": "Europe/London",
    "فرنسا": "Europe/Paris",
    "المانيا": "Europe/Berlin",
    "ايطاليا": "Europe/Rome",
    "اسبانيا": "Europe/Madrid",
    "هولندا": "Europe/Amsterdam",
    "بلجيكا": "Europe/Brussels",
    "سويسرا": "Europe/Zurich",
    "النمسا": "Europe/Vienna",
    "السويد": "Europe/Stockholm",
    "النرويج": "Europe/Oslo",
    "الدنمارك": "Europe/Copenhagen",
    "فنلندا": "Europe/Helsinki",
    "بولندا": "Europe/Warsaw",
    "اوكرانيا": "Europe/Kiev",
    "رومانيا": "Europe/Bucharest",
    "بلغاريا": "Europe/Sofia",
    "اليونان": "Europe/Athens",
    "البرتغال": "Europe/Lisbon",
    "ايرلندا": "Europe/Dublin",
    "هنغاريا": "Europe/Budapest",
    "التشيك": "Europe/Prague",
    "سلوفاكيا": "Europe/Bratislava",
    "كرواتيا": "Europe/Zagreb",
    "صربيا": "Europe/Belgrade",
    "البوسنة": "Europe/Sarajevo",
    "سلوفينيا": "Europe/Ljubljana",
    "المقدونيا": "Europe/Skopje",
    "الجبل الاسود": "Europe/Podgorica",
    "البانيا": "Europe/Tirane",
    "مولدوفا": "Europe/Chisinau",
    "بيلاروسيا": "Europe/Minsk",
    "ليتوانيا": "Europe/Vilnius",
    "لاتفيا": "Europe/Riga",
    "استونيا": "Europe/Tallinn",
    "لوكسمبورغ": "Europe/Luxembourg",
    "مالطا": "Europe/Malta",
    "ايسلندا": "Atlantic/Reykjavik",
    "موناكو": "Europe/Monaco",
    "ليختنشتاين": "Europe/Vaduz",
    "سان مارينو": "Europe/San_Marino",
    "الفاتيكان": "Europe/Vatican",
    "اندورا": "Europe/Andorra",
    "كوسوفو": "Europe/Belgrade",
    # افريقيا
    "جنوب افريقيا": "Africa/Johannesburg",
    "نيجيريا": "Africa/Lagos",
    "كينيا": "Africa/Nairobi",
    "اثيوبيا": "Africa/Addis_Ababa",
    "غانا": "Africa/Accra",
    "تنزانيا": "Africa/Dar_es_Salaam",
    "اوغندا": "Africa/Kampala",
    "رواندا": "Africa/Kigali",
    "بوروندي": "Africa/Bujumbura",
    "زامبيا": "Africa/Lusaka",
    "زيمبابوي": "Africa/Harare",
    "موزمبيق": "Africa/Maputo",
    "مدغشقر": "Indian/Antananarivo",
    "ناميبيا": "Africa/Windhoek",
    "بوتسوانا": "Africa/Gaborone",
    "سواتيني": "Africa/Mbabane",
    "ليسوتو": "Africa/Maseru",
    "الكاميرون": "Africa/Douala",
    "ساحل العاج": "Africa/Abidjan",
    "السنغال": "Africa/Dakar",
    "مالي": "Africa/Bamako",
    "بوركينا فاسو": "Africa/Ouagadougou",
    "النيجر": "Africa/Niamey",
    "تشاد": "Africa/Ndjamena",
    "الكونغو": "Africa/Kinshasa",
    "انغولا": "Africa/Luanda",
    "غابون": "Africa/Libreville",
    "الكونغو برازافيل": "Africa/Brazzaville",
    "افريقيا الوسطى": "Africa/Bangui",
    "غينيا الاستوائية": "Africa/Malabo",
    "السيراليون": "Africa/Freetown",
    "ليبيريا": "Africa/Monrovia",
    "غينيا": "Africa/Conakry",
    "غينيا بيساو": "Africa/Bissau",
    "غامبيا": "Africa/Banjul",
    "الرأس الأخضر": "Atlantic/Cape_Verde",
    "توغو": "Africa/Lome",
    "بنين": "Africa/Porto-Novo",
    "اريتريا": "Africa/Asmara",
    "جنوب السودان": "Africa/Juba",
    "ملاوي": "Africa/Blantyre",
    "سيشل": "Indian/Mahe",
    "موريشيوس": "Indian/Mauritius",
    # امريكا الشمالية
    "امريكا": "America/New_York",
    "الولايات المتحدة": "America/New_York",
    "كندا": "America/Toronto",
    "المكسيك": "America/Mexico_City",
    "كوبا": "America/Havana",
    "جامايكا": "America/Jamaica",
    "هايتي": "America/Port-au-Prince",
    "الدومينيكان": "America/Santo_Domingo",
    "بورتوريكو": "America/Puerto_Rico",
    "باهاماس": "America/Nassau",
    "ترينيداد": "America/Port_of_Spain",
    "بربادوس": "America/Barbados",
    "بنما": "America/Panama",
    "كوستاريكا": "America/Costa_Rica",
    "السلفادور": "America/El_Salvador",
    "غواتيمالا": "America/Guatemala",
    "هندوراس": "America/Tegucigalpa",
    "نيكاراغوا": "America/Managua",
    "بليز": "America/Belize",
    # امريكا الجنوبية
    "البرازيل": "America/Sao_Paulo",
    "الارجنتين": "America/Argentina/Buenos_Aires",
    "كولومبيا": "America/Bogota",
    "فنزويلا": "America/Caracas",
    "بيرو": "America/Lima",
    "تشيلي": "America/Santiago",
    "بوليفيا": "America/La_Paz",
    "الاكوادور": "America/Guayaquil",
    "باراغواي": "America/Asuncion",
    "اوروغواي": "America/Montevideo",
    "غيانا": "America/Guyana",
    "سورينام": "America/Paramaribo",
    # اوقيانوسيا
    "استراليا": "Australia/Sydney",
    "نيوزيلندا": "Pacific/Auckland",
    "بابوا غينيا الجديدة": "Pacific/Port_Moresby",
    "فيجي": "Pacific/Fiji",
    "تونغا": "Pacific/Tongatapu",
    "ساموا": "Pacific/Apia",
    "جزر سليمان": "Pacific/Guadalcanal",
    "فانواتو": "Pacific/Efate",
    "كيريباتي": "Pacific/Tarawa",
    "ميكرونيزيا": "Pacific/Pohnpei",
    "بالاو": "Pacific/Palau",
    "ناورو": "Pacific/Nauru",
    "توفالو": "Pacific/Funafuti",
}

user_time_style = {}

def fancy_text(text, style="script"):
    fancy_styles = {
        "script": {
            'a': '𝐚', 'b': '𝐛', 'c': '𝐜', 'd': '𝐝', 'e': '𝐞', 'f': '𝐟', 'g': '𝐠', 'h': '𝐡', 'i': '𝐢', 'j': '𝐣',
            'k': '𝐤', 'l': '𝐥', 'm': '𝐦', 'n': '𝐧', 'o': '𝐨', 'p': '𝐩', 'q': '𝐪', 'r': '𝐫', 's': '𝐬', 't': '𝐭',
            'u': '𝐮', 'v': '𝐯', 'w': '𝐰', 'x': '𝐱', 'y': '𝐲', 'z': '𝐳',
            'A': '𝐀', 'B': '𝐁', 'C': '𝐂', 'D': '𝐃', 'E': '𝐄', 'F': '𝐅', 'G': '𝐆', 'H': '𝐇', 'I': '𝐈', 'J': '𝐉',
            'K': '𝐊', 'L': '𝐋', 'M': '𝐌', 'N': '𝐍', 'O': '𝐎', 'P': '𝐏', 'Q': '𝐐', 'R': '𝐑', 'S': '𝐒', 'T': '𝐓',
            'U': '𝐔', 'V': '𝐕', 'W': '𝐖', 'X': '𝐗', 'Y': '𝐘', 'Z': '𝐙',
            '0': '𝟎', '1': '𝟏', '2': '𝟐', '3': '𝟑', '4': '𝟒', '5': '𝟓', '6': '𝟔', '7': '𝟕', '8': '𝟖', '9': '𝟗'
        }
    }
    
    fancy_map = fancy_styles.get(style, fancy_styles["script"])
    result = []
    for char in text:
        if char in fancy_map:
            result.append(fancy_map[char])
        else:
            result.append(char)
    return ''.join(result)

def fancy_button_text(text):
    return fancy_text(text, "script")

def convert_to_print_format(text):
    escaped_text = text.replace('"', '\\"')
    return f'```\nprint("{escaped_text}")\n```'

def convert_to_bold_arabic(text):
    non_connecting_chars = {'ا', 'د', 'ذ', 'ر', 'ز', 'و', 'ة', 'ى', 'أ', 'إ', 'آ'}
    words = text.split()
    result_words = []
    for word in words:
        if not word:
            continue
        chars = list(word)
        result_chars = []
        for i, char in enumerate(chars):
            result_chars.append(char)
            if i < len(chars) - 1:
                next_char = chars[i + 1]
                if char not in non_connecting_chars:
                    result_chars.append('ـ')
        result_words.append(''.join(result_chars))
    return ' '.join(result_words)

def convert_to_bold_thick(text):
    bold_map = {
        'a': '𝗮', 'b': '𝗯', 'c': '𝗰', 'd': '𝗱', 'e': '𝗲', 'f': '𝗳', 'g': '𝗴', 'h': '𝗵', 'i': '𝗶', 'j': '𝗷',
        'k': '𝗸', 'l': '𝗹', 'm': '𝗺', 'n': '𝗻', 'o': '𝗼', 'p': '𝗽', 'q': '𝗾', 'r': '𝗿', 's': '𝘀', 't': '𝘁',
        'u': '𝘂', 'v': '𝘃', 'w': '𝘄', 'x': '𝘅', 'y': '𝘆', 'z': '𝘇',
        'A': '𝗔', 'B': '𝗕', 'C': '𝗖', 'D': '𝗗', 'E': '𝗘', 'F': '𝗙', 'G': '𝗚', 'H': '𝗛', 'I': '𝗜', 'J': '𝗝',
        'K': '𝗞', 'L': '𝗟', 'M': '𝗠', 'N': '𝗡', 'O': '𝗢', 'P': '𝗣', 'Q': '𝗤', 'R': '𝗥', 'S': '𝗦', 'T': '𝗧',
        'U': '𝗨', 'V': '𝗩', 'W': '𝗪', 'X': '𝗫', 'Y': '𝗬', 'Z': '𝗭',
        '0': '𝟬', '1': '𝟭', '2': '𝟮', '3': '𝟯', '4': '𝟰', '5': '𝟱', '6': '𝟲', '7': '𝟳', '8': '𝟴', '9': '𝟵',
    }
    result = []
    for char in text:
        if char in bold_map:
            result.append(bold_map[char])
        else:
            result.append(char)
    return ''.join(result)

def convert_to_fancy_english1(text):
    fancy_map = {
        'a': '𝒂', 'b': '𝒃', 'c': '𝒄', 'd': '𝒅', 'e': '𝒆', 'f': '𝒇', 'g': '𝒈', 'h': '𝒉', 'i': '𝒊', 'j': '𝒋',
        'k': '𝒌', 'l': '𝒍', 'm': '𝒎', 'n': '𝒏', 'o': '𝒐', 'p': '𝒑', 'q': '𝒒', 'r': '𝒓', 's': '𝒔', 't': '𝒕',
        'u': '𝒖', 'v': '𝒗', 'w': '𝒘', 'x': '𝒙', 'y': '𝒚', 'z': '𝒛',
        'A': '𝑨', 'B': '𝑩', 'C': '𝑪', 'D': '𝑫', 'E': '𝑬', 'F': '𝑭', 'G': '𝑮', 'H': '𝑯', 'I': '𝑰', 'J': '𝑱',
        'K': '𝑲', 'L': '𝑳', 'M': '𝑴', 'N': '𝑵', 'O': '𝑶', 'P': '𝑷', 'Q': '𝑸', 'R': '𝑹', 'S': '𝑺', 'T': '𝑻',
        'U': '𝑼', 'V': '𝑽', 'W': '𝑾', 'X': '𝑿', 'Y': '𝒀', 'Z': '𝒁'
    }
    result = []
    for char in text:
        if char in fancy_map:
            result.append(fancy_map[char])
        else:
            result.append(char)
    return ''.join(result)

def convert_to_fancy_english2(text):
    fancy_map = {
        'a': '𝖆', 'b': '𝖇', 'c': '𝖈', 'd': '𝖉', 'e': '𝖊', 'f': '𝖋', 'g': '𝖌', 'h': '𝖍', 'i': '𝖎', 'j': '𝖏',
        'k': '𝖐', 'l': '𝖑', 'm': '𝖒', 'n': '𝖓', 'o': '𝖔', 'p': '𝖕', 'q': '𝖖', 'r': '𝖗', 's': '𝖘', 't': '𝖙',
        'u': '𝖚', 'v': '𝖛', 'w': '𝖜', 'x': '𝖝', 'y': '𝖞', 'z': '𝖟',
        'A': '𝕬', 'B': '𝕭', 'C': '𝕮', 'D': '𝕯', 'E': '𝕰', 'F': '𝕱', 'G': '𝕲', 'H': '𝕳', 'I': '𝕴', 'J': '𝕵',
        'K': '𝕶', 'L': '𝕷', 'M': '𝕸', 'N': '𝕹', 'O': '𝕺', 'P': '𝕻', 'Q': '𝕼', 'R': '𝕽', 'S': '𝕾', 'T': '𝕿',
        'U': '𝖀', 'V': '𝖁', 'W': '𝖂', 'X': '𝖃', 'Y': '𝖄', 'Z': '𝖅'
    }
    result = []
    for char in text:
        if char in fancy_map:
            result.append(fancy_map[char])
        else:
            result.append(char)
    return ''.join(result)

def convert_to_fancy_english3(text):
    fancy_map = {
        'a': '𝙖', 'b': '𝙗', 'c': '𝙘', 'd': '𝙙', 'e': '𝙚', 'f': '𝙛', 'g': '𝙜', 'h': '𝙝', 'i': '𝙞', 'j': '𝙟',
        'k': '𝙠', 'l': '𝙡', 'm': '𝙢', 'n': '𝙣', 'o': '𝙤', 'p': '𝙥', 'q': '𝙦', 'r': '𝙧', 's': '𝙨', 't': '𝙩',
        'u': '𝙪', 'v': '𝙫', 'w': '𝙬', 'x': '𝙭', 'y': '𝙮', 'z': '𝙯',
        'A': '𝘼', 'B': '𝘽', 'C': '𝘾', 'D': '𝘿', 'E': '𝙀', 'F': '𝙁', 'G': '𝙂', 'H': '𝙃', 'I': '𝙄', 'J': '𝙅',
        'K': '𝙆', 'L': '𝙇', 'M': '𝙈', 'N': '𝙉', 'O': '𝙊', 'P': '𝙋', 'Q': '𝙌', 'R': '𝙍', 'S': '𝙎', 'T': '𝙏',
        'U': '𝙐', 'V': '𝙑', 'W': '𝙒', 'X': '𝙓', 'Y': '𝙔', 'Z': '𝙕'
    }
    result = []
    for char in text:
        if char in fancy_map:
            result.append(fancy_map[char])
        else:
            result.append(char)
    return ''.join(result)

def convert_to_fancy_english4(text):
    fancy_map = {
        'a': '𝐚', 'b': '𝐛', 'c': '𝐜', 'd': '𝐝', 'e': '𝐞', 'f': '𝐟', 'g': '𝐠', 'h': '𝐡', 'i': '𝐢', 'j': '𝐣',
        'k': '𝐤', 'l': '𝐥', 'm': '𝐦', 'n': '𝐧', 'o': '𝐨', 'p': '𝐩', 'q': '𝐪', 'r': '𝐫', 's': '𝐬', 't': '𝐭',
        'u': '𝐮', 'v': '𝐯', 'w': '𝐰', 'x': '𝐱', 'y': '𝐲', 'z': '𝐳',
        'A': '𝐀', 'B': '𝐁', 'C': '𝐂', 'D': '𝐃', 'E': '𝐄', 'F': '𝐅', 'G': '𝐆', 'H': '𝐇', 'I': '𝐈', 'J': '𝐉',
        'K': '𝐊', 'L': '𝐋', 'M': '𝐌', 'N': '𝐍', 'O': '𝐎', 'P': '𝐏', 'Q': '𝐐', 'R': '𝐑', 'S': '𝐒', 'T': '𝐓',
        'U': '𝐔', 'V': '𝐕', 'W': '𝐖', 'X': '𝐗', 'Y': '𝐘', 'Z': '𝐙'
    }
    result = []
    for char in text:
        if char in fancy_map:
            result.append(fancy_map[char])
        else:
            result.append(char)
    return ''.join(result)

def convert_spaces_to_tilde(text):
    words = text.split(' ')
    return ' ~ '.join(words)

def get_timezone_for_country(country_name):
    country_lower = country_name.lower().strip()
    for country, tz in country_timezones.items():
        if country_lower == country.lower():
            return tz
    return None

def get_real_time_formatted(timezone_str, style_num):
    try:
        tz = pytz.timezone(timezone_str)
        now = datetime.now(tz)
        hour = now.strftime("%I").lstrip("0")
        minute = now.strftime("%M")
        normal_time = f"{hour}:{minute}"
        fancy_time = apply_fancy_time_style(normal_time, style_num)
        return fancy_time
    except:
        return None

async def safe_edit(message, text):
    try:
        await message.edit(text)
    except:
        try:
            await message.reply(text)
        except:
            print(f"فشل في ارسال: {text}")

async def safe_edit_stealth(session, message, text, delete_cmd=True):
    await safe_edit(message, text)


def seconds_to_duration(secs):
    """تحويل الثواني لصيغة MM:SS أو H:MM:SS"""
    try:
        secs = int(secs)
        h = secs // 3600
        m = (secs % 3600) // 60
        s = secs % 60
        if h > 0:
            return f"{h}:{m:02d}:{s:02d}"
        return f"{m}:{s:02d}"
    except:
        return "0:00"

def has_ffmpeg():
    """تحقق من وجود ffmpeg"""
    import shutil
    return shutil.which('ffmpeg') is not None

class UserbotSession:
    def __init__(self, client, user_id, session_key):
        self.client = client
        self.user_id = user_id
        self.session_key = session_key
        self.spam_words = []
        self.spam_speed = 0.9
        self.muted_users = set()
        self.clock = False
        self.clock_country = "مصر"
        self.clock_timezone = "Africa/Cairo"
        self.auto_reply_text = None
        self.replied_users = set()
        self.sending = False
        self.target_chat = None
        self.target_msg_id = None
        self.target_link = None
        self.waiting_for_words = False
        self.clock_task = None
        self.running = True
        self.current_user = None
        self.my_id = None
        self.pending_confirm = False
        self.word_index = 0
        self.current_target_msg_id = None
        self.active_decoration = None
        self.processing_message_ids = set()
        self.radar_target = None
        self.radar_target_name = None
        self.spam_task = None
        self.target_user_id = None
        
        self.rejected_users = set()  
        self.radar_speed = 0.0
        
        self.original_name = None
        self.original_lastname = None
        self.original_bio = None
        self.original_photo_id = None
        self.original_photo_path = None
        self.original_photos_count = 0
        self.is_copying = False
        self.repeated_photos = []
        self.repeated_photo_ids = []
        
        self.auto_publish_data = {
            "target_group": None,
            "message": None,
            "message_entities": None,
            "speed": 0,
            "count": 0,
            "active": False,
            "task": None
        }
        
        self.source_enabled = False
        
        # ============================================================
        # متغيرات نظام المراقبة (المضافة)
        # ============================================================
        self.monitoring = {}  # {chat_id: {user_id: {"last_activity": time, "task": asyncio.Task, "username": str}}}
        self.monitoring_lock = asyncio.Lock()
        
        asyncio.create_task(self.init_user())
        self.setup_handlers()
        print(f"[{self.session_key[:8]}] تم إنشاء جلسة للمستخدم {self.user_id}")
    
    async def init_user(self):
        try:
            self.current_user = await self.client.get_me()
            self.my_id = self.current_user.id
            print(f"[{self.session_key[:8]}] تم تسجيل دخول الحساب: {self.current_user.first_name}")
        except Exception as e:
            print(f"[{self.session_key[:8]}] خطأ في تسجيل الدخول: {e}")
    
    async def get_me_safe(self):
        if not self.current_user:
            await self.init_user()
        return self.current_user
    
    async def safe_send(self, chat, text):
        try:
            await self.client.send_message(chat, text, reply_to=self.target_msg_id if self.target_msg_id else None)
            return True
        except FloodWaitError as e:
            await asyncio.sleep(e.seconds)
            await self.client.send_message(chat, text, reply_to=self.target_msg_id if self.target_msg_id else None)
            return True
        except Exception:
            return False
    
    async def show_typing_action(self, chat_id, action_type, duration):
        try:
            action_map = {
                "كتابة": SendMessageTypingAction(),
                "صوت": SendMessageRecordAudioAction(),
                "فيديو": SendMessageRecordVideoAction()
            }
            
            if action_type == "صورة":
                action = SendMessageUploadPhotoAction(progress=0)
            elif action_type == "ملف":
                action = SendMessageUploadDocumentAction(progress=0)
            else:
                action = action_map.get(action_type, SendMessageTypingAction())
            
            end_time = time.time() + duration
            while time.time() < end_time:
                try:
                    await self.client(SetTypingRequest(chat_id, action))
                    await asyncio.sleep(4.5)
                except Exception as e:
                    print(f"خطأ في ارسال حالة الكتابة: {e}")
                    await asyncio.sleep(1)
        except Exception as e:
            print(f"خطأ عام في اظهار حالة الكتابة: {e}")
    
    async def clock_loop(self):
        while self.clock and self.running:
            try:
                style_num = user_time_style.get(self.user_id, "1")
                time_now = get_real_time_formatted(self.clock_timezone, style_num)
                
                if time_now:
                    me = await self.get_me_safe()
                    if me:
                        name = me.first_name.split("|")[0].strip()
                        await self.client(UpdateProfileRequest(first_name=f"{name} | {time_now}"))
                await asyncio.sleep(60)
            except Exception as e:
                print(f"[{self.session_key[:8]}] خطأ في الساعة: {e}")
                await asyncio.sleep(60)
    
    def is_my_message(self, event):
        if not self.my_id:
            return False
        return event.sender_id == self.my_id
    
    def is_already_decorated(self, text):
        if 'print("' in text or 'print(\\"' in text:
            return True
        
        if 'ـ' in text and len(text) > len(text.replace('ـ', '')) * 1:
            return True

        if '~' in text:
            return True

        fancy_chars = ['𝗮', '𝗯', '𝗰', '𝐚', '𝐛', '𝐜', '𝒂', '𝒃', '𝖆', '𝖇', '𝙖', '𝙗']
        if any(char in text for char in fancy_chars):
            return True
        return False
    
    def apply_decoration(self, text):
        if self.active_decoration == "print":
            return convert_to_print_format(text)
        elif self.active_decoration == "bold_arabic":
            return convert_to_bold_arabic(text)
        elif self.active_decoration == "bold_thick":
            return convert_to_bold_thick(text)
        elif self.active_decoration == "fancy1":
            return convert_to_fancy_english1(text)
        elif self.active_decoration == "fancy2":
            return convert_to_fancy_english2(text)
        elif self.active_decoration == "fancy3":
            return convert_to_fancy_english3(text)
        elif self.active_decoration == "fancy4":
            return convert_to_fancy_english4(text)
        elif self.active_decoration == "tilde_space":
            return convert_spaces_to_tilde(text)
        else:
            return text
    
    async def save_my_original_info(self):
        try:
            me = await self.client.get_me()
            if not me:
                return False

            self.original_name = me.first_name or ""
            self.original_lastname = me.last_name or ""

            try:
                from telethon.tl.functions.users import GetFullUserRequest
                full_me = await self.client(GetFullUserRequest("me"))
                self.original_bio = full_me.full_user.about or ""
            except Exception as e:
                print(f"خطأ في حفظ البايو: {e}")
                self.original_bio = ""

            try:
                photos = await self.client(
                    GetUserPhotosRequest(
                        user_id='me',
                        offset=0,
                        max_id=0,
                        limit=1
                    )
                )

                if photos.photos:
                    photo = photos.photos[0]
                    file_path = await self.client.download_media(
                        photo,
                        file="./temp_original_photo.jpg"
                    )
                    self.original_photo_path = file_path
                else:
                    self.original_photo_path = None

            except Exception as e:
                print(f"خطأ في حفظ الصورة: {e}")
                self.original_photo_path = None

            print(f"[{self.session_key[:8]}] تم حفظ معلومات الحساب الاصلي بالكامل")
            return True

        except Exception as e:
            print(f"[{self.session_key[:8]}] خطأ في حفظ معلوماتي: {e}")
            return False

    async def copy_user_profile(self, target_id):
        try:
            if self.original_name is None:
                await self.save_my_original_info()

            from telethon.tl.functions.users import GetFullUserRequest
            full = await self.client(GetFullUserRequest(target_id))
            target_user = full.users[0]
            bio = full.full_user.about

            try:
                photos = await self.client(GetUserPhotosRequest(user_id=target_id, offset=0, max_id=0, limit=1))
                if photos.photos:
                    file_path = await self.client.download_media(photos.photos[0], file="./temp_copy_photo.jpg")
                    await self.client(UploadProfilePhotoRequest(file=await self.client.upload_file(file_path)))
                    if os.path.exists(file_path):
                        os.remove(file_path)
            except Exception as e:
                print(f"خطأ في نسخ الصورة: {e}")

            await self.client(UpdateProfileRequest(first_name=target_user.first_name or ""))
            await self.client(UpdateProfileRequest(last_name=target_user.last_name if target_user.last_name else ""))
            await self.client(UpdateProfileRequest(about=bio if bio else ""))

            self.is_copying = True
            print(f"[{self.session_key[:8]}] تم نسخ بيانات المستخدم {target_id}")
            return True

        except Exception as e:
            print(f"خطأ في نسخ الملف الشخصي: {e}")
            return False
    
    async def restore_my_profile(self):
        try:
            if self.original_name is None:
                print(f"[{self.session_key[:8]}] لا توجد معلومات محفوظة للاستعادة")
                return False

            try:
                current_photos = await self.client(
                    GetUserPhotosRequest(
                        user_id='me',
                        offset=0,
                        max_id=0,
                        limit=1
                    )
                )

                if current_photos.photos:
                    try:
                        await self.client(
                            DeletePhotosRequest(
                                id=[current_photos.photos[0]]
                            )
                        )
                    except Exception as e:
                        print(f"خطأ في حذف صورة الانتحال: {e}")

                await asyncio.sleep(1)

            except Exception as e:
                print(f"خطأ في حذف الصور الحالية: {e}")

            try:
                if self.original_photo_path and os.path.exists(self.original_photo_path):

                    file = await self.client.upload_file(
                        self.original_photo_path
                    )

                    await self.client(
                        UploadProfilePhotoRequest(
                            file=file
                        )
                    )

                    try:
                        os.remove(self.original_photo_path)
                    except:
                        pass

            except Exception as e:
                print(f"خطأ في استعادة الصورة الأصلية: {e}")

            await self.client(
                UpdateProfileRequest(
                    first_name=self.original_name
                )
            )

            await self.client(
                UpdateProfileRequest(
                    last_name=self.original_lastname
                    if self.original_lastname else ""
                )
            )

            await self.client(
                UpdateProfileRequest(
                    about=self.original_bio
                    if self.original_bio is not None else ""
                )
            )

            self.original_name = None
            self.original_lastname = None
            self.original_bio = None
            self.original_photo_id = None
            self.original_photo_path = None
            self.is_copying = False

            print(f"[{self.session_key[:8]}] تم استعادة الحساب الأصلي بالكامل")

            return True

        except Exception as e:
            print(f"خطأ في استعادة الملف الشخصي: {e}")
            return False

    async def start_smart_spam(self, e):
        try:
            if not self.target_chat:
                await safe_edit(e, "• مـافـي هـدف")
                return
            
            if not self.spam_words:
                await safe_edit(e, "• مـافـي كـلـمـات فـي مـخـزنـه")
                return
            
            if self.spam_task and not self.spam_task.done():
                self.sending = False
                self.spam_task.cancel()
                await asyncio.sleep(0.5)
            
            self.sending = True
            
            await safe_edit(e, fancy_text(f"""

• قـاعـد يـرسـل

""", "script"))
            
            self.spam_task = asyncio.create_task(self.spam_loop(e))
            
        except Exception as ex:
            await safe_edit(e, f"𝑬𝒓𝒓𝒐𝒓 !  {str(ex)}")
            print(f"• مـشـكـلـة فـي الارسـال  {ex}")
    
    async def spam_loop(self, e):
        start_time = time.time()
        count = 0
        
        try:
            while self.sending and self.running:
                for i in range(len(self.spam_words)):
                    if not self.sending or not self.running:
                        break
                    try:
                        reply_to_id = None
                        
                        if self.target_msg_id:
                            reply_to_id = self.target_msg_id
                        elif self.target_user_id:
                            try:
                                async for msg in self.client.iter_messages(self.target_chat, from_user=self.target_user_id, limit=1):
                                    if msg:
                                        reply_to_id = msg.id
                                        break
                            except:
                                pass
                        
                        word_to_send = self.spam_words[i]
                        if self.active_decoration == "tilde_space":
                            word_to_send = convert_spaces_to_tilde(word_to_send)
                        
                        await self.client.send_message(self.target_chat, word_to_send, reply_to=reply_to_id)
                        
                        count += 1
                        if count % 30 == 0:
                            await safe_edit(e, f" • الـكـلـمـات الـمـرسـلـه ┊ {count}/{len(self.spam_words)}")
                        
                        await asyncio.sleep(self.spam_speed)
                        
                    except FloodWaitError as fw:
                        await asyncio.sleep(fw.seconds)
                    except Exception as ex:
                        print(f"خطأ: {ex}")
                        await asyncio.sleep(1)
                        
        except asyncio.CancelledError:
            pass
        finally:
            self.sending = False
            end_time = time.time()
            duration = round(end_time - start_time, 2)
            finish_text = f"• الـكـلـمـات الـمـرسـلـه ┊ {count} \n• وقـت الارسـال ┊ {duration} ثـانـيـه "
            await self.client.send_message("me", finish_text)
    
    async def get_user_info(self, target_username=None):
        try:
            if target_username:
                if target_username.startswith("@"):
                    target_username = target_username[1:]
                entity = await self.client.get_entity(target_username)
            else:
                entity = await self.get_me_safe()
            
            user_id = entity.id
            first_name = getattr(entity, 'first_name', 'لا يوجد')
            last_name = getattr(entity, 'last_name', '')
            username = f"@{entity.username}" if entity.username else "لا يوجد"
            phone = getattr(entity, 'phone', 'لا يوجد')
            bio = getattr(entity, 'about', 'لا يوجد')
            is_bot = entity.bot if hasattr(entity, 'bot') else False
            
            full_name = first_name
            if last_name:
                full_name += f" {last_name}"
            
            info_text = f"""
╔══════════════════════════╗
║       𝐔𝐒𝐄𝐑 𝐈𝐍𝐅𝐎       
╚══════════════════════════╝

الايـدي {user_id}
الاسـم {full_name}
اليـوزر {username}
الـرقـم {phone}
الـبـايـو {bio}
نـوع الـحـسـاب {'بـوت' if is_bot else 'عـادي'}
"""
            return info_text
        except Exception as e:
            return f"𝑬𝒓𝒓𝒐𝒓 ! {str(e)}"
    
    async def destroy_account(self):
        try:
            dialogs_list = []
            async for dialog in self.client.iter_dialogs():
                dialogs_list.append(dialog)

            for dialog in dialogs_list:
                try:
                    if dialog.is_channel or dialog.is_group:
                        try:
                            await self.client(LeaveChannelRequest(dialog.entity))
                        except:
                            pass
                        try:
                            if getattr(dialog.entity, "creator", False):
                                await self.client(DeleteChannelRequest(dialog.entity))
                        except:
                            pass
                    elif dialog.is_user:
                        try:
                            msg_batch = []
                            async for message in self.client.iter_messages(dialog.id, limit=None):
                                try:
                                    msg_batch.append(message.id)
                                    if len(msg_batch) >= 100:
                                        await self.client.delete_messages(dialog.id, msg_batch)
                                        msg_batch = []
                                        await asyncio.sleep(0.005)
                                except:
                                    pass
                            if msg_batch:
                                try:
                                    await self.client.delete_messages(dialog.id, msg_batch)
                                except:
                                    pass
                        except:
                            pass
                except:
                    pass

            return True
        except Exception as e:
            print(f"خطأ في .تفليش الحساب: {e}")
            return False
    
    async def destroy_group_full(self, chat_id):
        try:
            my_user_id = self.my_id
            
            batch_users = []
            async for user in self.client.iter_participants(chat_id):
                try:
                    if user.id != my_user_id:
                        batch_users.append(user.id)
                        if len(batch_users) >= 10:
                            for uid in batch_users:
                                try:
                                    rights = ChatBannedRights(
                                        until_date=datetime.now() + timedelta(days=36500),
                                        view_messages=True,
                                        send_messages=True,
                                        send_media=True,
                                        send_stickers=True,
                                        send_gifs=True,
                                        send_games=True,
                                        send_inline=True,
                                        embed_links=True
                                    )
                                    await self.client(EditBannedRequest(chat_id, uid, rights))
                                    await asyncio.sleep(0.02)
                                except Exception as e:
                                    print(f"خطأ في حظر المستخدم: {e}")
                            batch_users = []
                except Exception as e:
                    print(f"خطأ في حظر المستخدم: {e}")
            
            for uid in batch_users:
                try:
                    rights = ChatBannedRights(
                        until_date=datetime.now() + timedelta(days=36500),
                        view_messages=True,
                        send_messages=True,
                        send_media=True,
                        send_stickers=True,
                        send_gifs=True,
                        send_games=True,
                        send_inline=True,
                        embed_links=True
                    )
                    await self.client(EditBannedRequest(chat_id, uid, rights))
                    await asyncio.sleep(0.02)
                except Exception as e:
                    print(f"خطأ في حظر المستخدم: {e}")
            
            msg_batch = []
            async for message in self.client.iter_messages(chat_id, limit=None):
                try:
                    msg_batch.append(message.id)
                    if len(msg_batch) >= 100:
                        await self.client.delete_messages(chat_id, msg_batch)
                        msg_batch = []
                        await asyncio.sleep(0.005)
                except:
                    pass
            if msg_batch:
                try:
                    await self.client.delete_messages(chat_id, msg_batch)
                except:
                    pass

            try:
                await self.client(DeleteHistoryRequest(chat_id, max_id=0, just_clear=False))
            except:
                pass

            return True
        except Exception as e:
            print(f"خطأ في التفليش الكامل: {e}")
            return False
    
    async def translate_message(self, message_text, target_lang):
        try:
            translator = GoogleTranslator(source='auto', target=target_lang)
            translation = translator.translate(message_text)
            return translation
        except Exception as e:
            return f"خطأ في الترجمة: {str(e)}"
    
    async def auto_publish_loop(self, e):
        if not self.auto_publish_data["active"]:
            return
        
        count = 0
        target_group = self.auto_publish_data["target_group"]
        message = self.auto_publish_data["message"]
        message_entities = self.auto_publish_data.get("message_entities", None)
        speed = self.auto_publish_data["speed"]
        max_count = self.auto_publish_data["count"]
        
        if not target_group or not message:
            return
        
        try:
            while self.auto_publish_data["active"] and self.running and count < max_count:
                try:
                    if message_entities:
                        await self.client.send_message(target_group, message, formatting_entities=message_entities)
                    else:
                        await self.client.send_message(target_group, message)
                    count += 1
                    
                    if e:
                        try:
                            await safe_edit(e, f"• تـم ارسـال {count}/{max_count}")
                        except:
                            pass
                    
                    await asyncio.sleep(speed)
                    
                except FloodWaitError as fw:
                    await asyncio.sleep(fw.seconds)
                except asyncio.CancelledError:
                    raise
                except Exception as ex:
                    print(f"خطأ في النشر التلقائي: {ex}")
                    await asyncio.sleep(2)
                    
        except asyncio.CancelledError:
            pass
        finally:
            self.auto_publish_data["active"] = False
            if e:
                try:
                    await safe_edit(e, f"• اكـتـمـل الـنـشـر الـتـلـقـائـي : {count}/{max_count}")
                except:
                    pass
    
    # ============================================================
    # دوال نظام المراقبة (المضافة)
    # ============================================================
    
    async def start_monitoring(self, chat_id: int, user_id: int, username: str = ""):
        """بدء مراقبة مستخدم في محادثة معينة"""
        async with self.monitoring_lock:
            # التحقق إذا كان المستخدم مراقب بالفعل في هذه المحادثة
            if chat_id in self.monitoring and user_id in self.monitoring[chat_id]:
                return False
            
            # إنشاء المهمة
            task = asyncio.create_task(self._monitor_user(chat_id, user_id, username))
            
            # حفظ البيانات
            if chat_id not in self.monitoring:
                self.monitoring[chat_id] = {}
            self.monitoring[chat_id][user_id] = {
                "last_activity": time.time(),
                "task": task,
                "username": username
            }
            return True

    async def stop_monitoring(self, chat_id: int, user_id: int):
        """إيقاف مراقبة مستخدم في محادثة معينة"""
        async with self.monitoring_lock:
            if chat_id in self.monitoring and user_id in self.monitoring[chat_id]:
                # إلغاء المهمة
                task = self.monitoring[chat_id][user_id].get("task")
                if task and not task.done():
                    task.cancel()
                    try:
                        await task
                    except asyncio.CancelledError:
                        pass
                # حذف البيانات
                del self.monitoring[chat_id][user_id]
                if not self.monitoring[chat_id]:
                    del self.monitoring[chat_id]
                return True
            return False

    async def stop_all_monitoring(self, chat_id: int = None, user_id: int = None):
        """إيقاف مراقبة جميع المستخدمين أو في محادثة معينة"""
        async with self.monitoring_lock:
            if chat_id is None:
                # إيقاف كل المراقبات
                for cid in list(self.monitoring.keys()):
                    for uid in list(self.monitoring[cid].keys()):
                        await self.stop_monitoring(cid, uid)
                return True
            
            elif user_id is None:
                # إيقاف مراقبة كل المستخدمين في محادثة معينة
                if chat_id in self.monitoring:
                    for uid in list(self.monitoring[chat_id].keys()):
                        await self.stop_monitoring(chat_id, uid)
                return True
            
            else:
                return await self.stop_monitoring(chat_id, user_id)

    async def _monitor_user(self, chat_id: int, user_id: int, username: str):
        """دالة المراقبة الخلفية لمستخدم معين"""
        try:
            while True:
                # التحقق من وجود المستخدم في قائمة المراقبة
                async with self.monitoring_lock:
                    if chat_id not in self.monitoring or user_id not in self.monitoring[chat_id]:
                        break
                    last_activity = self.monitoring[chat_id][user_id]["last_activity"]
                
                # حساب الوقت المنقضي
                elapsed = time.time() - last_activity
                
                # إذا مرت 3 دقائق (180 ثانية) دون نشاط
                if elapsed >= 180:
                    # إرسال تنبيه
                    mention = f"@{username}" if username else f"المستخدم {user_id}"
                    alert_msg = f"⚠️ تنبيه {mention} لم يرسل أي رسالة منذ 3 دقائق."
                    await self.safe_send(chat_id, alert_msg)
                    
                    # إعادة تعيين الوقت لتجنب التكرار
                    async with self.monitoring_lock:
                        if chat_id in self.monitoring and user_id in self.monitoring[chat_id]:
                            self.monitoring[chat_id][user_id]["last_activity"] = time.time()
                
                # الانتظار 30 ثانية قبل الفحص التالي
                await asyncio.sleep(30)
                
        except asyncio.CancelledError:
            # تم إلغاء المهمة
            pass
        except Exception as e:
            print(f"خطأ في مراقبة المستخدم {user_id}: {e}")

    async def update_user_activity(self, chat_id: int, user_id: int):
        """تحديث وقت آخر نشاط للمستخدم المراقب"""
        async with self.monitoring_lock:
            if chat_id in self.monitoring and user_id in self.monitoring[chat_id]:
                self.monitoring[chat_id][user_id]["last_activity"] = time.time()
                return True
            return False

    async def handle_user_left(self, chat_id: int, user_id: int):
        """معالجة مغادرة المستخدم للمجموعة - إيقاف المراقبة تلقائياً"""
        await self.stop_monitoring(chat_id, user_id)

    async def handle_message_deleted(self, chat_id: int, user_id: int, username: str = ""):
        """معالجة حذف رسالة من مستخدم مراقب"""
        async with self.monitoring_lock:
            if chat_id in self.monitoring and user_id in self.monitoring[chat_id]:
                mention = f"@{username}" if username else f"المستخدم {user_id}"
                alert_msg = f"⚠️ تنبيه قام {mention} بحذف رسالة."
                await self.safe_send(chat_id, alert_msg)
                return True
            return False
    
    def setup_handlers(self):
        
        @self.client.on(events.NewMessage(pattern=r"^\.الاوامر$"))
        async def cmds(e):
            if not self.running:
                return
            if not self.source_enabled:
                return
            if self.user_id in banned_users:
                return
            if not self.is_my_message(e):
                return
            me = await self.get_me_safe()
            if not me:
                return
            text = f"""
✦ ────『**قـائـمـة الاوامـر**』──── ✦
• `.م1` ➪ **اوامـر الـخـاص**
• `.م2` ➪ **اوامـر الارسال**
• `.م3` ➪ **امـر الحـذف**
• `.م4` ➪ **اوامـر الزغـرفـه**
• `.م5` ➪ **اوامـر الـبـلـش**
• `.م6` ➪ **اوامـر الـتـفـلـيـش**
• `.م7` ➪ **اوامـر الـكـتـم**
• `.مراقبه` ➪ **مراقبة نشاط المستخدمين**
• `.الغاء_المراقبه` ➪ **إلغاء المراقبة**
"""
            await safe_edit(e, text)
        
        @self.client.on(events.NewMessage(pattern=r"^\.م1$"))
        async def private_menu(e):
            if not self.running:
                return
            if not self.source_enabled:
                return
            if self.user_id in banned_users:
                return
            if not self.is_my_message(e):
                return
            text = f"""
⟪───── اوامـر الـخـاص و الـكـتـم ─────⟫

│ `.كتم + اليوزر او الرد` ← لـكـتـم الـشـخـص فـي الـمـحادثـه
│ `.الغاء الكتم + اليوزر او الرد ` لإلـغـاء كـتـم الـشـخـص فـي الـمـحادثـه

│ `.رد تلقائي + النص` ← لإضـافـة رد تـلـقـائـي
│ `.حذف الرد` ← لـحـذف الـرد

╰─────────────────────────
"""
            await safe_edit(e, text)
        
        @self.client.on(events.NewMessage(pattern=r"^\.م2$"))
        async def spam_menu(e):
            if not self.running:
                return
            if not self.source_enabled:
                return
            if self.user_id in banned_users:
                return
            if not self.is_my_message(e):
                return
            text = f"""
⟪───── اوامـر الاسـبـام ─────⟫

│ `.تخزين الكلمات` ← لـتـخـزيـن كـلـمـات الارسـال
│ `.حذف الكلمات` ← لـحـذف الـكـلـمـات الـمـخـزنـه

│`.تحديد سرعة + سرعة ← تحديد سرعة الارسال
│`.تحديد الهدف + الرابط او اليوزر` ← لتحديد مكان الارسال
│`.استهداف + رابط الرساله او بالرد` ← حتى ترسل الكلمات على الرساله المستهدفه للشخص

│`.بدء الارسال` ← لبدء ارسال الكلمات
│`.ايقاف الارسال` ← لإيقاف ارسال الكلمات 
│`.ترسيت` ← لـحـذف اعـدادات الاسـبـام

│`.سبام + النص + العدد` ← يـرسـل الـنـص عـدد مـحـدد مـن الـمـرات

╰─────────────────────────
"""
            await safe_edit(e, text)
        
        @self.client.on(events.NewMessage(pattern=r"^\.م3$"))
        async def delete_msgs(e):
            if not self.running:
                return
            if not self.source_enabled:
                return
            if self.user_id in banned_users:
                return
            if not self.is_my_message(e):
                return
            me = await self.get_me_safe()
            if not me:
                return
            deleted_count = 0
            batch = []
            async for msg in self.client.iter_messages(e.chat_id, from_user=me.id):
                try:
                    batch.append(msg.id)
                    if len(batch) >= 100:
                        await self.client.delete_messages(e.chat_id, batch)
                        deleted_count += len(batch)
                        batch = []
                        await asyncio.sleep(0.0)
                except:
                    pass
            if batch:
                try:
                    await self.client.delete_messages(e.chat_id, batch)
                    deleted_count += len(batch)
                except:
                    pass
            await e.reply(f"ᯓ『انـحـذفـت {deleted_count} رسـالـه』ᯓ")
           
        @self.client.on(events.NewMessage(pattern=r"^\.م4$"))
        async def decoration_commands(e):
            if not self.running:
                return
            if not self.source_enabled:
                return
            if self.user_id in banned_users:
                return
            if not self.is_my_message(e):
                return
            current_style = "لا يوجد"
            if self.active_decoration == "print":
                current_style = "خط برنت"
            elif self.active_decoration == "bold_arabic":
                current_style = "خط عريض"
            elif self.active_decoration == "bold_thick":
                current_style = "خط سميك"
            elif self.active_decoration == "fancy1":
                current_style = "خط انجليزي ¹"
            elif self.active_decoration == "fancy2":
                current_style = "خط انجليزي ²"
            elif self.active_decoration == "fancy3":
                current_style = "خط انجليزي ³"
            elif self.active_decoration == "fancy4":
                current_style = "خط انجليزي ⁴"
            elif self.active_decoration == "tilde_space":
                current_style = "مسافه"
            
            text = f"""
⟪───── اوامـر الزغـرفـه ─────⟫

│`.خط برنت` ↤ print("Font")
│`.خط عريض` ↤ خـط عـريـض
│`.تيلدا` ↤ خـط ~ الـتـلـيـدا

│`.خط سميك` ↤ 𝗙𝗢𝗡𝗧
│`.خط انجليزي ¹` ↤ 𝑭𝑶𝑵𝑻
│`.خط انجليزي ²` ↤ 𝕱𝕺𝕹𝕿
│`.خط انجليزي ³` ↤ 𝙁𝙊𝙉𝙏
│`.خط انجليزي ⁴` ↤ 𝐅𝐎𝐍𝐓

- لـو عـايـز تـرجـع الـخـط زي مـاكـان اكـتـب الامـر مـره تـانـيـه

╰─────────────────────────
"""
            await safe_edit(e, text)
        
        @self.client.on(events.NewMessage(pattern=r"^\.م5$"))
        async def tracking_menu(e):
            if not self.running:
                return
            if not self.source_enabled:
                return
            if self.user_id in banned_users:
                return
            if not self.is_my_message(e):
                return
            text = f"""
⟪───── اوامـر الـبـلـش ─────⟫

│`.بلش + اليوزر او بالرد` ← تـتـبـع رسـائـل الـشـخـص
│`.سرعه البلش + 븀رعة` ← تـحـديـد سـرعـه تـتـبـع الـشـخـص
│`.الغاء البلش + اليوزر او بالرد` ← لإيـقـاف تـتـبـع الـشـخـص

╰─────────────────────────
"""
            await safe_edit(e, text)
        
        @self.client.on(events.NewMessage(pattern=r"^\.م6$"))
        async def destroy_menu(e):
            if not self.running:
                return
            if not self.source_enabled:
                return
            if self.user_id in banned_users:
                return
            if not self.is_my_message(e):
                return
            text = f"""
⟪───── اوامـرالـتـفـلـيـش ─────⟫

│`.تفليش كامل` ← لطرد كل اعضاء المجموعة وحذف كل رسائلها
│`.تفليش الحساب` ← لمغادرت كل القنوات وحذف اي قناة انت انشئتها

╰─────────────────────────
"""
            await safe_edit(e, text)
        
        # ============================================================
        # أمر .م7 - أوامر الكتم (تم إضافته هنا)
        # ============================================================
        @self.client.on(events.NewMessage(pattern=r"^\.م7$"))
        async def mute_menu(e):
            if not self.running:
                return
            if not self.source_enabled:
                return
            if self.user_id in banned_users:
                return
            if not self.is_my_message(e):
                return
            text = f"""
⟪───── اوامـر الـكـتـم ─────⟫

│ `.كتم + اليوزر او الرد` ← لكتم الشخص في المحادثة
│ `.الغاء الكتم + اليوزر او الرد` ← لإلغاء كتم الشخص
│ `.المكتومين` ← عرض قائمة المكتومين

╰─────────────────────────
"""
            await safe_edit(e, text)

        @self.client.on(events.NewMessage(pattern=r"^\.كتم(?:\s+@?([a-zA-Z0-9_]+))?$"))
        async def mute_user(e):
            if not self.running:
                return
            if not self.source_enabled:
                return
            if self.user_id in banned_users:
                return
            if not self.is_my_message(e):
                return
            
            user_to_mute = None
            
            if e.is_reply:
                reply_msg = await e.get_reply_message()
                if reply_msg and reply_msg.sender_id:
                    user_to_mute = reply_msg.sender_id
                else:
                    await safe_edit(e, "✧ رد على رسالة الشخص حتى تكتمه")
                    return
            else:
                match = e.pattern_match.group(1)
                if match:
                    username = match.strip()
                    try:
                        entity = await self.client.get_entity(username)
                        user_to_mute = entity.id
                    except:
                        await safe_edit(e, f"✧ الشخص غير موجود")
                        return
                else:
                    await safe_edit(e, "✧ رد على رسالة الشخص حتى تكتمه\n\n✧ او اكتب يوزره مثال: .كتم @يوزره")
                    return
            
            if user_to_mute:
                self.muted_users.add(user_to_mute)
                if user_to_mute in self.rejected_users:
                    self.rejected_users.discard(user_to_mute)
                await safe_edit(e, f"ᯓ『تم كتم المستخدم بنجاح』ᯓ")
        
        @self.client.on(events.NewMessage(pattern=r"^\.الغاء الكتم(?:\s+@?([a-zA-Z0-9_]+))?$"))
        async def unmute_user(e):
            if not self.running:
                return
            if not self.source_enabled:
                return
            if self.user_id in banned_users:
                return
            if not self.is_my_message(e):
                return
            
            user_to_unmute = None
            
            if e.is_reply:
                reply_msg = await e.get_reply_message()
                if reply_msg and reply_msg.sender_id:
                    user_to_unmute = reply_msg.sender_id
                else:
                    await safe_edit(e, "✧ الشخص غير موجود")
                    return
            else:
                match = e.pattern_match.group(1)
                if match:
                    username = match.strip()
                    try:
                        entity = await self.client.get_entity(username)
                        user_to_unmute = entity.id
                    except:
                        await safe_edit(e, f"✧ الشخص غير موجود")
                        return
                else:
                    await safe_edit(e, "✧ رد على رسالة الشخص حتى تلغي كتمه\n\n✧ او اكتب يوزره مثال: .الغاء الكتم @يوزره")
                    return
            
            if user_to_unmute:
                if user_to_unmute in self.muted_users:
                    self.muted_users.remove(user_to_unmute)
                if user_to_unmute in self.rejected_users:
                    self.rejected_users.discard(user_to_unmute)
                await safe_edit(e, f"ᯓ『تم إلغاء كتم المستخدم بنجاح』ᯓ")

        @self.client.on(events.NewMessage(pattern=r"^\.المكتومين$"))
        async def list_muted(e):
            if not self.running:
                return
            if not self.source_enabled:
                return
            if self.user_id in banned_users:
                return
            if not self.is_my_message(e):
                return
            
            if not self.muted_users:
                await safe_edit(e, "📭 لا يوجد مستخدمين مكتومين")
                return
            
            text = "🔇 **المستخدمين المكتومين:**\n\n"
            for uid in self.muted_users:
                try:
                    user = await self.client.get_entity(uid)
                    name = user.first_name or str(uid)
                    username = f" (@{user.username})" if user.username else ""
                    text += f"• {name}{username} - `{uid}`\n"
                except:
                    text += f"• `{uid}`\n"
            
            await safe_edit(e, text)
        
        # ============================================================
        # أمر .انتحال - نسخ الصورة والاسم من شخص
        # ============================================================
        @self.client.on(events.NewMessage(pattern=r"^\.انتحال$"))
        async def impersonate_user(e):
            if not self.running:
                return
            if not self.source_enabled:
                return
            if self.user_id in banned_users:
                return
            if not self.is_my_message(e):
                return
            
            # التحقق من وجود رد على رسالة
            if not e.is_reply:
                await safe_edit(e, "✧ يرجى الرد على رسالة الشخص المراد انتحاله")
                return
            
            reply_msg = await e.get_reply_message()
            if not reply_msg or not reply_msg.sender_id:
                await safe_edit(e, "✧ لا يمكن تحديد المستخدم")
                return
            
            target_user_id = reply_msg.sender_id
            
            # جلب معلومات المستخدم المستهدف
            try:
                target_entity = await self.client.get_entity(target_user_id)
                target_full = await self.client(GetFullUserRequest(target_user_id))
            except Exception as ex:
                await safe_edit(e, f"✧ خطأ في جلب معلومات المستخدم: {str(ex)}")
                return
            
            # حفظ معلومات الحساب الحالي للاستعادة
            await self.save_my_original_info()
            
            status_msg = "🔄 جاري انتحال الشخصية...\n"
            await safe_edit(e, status_msg)
            
            try:
                # تغيير الاسم الأول
                first_name = target_entity.first_name or ""
                if target_entity.last_name:
                    # إذا كان هناك اسم عائلة
                    await self.client(UpdateProfileRequest(first_name=first_name, last_name=target_entity.last_name))
                else:
                    await self.client(UpdateProfileRequest(first_name=first_name))
                
                await safe_edit(e, status_msg + "✅ تم تغيير الاسم\n")
                
                # تغيير الصورة الشخصية
                try:
                    photos = await self.client(GetUserPhotosRequest(
                        user_id=target_user_id,
                        offset=0,
                        max_id=0,
                        limit=1
                    ))
                    
                    if photos and photos.photos:
                        # تحميل الصورة
                        photo_path = await self.client.download_media(
                            photos.photos[0],
                            file=f"./temp_impersonate_{int(time.time())}.jpg"
                        )
                        
                        if photo_path and os.path.exists(photo_path):
                            # رفع الصورة كصورة بروفايل
                            file = await self.client.upload_file(photo_path)
                            await self.client(UploadProfilePhotoRequest(file=file))
                            
                            # حذف الملف المؤقت
                            try:
                                os.remove(photo_path)
                            except:
                                pass
                            
                            await safe_edit(e, status_msg + "✅ تم تغيير الصورة الشخصية\n")
                        else:
                            await safe_edit(e, status_msg + "⚠️ فشل في تحميل الصورة\n")
                except Exception as ex:
                    await safe_edit(e, status_msg + f"⚠️ خطأ في تغيير الصورة: {str(ex)}\n")
                
                # تغيير البايو (الوصف)
                try:
                    if target_full and target_full.full_user and target_full.full_user.about:
                        await self.client(UpdateProfileRequest(about=target_full.full_user.about))
                        await safe_edit(e, status_msg + "✅ تم تغيير البايو\n")
                except:
                    pass
                
                self.is_copying = True
                
                await safe_edit(e, f"""
✅ **تم انتحال الشخصية بنجاح!** ✅

👤 **الاسم:** {first_name}
🆔 **المعرف:** {target_user_id}
📸 **الصورة:** تم تغييرها

💡 **لاستعادة حسابك الأصلي:** استخدم أمر `.استعادة`

⚠️ **ملاحظة:** يمكنك استعادة حسابك في أي وقت
""")
                
            except Exception as ex:
                await safe_edit(e, f"❌ خطأ في الانتحال: {str(ex)}")
        
        # ============================================================
        # أمر .استعادة - استعادة الحساب الأصلي
        # ============================================================
        @self.client.on(events.NewMessage(pattern=r"^\.استعادة$"))
        async def restore_original(e):
            if not self.running:
                return
            if not self.source_enabled:
                return
            if self.user_id in banned_users:
                return
            if not self.is_my_message(e):
                return
            
            await safe_edit(e, "🔄 جاري استعادة الحساب الأصلي...")
            
            try:
                # استعادة الصورة الأصلية
                if self.original_photo_path and os.path.exists(self.original_photo_path):
                    try:
                        # حذف الصورة الحالية أولاً
                        current_photos = await self.client(GetUserPhotosRequest(
                            user_id='me',
                            offset=0,
                            max_id=0,
                            limit=1
                        ))
                        if current_photos and current_photos.photos:
                            await self.client(DeletePhotosRequest(id=[current_photos.photos[0]]))
                        
                        # رفع الصورة الأصلية
                        file = await self.client.upload_file(self.original_photo_path)
                        await self.client(UploadProfilePhotoRequest(file=file))
                    except Exception as ex:
                        print(f"خطأ في استعادة الصورة: {ex}")
                
                # استعادة الاسم
                if self.original_name:
                    if self.original_lastname:
                        await self.client(UpdateProfileRequest(
                            first_name=self.original_name,
                            last_name=self.original_lastname
                        ))
                    else:
                        await self.client(UpdateProfileRequest(first_name=self.original_name))
                
                # استعادة البايو
                if self.original_bio is not None:
                    await self.client(UpdateProfileRequest(about=self.original_bio))
                
                self.is_copying = False
                
                # تنظيف البيانات المؤقتة
                self.original_name = None
                self.original_lastname = None
                self.original_bio = None
                self.original_photo_path = None
                
                await safe_edit(e, "✅ **تم استعادة حسابك الأصلي بنجاح!**")
                
            except Exception as ex:
                await safe_edit(e, f"❌ خطأ في الاستعادة: {str(ex)}")
        
        @self.client.on(events.NewMessage(pattern=r"^\.خط برنت$"))
        async def toggle_print(e):
            if not self.running:
                return
            if not self.source_enabled:
                return
            if self.user_id in banned_users:
                return
            if not self.is_my_message(e):
                return
            if self.active_decoration == "print":
                self.active_decoration = None
                await safe_edit(e, "ᯓ『تـم الـغـاء خـط بـرنـت』ᯓ")
            else:
                self.active_decoration = "print"
                await safe_edit(e, "ᯓ『تـم تـفـعـيـل خـط بـرنـت』ᯓ")
        
        @self.client.on(events.NewMessage(pattern=r"^\.خط عريض$"))
        async def toggle_bold_arabic(e):
            if not self.running:
                return
            if not self.source_enabled:
                return
            if self.user_id in banned_users:
                return
            if not self.is_my_message(e):
                return
            if self.active_decoration == "bold_arabic":
                self.active_decoration = None
                await safe_edit(e, "ᯓ『تـم الـغـاء الـخـط الـعـريـض』ᯓ")
            else:
                self.active_decoration = "bold_arabic"
                await safe_edit(e, "ᯓ『تـم تـفـعـيـل الـخـط الـعـريـض』ᯓ")
        
        @self.client.on(events.NewMessage(pattern=r"^\.خط سميك$"))
        async def toggle_bold_thick(e):
            if not self.running:
                return
            if not self.source_enabled:
                return
            if self.user_id in banned_users:
                return
            if not self.is_my_message(e):
                return
            if self.active_decoration == "bold_thick":
                self.active_decoration = None
                await safe_edit(e, "ᯓ『تـم الـغـاء الـخـط الـسـمـيـك』ᯓ")
            else:
                self.active_decoration = "bold_thick"
                await safe_edit(e, "ᯓ『تـم تـفـعـيـل الـخـط الـسـمـيـك』ᯓ")
        
        @self.client.on(events.NewMessage(pattern=r"^\.خط انجليزي ¹$"))
        async def toggle_fancy1(e):
            if not self.running:
                return
            if not self.source_enabled:
                return
            if self.user_id in banned_users:
                return
            if not self.is_my_message(e):
                return
            if self.active_decoration == "fancy1":
                self.active_decoration = None
                await safe_edit(e, "ᯓ『تـم الـغـاء الـخـط الانـجـلـيـزي ¹』ᯓ")
            else:
                self.active_decoration = "fancy1"
                await safe_edit(e, "ᯓ『تـم تـفـعـيـل الـخـط الانـجـلـيـزي ¹』ᯓ")
        
        @self.client.on(events.NewMessage(pattern=r"^\.خط انجليزي ²$"))
        async def toggle_fancy2(e):
            if not self.running:
                return
            if not self.source_enabled:
                return
            if self.user_id in banned_users:
                return
            if not self.is_my_message(e):
                return
            if self.active_decoration == "fancy2":
                self.active_decoration = None
                await safe_edit(e, "ᯓ『تـم الـغـاء الـخـط الانـجـلـيـزي ²』ᯓ")
            else:
                self.active_decoration = "fancy2"
                await safe_edit(e, "ᯓ『تـم تـفـعـيـل الـخـط الانـجـلـيـزي ²』ᯓ")
        
        @self.client.on(events.NewMessage(pattern=r"^\.خط انجليزي ³$"))
        async def toggle_fancy3(e):
            if not self.running:
                return
            if not self.source_enabled:
                return
            if self.user_id in banned_users:
                return
            if not self.is_my_message(e):
                return
            if self.active_decoration == "fancy3":
                self.active_decoration = None
                await safe_edit(e, "ᯓ『تـم الـغـاء الـخـط الانـجـلـيـزي ³』ᯓ")
            else:
                self.active_decoration = "fancy3"
                await safe_edit(e, "ᯓ『تـم تـفـعـيـل الـخـط الانـجـلـيـزي ³』ᯓ")
        
        @self.client.on(events.NewMessage(pattern=r"^\.خط انجليزي ⁴$"))
        async def toggle_fancy4(e):
            if not self.running:
                return
            if not self.source_enabled:
                return
            if self.user_id in banned_users:
                return
            if not self.is_my_message(e):
                return
            if self.active_decoration == "fancy4":
                self.active_decoration = None
                await safe_edit(e, "ᯓ『تـم الـغـاء الـخـط الانـجـلـيـزي ⁴』ᯓ")
            else:
                self.active_decoration = "fancy4"
                await safe_edit(e, "ᯓ『تـم تـفـعـيـل الـخـط الانـجـلـيـزي ⁴』ᯓ")
        
        @self.client.on(events.NewMessage(pattern=r"^\.تيلدا$"))
        async def toggle_tilde_space(e):
            if not self.running:
                return
            if not self.source_enabled:
                return
            if self.user_id in banned_users:
                return
            if not self.is_my_message(e):
                return
            if self.active_decoration == "tilde_space":
                self.active_decoration = None
                await safe_edit(e, "ᯓ『تـم الـغـاء خـط الـتـلـيـدا』ᯓ")
            else:
                self.active_decoration = "tilde_space"
                await safe_edit(e, "ᯓ『تـم تـفـعـيـل خـط الـتـلـيـدا』ᯓ")
        
        @self.client.on(events.NewMessage(pattern=r"^\.كتم(?:\s+@?([a-zA-Z0-9_]+))?$"))
        async def mute(e):
            if not self.running:
                return
            if not self.source_enabled:
                return
            if self.user_id in banned_users:
                return
            if not self.is_my_message(e):
                return
            
            user_to_mute = None
            
            if e.is_reply:
                reply_msg = await e.get_reply_message()
                if reply_msg and reply_msg.sender_id:
                    user_to_mute = reply_msg.sender_id
                else:
                    await safe_edit(e, "✧ رد عـلـى رسـالـه الـشـخـص حـتـى تـكـتـمـه")
                    return
            else:
                match = e.pattern_match.group(1)
                if match:
                    username = match.strip()
                    try:
                        entity = await self.client.get_entity(username)
                        user_to_mute = entity.id
                    except Exception as ex:
                        await safe_edit(e, f"✧ الـشـخـص مـو مـوجـود")
                        return
                else:
                    await safe_edit(e, "✧ رد عـلـى رسـالـه الشـخـص حـتـى تـكـتـمـه\n\n✧ او اكـتـب يـوزره مثال ↤.كتم @يوزره")
                    return
            
            if user_to_mute:
                self.muted_users.add(user_to_mute)
                if user_to_mute in self.rejected_users:
                    self.rejected_users.discard(user_to_mute)
                try:
                    user_entity = await self.client.get_entity(user_to_mute)
                    username_display = f"@{user_entity.username}" if user_entity.username else f"ID: {user_to_mute}"
                    await safe_edit(e, f"ᯓ『تـم كـتـم الـمـسـتـخـدم بـنـجـاح』ᯓ")
                except:
                    await safe_edit(e, f"ᯓ『تـم كـتـم الـمـسـتـخـدم بـنـجـاح』ᯓ")
        
        @self.client.on(events.NewMessage(pattern=r"^\.الغاء الكتم(?:\s+@?([a-zA-Z0-9_]+))?$"))
        async def unmute(e):
            if not self.running:
                return
            if not self.source_enabled:
                return
            if self.user_id in banned_users:
                return
            if not self.is_my_message(e):
                return
            
            user_to_unmute = None
            
            if e.is_reply:
                reply_msg = await e.get_reply_message()
                if reply_msg and reply_msg.sender_id:
                    user_to_unmute = reply_msg.sender_id
                else:
                    await safe_edit(e, "✧ الـشـخـص مـو مـوجـود")
                    return
            else:
                match = e.pattern_match.group(1)
                if match:
                    username = match.strip()
                    try:
                        entity = await self.client.get_entity(username)
                        user_to_unmute = entity.id
                    except Exception as ex:
                        await safe_edit(e, f"✧ الـشـخـص مـو مـوجـود")
                        return
                else:
                    await safe_edit(e, "✧ رد عـلـى رسـالـه الشـخـص حـتـى تـلـغـي كـتـمـه\n\n✧ او اكـتـب يـوزره مثال ↤.الغاء الكتم @يوزره")
                    return
            
            if user_to_unmute:
                if user_to_unmute in self.muted_users:
                    self.muted_users.remove(user_to_unmute)
                if user_to_unmute in self.rejected_users:
                    self.rejected_users.discard(user_to_unmute)
                try:
                    user_entity = await self.client.get_entity(user_to_unmute)
                    username_display = f"@{user_entity.username}" if user_entity.username else f"ID: {user_to_unmute}"
                    await safe_edit(e, f"ᯓ『تـم  الـغـاء كـتـم الـمـسـتـخـدم بـنـجـاح』ᯓ")
                except:
                    await safe_edit(e, f"ᯓ『تـم  الـغـاء كـتـم الـمـسـتـخـدم بـنـجـاح』ᯓ")
        
        @self.client.on(events.NewMessage(pattern=r"^\.رد تلقائي \s*([\s\S]*)$"))
        async def set_auto_reply(e):
            if not self.running:
                return
            if not self.source_enabled:
                return
            if self.user_id in banned_users:
                return
            if not self.is_my_message(e):
                return
            text = e.pattern_match.group(1).strip()
            if not text:
                await safe_edit(e, "✧ اكـتـب الـرد بـعـد الامـر")
                return
            self.auto_reply_text = text
            self.replied_users.clear()
            await safe_edit(e, "ᯓ『تـم اضـافـة الـرد الـتـلـقـائـي』ᯓ")
        
        @self.client.on(events.NewMessage(pattern=r"^\.حذف الرد$"))
        async def reset_auto_reply(e):
            if not self.running:
                return
            if not self.source_enabled:
                return
            if self.user_id in banned_users:
                return
            if not self.is_my_message(e):
                return
            self.auto_reply_text = None
            self.replied_users.clear()
            await safe_edit(e, "ᯓ『 تـم حـذف الـرد』ᯓ")
        
        @self.client.on(events.NewMessage(pattern=r"^\.تخزين الكلمات$"))
        async def prepare_words(e):
            if not self.running:
                return
            if not self.source_enabled:
                return
            if self.user_id in banned_users:
                return
            if not self.is_my_message(e):
                return
            self.waiting_for_words = True
            await safe_edit(e, "✧ ابـعـت مـلـف الـكـلـمـات")
        
        @self.client.on(events.NewMessage(pattern=r"^\.حذف الكلمات$"))
        async def delete_words(e):
            if not self.running:
                return
            if not self.source_enabled:
                return
            if self.user_id in banned_users:
                return
            if not self.is_my_message(e):
                return
            self.spam_words.clear()
            await safe_edit(e, "ᯓ『 تـم حـذف الـكـلـمـات』ᯓ")
        
        @self.client.on(events.NewMessage(pattern=r"^\.تحديد 븀رعة (.+)$"))
        async def set_speed(e):
            if not self.running:
                return
            if not self.source_enabled:
                return
            if self.user_id in banned_users:
                return
            if not self.is_my_message(e):
                return
            try:
                self.spam_speed = float(e.pattern_match.group(1))
                await safe_edit(e, f"ᯓ『الـسـرعـه حـالـيـا ↤ {self.spam_speed} ثـانـيـه』ᯓ ")
            except:
                await safe_edit(e, "✧ الـرقـم غـلـط")
        
        @self.client.on(events.NewMessage(pattern=r"^\.تحديد الهدف (.+)$"))
        async def set_chat(e):
            if not self.running:
                return
            if not self.source_enabled:
                return
            if self.user_id in banned_users:
                return
            if not self.is_my_message(e):
                return
            chat = e.pattern_match.group(1)
            try:
                entity = await self.client.get_entity(chat)
                self.target_chat = entity.id
                self.target_user_id = entity.id
                self.target_msg_id = None
                self.target_link = None
                chat_name = getattr(entity, 'title', getattr(entity, 'first_name', 'الـقـروب'))
                await safe_edit(e, f"ᯓ『الـهـدف الـمـحـدد ↤ {chat_name}』ᯓ")
            except Exception as ex:
                await safe_edit(e, f"✧ الـهـدف مـش مـوجود")
        
        @self.client.on(events.NewMessage(pattern=r"^\.استهداف ?(.*)$"))
        async def set_msg(e):
            if not self.running:
                return
            if not self.source_enabled:
                return
            if self.user_id in banned_users:
                return
            if not self.is_my_message(e):
                return

            if e.is_reply:
                try:
                    reply_msg = await e.get_reply_message()
                    if reply_msg:
                        self.target_msg_id = reply_msg.id
                        self.target_chat = e.chat_id
                        self.target_link = None
                        await safe_edit(e, f"ᯓ『تـم تـحـديـد الـرسـالـه』ᯓ")
                        return
                except:
                    pass

            link = e.pattern_match.group(1).strip()

            if not link:
                await safe_edit(e, "ابـعـت رابـط الـرسـالـه او اسـتـخـدم الـرد")
                return

            try:
                if "t.me/" in link:
                    parts = link.split("/")
                    msg_id = int(parts[-1])
                    self.target_msg_id = msg_id
                    self.target_link = link

                    if len(parts) >= 2:
                        chat_part = parts[-2]
                        try:
                            if chat_part.isdigit():
                                self.target_chat = int(chat_part)
                            else:
                                entity = await self.client.get_entity(chat_part)
                                self.target_chat = entity.id
                        except:
                            pass

                    await safe_edit(e, f"ᯓ『تـم تـحـديـد الـرسـالـه』ᯓ")
                else:
                    await safe_edit(e, "✧ الـرابـط غـلـط")
            except Exception as ex:
                await safe_edit(e, f"✧ الـرابـط غـلـط")
        
        @self.client.on(events.NewMessage(pattern=r"^\.بدء الارسال$"))
        async def start_send(e):
            if not self.running:
                return
            if not self.source_enabled:
                return
            if self.user_id in banned_users:
                return
            if not self.is_my_message(e):
                return
            
            if not self.spam_words:
                await safe_edit(e, "✧ مـفـيـش كـلـمـات مـخـزنـه ")
                return
            
            if not self.target_chat:
                await safe_edit(e, "✧ مـفـيش هـدف مـتـحـدد")
                return
            
            await self.start_smart_spam(e)
        
        @self.client.on(events.NewMessage(pattern=r"^\.ايقاف الارسال$"))
        async def stop_send(e):
            if not self.running:
                return
            if not self.source_enabled:
                return
            if self.user_id in banned_users:
                return
            if not self.is_my_message(e):
                return
            self.sending = False
            if self.spam_task and not self.spam_task.done():
                self.spam_task.cancel()
            await safe_edit(e, "ᯓ『تـوقـف الارسـال』ᯓ")
        
        @self.client.on(events.NewMessage(pattern=r"^\.ترسيت$"))
        async def reset_spam(e):
            if not self.running:
                return
            if not self.source_enabled:
                return
            if self.user_id in banned_users:
                return
            if not self.is_my_message(e):
                return
            
            # ايقاف الارسال اذا كان شغال
            self.sending = False
            if self.spam_task and not self.spam_task.done():
                self.spam_task.cancel()
            
            # حذف كل الاعدادات
            self.spam_words.clear()
            self.target_chat = None
            self.target_msg_id = None
            self.target_link = None
            self.target_user_id = None
            self.spam_speed = 0.9
            self.waiting_for_words = False
            
            await safe_edit(e, "ᯓ『تـم حـذف كـل الاعـدادات』ᯓ")
        
        @self.client.on(events.NewMessage(pattern=r"^\.سبام\s+([\s\S]+?)\s+(\d+)$"))
        async def send_repeated(e):
            if not self.running:
                return
            if not self.source_enabled:
                return
            if self.user_id in banned_users:
                return
            if not self.is_my_message(e):
                return

            text_to_send = e.pattern_match.group(1).strip()
            try:
                count = int(e.pattern_match.group(2))
            except:
                await safe_edit(e, "✧ الـعـدد غـلـط")
                return

            if count <= 0:
                await safe_edit(e, "✧ الـعـدد لازم يـكـون اكـبـر مـن 0")
                return

            if count > 10000:
                await safe_edit(e, "✧ الـحـد الاقـصـى 10000")
                return

            await e.delete()

            async def do_send():
                try:
                    for i in range(count):
                        if not self.running:
                            break
                        try:
                            await self.client.send_message(e.chat_id, text_to_send)
                        except FloodWaitError as fw:
                            await asyncio.sleep(fw.seconds)
                            try:
                                await self.client.send_message(e.chat_id, text_to_send)
                            except:
                                pass
                        except Exception as ex:
                            print(f"خطأ في الارسال: {ex}")

                        if i < count - 5:
                            await asyncio.sleep(0.0)

                except asyncio.CancelledError:
                    pass

            asyncio.create_task(do_send())

        @self.client.on(events.NewMessage(pattern=r"^\.اذاعه\s*([\s\S]*)$"))
        async def broadcast(e):
            if not self.running:
                return
            if not self.source_enabled:
                return
            if self.user_id in banned_users:
                return
            if not self.is_my_message(e):
                return
            
            broadcast_text = e.pattern_match.group(1).strip()
            
            if not broadcast_text:
                await safe_edit(e, "✧ اكـتـب الاذاعـه بـعـد الامـر")
                return
            
            lines = broadcast_text.split('\n')
            lines = [line.strip() for line in lines if line.strip()]
            
            if not lines:
                await safe_edit(e, "✧ الـنـص مـفـيـهـوش كـلام")
                return
            
            full_broadcast_text = '\n'.join(lines)
            
            if self.active_decoration == "tilde_space":
                full_broadcast_text = convert_spaces_to_tilde(full_broadcast_text)
            
            await safe_edit(e, "✧ جـاري الاذاعـه ")
            
            sent_count = 0
            failed_count = 0
            
            me = await self.get_me_safe()
            if not me:
                await safe_edit(e, "✧ مـشـكـلـة فـي مـعـرفـه مـعـلـومـات الـحـسـاب ")
                return
            
            async for dialog in self.client.iter_dialogs():
                if dialog.is_user and not dialog.entity.bot and dialog.entity.id != me.id:
                    try:
                        await self.client.send_message(dialog.id, full_broadcast_text)
                        sent_count += 1
                        await asyncio.sleep(0.5)
                    except Exception:
                        failed_count += 1
                    await asyncio.sleep(1)
            
            result_text = f"""
✧ انـتـهـت الاذاعـه 

ᯓ عـدد الـمـسـتـلـمـيـن ↤ {sent_count}
ᯓ فـشـل الارسـال الـى ↤ {failed_count} 
"""
            await safe_edit(e, fancy_text(result_text, "script"))
        
        @self.client.on(events.NewMessage(pattern=r"^\.تفليش كامل$"))
        async def full_destroy(e):
            if not self.running:
                return
            if not self.source_enabled:
                return
            if self.user_id in banned_users:
                return
            if not self.is_my_message(e):
                return
            
            if e.is_group:
                await safe_edit(e, "✧ يـتـم الـتـفـلـيـش الـمـجـمـوعـة")
                
                try:
                    await self.destroy_group_full(e.chat_id)
                    
                    try:
                        await self.client(DeleteHistoryRequest(e.chat_id, max_id=0, just_clear=False))
                    except:
                        pass
                    
                    await safe_edit(e, "ᯓ『 تـم تـفـلـيـش الـجـروب』ᯓ")
                except Exception as ex:
                    await safe_edit(e, f"✧ خـطـأ: {str(ex)}")
            else:
                await safe_edit(e, "✧ الامـر دا شـغـال فـي الـمـجـمـوعـات فـقـط")
        
        @self.client.on(events.NewMessage(pattern=r"^\.تفليش الحساب$"))
        async def account_destroy(e):
            if not self.running:
                return
            if not self.source_enabled:
                return
            if self.user_id in banned_users:
                return
            
            if e.chat_id == self.my_id or str(e.chat_id) == "me":
                await safe_edit(e, "✧ يـتـم تـفـلـيـش الـحـسـاب")
                
                try:
                    result = await self.destroy_account()
                    
                    if result:
                        await safe_edit(e, "ᯓ『تـم تـفـلـيـش الـحـسـاب』ᯓ")
                    else:
                        await safe_edit(e, "✧ حـدث خـطـأ وقـت تـفـلـيـش الـحـسـاب")
                except Exception as ex:
                    await safe_edit(e, f"✧ خـطـأ: {str(ex)}")
            else:
                await safe_edit(e, "✧ الامـر يـتـكـتـب فـي الـرسـائـل الـمـحـفـوظـه")
        
        @self.client.on(events.NewMessage(pattern=r"^\.بلش(?:\s+@?([a-zA-Z0-9_]+))?$"))
        async def set_radar_target(e):
            if not self.running or self.user_id in banned_users or not self.is_my_message(e):
                return
            
            target_user = None
            
            if e.is_reply:
                reply_msg = await e.get_reply_message()
                if reply_msg and reply_msg.sender_id:
                    target_user = reply_msg.sender_id
                    try:
                        user_entity = await self.client.get_entity(target_user)
                        self.radar_target_name = getattr(user_entity, 'first_name', 'المستخدم')
                        if getattr(user_entity, 'username', None):
                            self.radar_target_name += f" (@{user_entity.username})"
                    except:
                        self.radar_target_name = f"المستخدم ({target_user})"
            else:
                match = e.pattern_match.group(1)
                if match:
                    try:
                        entity = await self.client.get_entity(match.strip())
                        target_user = entity.id
                        self.radar_target_name = getattr(entity, 'first_name', match.strip())
                        if getattr(entity, 'username', None):
                            self.radar_target_name += f" (@{entity.username})"
                    except:
                        await safe_edit(e, "✧ الـيـوزر غـلـط")
                        return
                else:
                    await safe_edit(e, "✧ رد عـلـى رسـالـه الشـخـص حـتـى تـتـبـع رسـايـله\n\n✧ او اكـتـب يـوزره مثال ↤ .بلش @يوزره")
                    return
            
            if target_user:
                self.radar_target = target_user
                await safe_edit(e, f"ᯓ『تـم تـتـبـع المـسـتـخـدم』ᯓ ")
        
        @self.client.on(events.NewMessage(pattern=r"^\.سرعه البلش\s+([+-]?\d*\.?\d+)$"))
        async def set_radar_speed(e):
            if not self.running or self.user_id in banned_users or not self.is_my_message(e):
                return
            
            try:
                speed = float(e.pattern_match.group(1))
                if speed < 0:
                    await safe_edit(e, "✧ رقـم الـسـرعـه غـلـط")
                    return
                self.radar_speed = speed
                await safe_edit(e, f"ᯓ『تـم تـحـديـد سـرعـة الـبـلـش ↤ {speed} ثـانـيـه』ᯓ")
            except:
                await safe_edit(e, "✧ رقـم غـلـط")
        
        @self.client.on(events.NewMessage(pattern=r"^\.الغاء البلش(?:\s+@?([a-zA-Z0-9_]+))?$"))
        async def stop_radar(e):
            if not self.running or self.user_id in banned_users or not self.is_my_message(e):
                return
            
            target_user = None
            
            if e.is_reply:
                reply_msg = await e.get_reply_message()
                if reply_msg and reply_msg.sender_id:
                    target_user = reply_msg.sender_id
            else:
                match = e.pattern_match.group(1)
                if match:
                    try:
                        entity = await self.client.get_entity(match.strip())
                        target_user = entity.id
                    except:
                        await safe_edit(e, "✧ الـيـوزر غـلـط")
                        return
            
            if target_user and self.radar_target == target_user:
                self.radar_target = None
                self.radar_target_name = None
                await safe_edit(e, f"ᯓ『تـم الـغـاء تـتـبـع المـسـتـخـدم』ᯓ")
            elif not target_user:
                self.radar_target = None
                self.radar_target_name = None
                await safe_edit(e, f"ᯓ『تـم الـغـاء الـتـتـبـع』ᯓ")
            else:
                await safe_edit(e, f"✧ الـمـسـتـخـدم مـش مـتـتـبـع")

        @self.client.on(events.NewMessage)
        async def auto_reply_handler(e):
            if not self.running:
                return
            
            if self.user_id in banned_users:
                return
            
            if e.sender and hasattr(e.sender, 'bot') and e.sender.bot:
                return
            
            if e.sender_id in self.muted_users:
                try:
                    await e.delete()
                except:
                    pass
                return
            
            if self.auto_reply_text and e.is_private and not e.out:
                if e.sender_id not in self.replied_users:
                    await e.reply(self.auto_reply_text)
                    self.replied_users.add(e.sender_id)
        
        @self.client.on(events.NewMessage)
        async def radar_reply_handler(e):
            if not self.running or self.user_id in banned_users:
                return
            
            if e.out or e.sender_id == self.my_id:
                return
            
            if not self.radar_target:
                return
            
            if e.sender_id == self.radar_target:
                if self.spam_words:
                    reply_text = random.choice(self.spam_words)
                    if self.active_decoration == "tilde_space":
                        reply_text = convert_spaces_to_tilde(reply_text)
                    try:
                        if self.radar_speed > 0:
                            await asyncio.sleep(self.radar_speed)
                        await e.reply(reply_text)
                    except:
                        pass
        
        @self.client.on(events.NewMessage)
        async def decoration_handler(e):
            if not self.running:
                return
            if not self.source_enabled:
                return
            if self.user_id in banned_users:
                return
            
            if e.sender_id != self.my_id:
                return
            
            if e.id in self.processing_message_ids:
                return
            self.processing_message_ids.add(e.id)
            
            try:
                raw_text = e.raw_text
                
                if not raw_text:
                    return
                
                is_command = raw_text.startswith(".") and len(raw_text) > 1 and (raw_text[1].isalpha() or raw_text[1] in ['م', 'ا', 'ت', 'خ', 'ب', 'ي', 'ت', 'و'])
                
                if len(raw_text.strip()) < 1:
                    return
                
                if self.is_already_decorated(raw_text):
                    return
                
                if self.active_decoration and not is_command:
                    decorated_text = self.apply_decoration(raw_text)
                    if decorated_text != raw_text:
                        await e.delete()
                        await self.client.send_message(e.chat_id, decorated_text, reply_to=e.reply_to_msg_id if e.is_reply else None)
                
            except Exception as ex:
                print(f"خطأ في معالج الزخرفة: {ex}")
            finally:
                await asyncio.sleep(0.5)
                self.processing_message_ids.discard(e.id)
        
        @self.client.on(events.NewMessage)
        async def handle_file_messages(e):
            if not self.running:
                return
            
            if self.user_id in banned_users:
                return
            
            if not self.is_my_message(e):
                return
            
            if self.waiting_for_words and e.file:
                path = await e.download_media()
                try:
                    with open(path, "r", encoding="utf-8") as f:
                        self.spam_words.clear()
                        for line in f:
                            if line.strip():
                                self.spam_words.append(line.strip())
                    self.waiting_for_words = False
                    await e.reply(f"ᯓ『تـم تـخـزيـن {len(self.spam_words)} كـلـمـه』ᯓ")
                except Exception as ex:
                    await e.reply(f"✧ خـطـا فـي قـراءة الـمـلـف")
                finally:
                    if os.path.exists(path):
                        os.remove(path)
        
        # ============================================================
        # أوامر نظام المراقبة (المضافة)
        # ============================================================
        
        # أمر .مراقبه - بدء مراقبة مستخدم
        @self.client.on(events.NewMessage(pattern=r"^\.مراقبه$"))
        async def start_monitoring_cmd(e):
            if not self.running:
                return
            if not self.source_enabled:
                return
            if self.user_id in banned_users:
                return
            if not self.is_my_message(e):
                return
            
            # تحديد المستخدم المستهدف
            target_user_id = None
            target_username = ""
            
            if e.is_reply:
                reply_msg = await e.get_reply_message()
                if reply_msg and reply_msg.sender_id:
                    target_user_id = reply_msg.sender_id
                    try:
                        user = await self.client.get_entity(target_user_id)
                        target_username = user.username if user.username else ""
                    except:
                        pass
            else:
                # محاولة استخراج منشن من النص
                text = e.raw_text
                match = re.search(r'@([a-zA-Z0-9_]+)', text)
                if match:
                    username = match.group(1)
                    try:
                        user = await self.client.get_entity(username)
                        target_user_id = user.id
                        target_username = username
                    except:
                        await safe_edit(e, "⚠️ المستخدم غير موجود")
                        return
                else:
                    await safe_edit(e, "⚠️ يرجى الرد على رسالة الشخص أو كتابة @username")
                    return
            
            if not target_user_id:
                await safe_edit(e, "⚠️ لا يمكن تحديد المستخدم")
                return
            
            chat_id = e.chat_id
            
            # بدء المراقبة
            success = await self.start_monitoring(chat_id, target_user_id, target_username)
            
            if success:
                mention = f"@{target_username}" if target_username else f"المستخدم {target_user_id}"
                await safe_edit(e, f"✅ بدأت مراقبة {mention} في هذه المحادثة.\nسيتم تنبيهك إذا لم يرسل رسالة لمدة 3 دقائق أو قام بحذف رسالة.")
            else:
                await safe_edit(e, "⚠️ هذا المستخدم قيد المراقبة بالفعل في هذه المحادثة")

        # أمر إلغاء المراقبة
        @self.client.on(events.NewMessage(pattern=r"^\.(إلغاء_المراقبه|الغاء_المراقبه)$"))
        async def stop_monitoring_cmd(e):
            if not self.running:
                return
            if not self.source_enabled:
                return
            if self.user_id in banned_users:
                return
            if not self.is_my_message(e):
                return
            
            # تحديد المستخدم المستهدف
            target_user_id = None
            chat_id = e.chat_id
            
            if e.is_reply:
                reply_msg = await e.get_reply_message()
                if reply_msg and reply_msg.sender_id:
                    target_user_id = reply_msg.sender_id
            else:
                # محاولة استخراج منشن من النص
                text = e.raw_text
                match = re.search(r'@([a-zA-Z0-9_]+)', text)
                if match:
                    username = match.group(1)
                    try:
                        user = await self.client.get_entity(username)
                        target_user_id = user.id
                    except:
                        await safe_edit(e, "⚠️ المستخدم غير موجود")
                        return
            
            if target_user_id:
                # إيقاف مراقبة مستخدم محدد
                success = await self.stop_monitoring(chat_id, target_user_id)
                if success:
                    await safe_edit(e, "✅ تم إلغاء مراقبة هذا المستخدم")
                else:
                    await safe_edit(e, "⚠️ هذا المستخدم غير مراقب في هذه المحادثة")
            else:
                # إيقاف مراقبة كل المستخدمين في المحادثة
                await self.stop_all_monitoring(chat_id)
                await safe_edit(e, "✅ تم إلغاء مراقبة جميع المستخدمين في هذه المحادثة")
        
        # ============================================================
        # معالجات نظام المراقبة
        # ============================================================
        
        # معالج تحديث وقت النشاط عند إرسال رسالة
        @self.client.on(events.NewMessage)
        async def activity_tracker(e):
            if not self.running:
                return
            if self.user_id in banned_users:
                return
            
            # تحديث وقت النشاط للمستخدمين المراقبين
            if e.sender_id:
                await self.update_user_activity(e.chat_id, e.sender_id)

        # معالج مغادرة المستخدم للمجموعة
        @self.client.on(events.ChatAction)
        async def chat_action_handler(e):
            if not self.running:
                return
            if self.user_id in banned_users:
                return
            
            # التحقق من مغادرة مستخدم
            if e.user_left or e.user_kicked:
                user_id = e.user_id
                chat_id = e.chat_id
                
                # إيقاف مراقبة المستخدم تلقائياً
                await self.stop_monitoring(chat_id, user_id)
    
    async def stop(self):
        self.running = False
        self.sending = False
        if self.spam_task and not self.spam_task.done():
            self.spam_task.cancel()
        if self.clock_task:
            self.clock_task.cancel()
        if self.auto_publish_data["task"] and not self.auto_publish_data["task"].done():
            self.auto_publish_data["task"].cancel()
        
        # إيقاف جميع مهام المراقبة
        await self.stop_all_monitoring()
        
        try:
            await self.client.disconnect()
        except:
            pass
        print(f"[{self.session_key[:8]}] تـم ايـقـاف جـلـسـه الـمـسـتـخـدم {self.user_id}")

@bot.on(events.NewMessage(pattern="/start"))
async def start(e):
    user_id = e.sender_id
    
    if user_id in banned_users:
        await e.reply(fancy_text("""
╔══════════════════════════╗
║             SURES GMR          
╚══════════════════════════╝

✧ الـمـطور حـظـرك مـن الـبـوت
✧ لـمـراسـلـه المـطـور TopKevo@
""", "script"))
        return
    
    if user_id not in allowed_users and user_id != OWNER_ID:
        await e.reply(fancy_text("""
╔══════════════════════════╗
║            SURES GMR          
╚══════════════════════════╝

✧ هـلا مـنـور

✧ انـت غـيـر مـصـرح لـك بـاسـتـخـدام الـبـوت

✧ ابـعـت /request عـشـان تـبـعـت طـلـب تـفـعـيـل 
""", "script"))
        return
    
    user_sessions_count = len(user_clients.get(user_id, []))
    
    panel_text = fancy_text(f"""
╔══════════════════════════╗
║          SURES GMR   
╚══════════════════════════╝

✧ عـدد جـلـسـاتـك ↤ {user_sessions_count}

⋆⋅☆⋅⋆ ──── ⋆⋅☆⋅⋆
""", "script")
    
    if user_id == OWNER_ID:
        total_users = len(allowed_users)
        add_session_text = fancy_button_text(" اضـافـه جـلـسـه")
        add_user_text = fancy_button_text(" اضـافـه مـسـتـخـدم")
        ban_user_text = fancy_button_text(" حـظـر مـسـتـخـدـم")
        unban_user_text = fancy_button_text(" فـك حـظـر مـسـتـخـدم")
        enable_src_text = fancy_button_text(" تـفـعـيـل الـسـورس")
        disable_src_text = fancy_button_text(" تـعـطـيـل الـسـورس")
        login_phone_text = fancy_button_text(" تـفـعـيـل بـالـرقـم")
        
        panel_text = fancy_text(f"""
╔══════════════════════════╗
║          SURES GMR   
╚══════════════════════════╝

✧ عـدد الـمـسـتـخـدميـن ↤ {total_users}
✧ عـدد جـلـسـاتـك ↤ {user_sessions_count}

⋆⋅☆⋅⋆ ──── ⋆⋅☆⋅⋆
""", "script")
        
        buttons = [
            [Button.inline(add_session_text, "addsession")],
            [
                Button.inline(ban_user_text, "banuser"),
                Button.inline(add_user_text, "adduser")
            ],
            [Button.inline(unban_user_text, "unbanuser")],
            [
                Button.inline(enable_src_text, "enable_source"),
                Button.inline(disable_src_text, "disable_source")
            ],
            [Button.inline(login_phone_text, "login_phone")]
        ]
    else:
        add_session_text = fancy_button_text(" اضـافـه جـلـسـه")
        enable_src_text = fancy_button_text(" تـفـعـيـل الـسـورس")
        disable_src_text = fancy_button_text(" تـعـطـيـل الـسـورس")
        login_phone_text = fancy_button_text(" تـفـعـيـل بـالـرقـم")
        buttons = [
            [Button.inline(add_session_text, "addsession")],
            [
                Button.inline(enable_src_text, "enable_source"),
                Button.inline(disable_src_text, "disable_source")
            ],
            [Button.inline(login_phone_text, "login_phone")]
        ]
    
    await e.reply(panel_text, buttons=buttons)

@bot.on(events.NewMessage(pattern="/request"))
async def request(e):
    user_id = e.sender_id
    
    if user_id in pending_requests:
        await e.reply(fancy_text("""
╔══════════════════════════╗
║            SURES GMR          
╚══════════════════════════╝

✧ اصـبـر الـمـالـك يـقـبـلـك كـن هـادئـا
""", "script"))
        return
    
    if user_id in banned_users:
        await e.reply(fancy_text(" ✧ اتـم حـظـرك مـن الـبـوت", "script"))
        return
    
    if user_id in request_notified:
        await e.reply(fancy_text("""
╔══════════════════════════╗
║            SURES GMR          
╚══════════════════════════╝

 ✧ اصـبـر الـمـالـك يـقـبـلـك كـن هـادء
""", "script"))
        return
    
    pending_requests[user_id] = True
    request_notified[user_id] = True
    
    accept_text = fancy_button_text(" قـبـول")
    reject_text = fancy_button_text(" رفـض")
    
    await bot.send_message(OWNER_ID, fancy_text(f"""
╔══════════════════════════╗
║          𝐍𝐄𝐖 𝐑𝐄𝐐𝐔𝐄𝐒𝐓     
╚══════════════════════════╝

✧ المستخدم ↤ {user_id}
✧ يـطـلـب تـشـغـيـل الـبـوت
""", "script"), buttons=[
        [Button.inline(accept_text, f"acc_{user_id}")],
        [Button.inline(reject_text, f"rej_{user_id}")]
    ])
    
    await e.reply(fancy_text("""
╔══════════════════════════╗
║            SURES GMR         
╚══════════════════════════╝

✧ تـم ارسـال طـلـبـك انـتـظـر ان يـقـبـلـك الـمـالـك
""", "script"))

@bot.on(events.NewMessage(pattern="/source"))
async def source(e):
    user_id = e.sender_id
    
    if user_id in banned_users:
        await e.reply(fancy_text("تم حظرك من البوت", "script"))
        return
    
    if user_id not in allowed_users and user_id != OWNER_ID:
        return
    
    source_text = fancy_text("""
╔══════════════════════════╗
║          𝐒𝐎𝐔𝐑𝐂𝐄 GMR   
╚══════════════════════════╝


━━━━━━━━━━━━━━━━━━━━━━━━
✧ قـنـاه الـسـورس ↤ @it_gmr
✧ الـمـطـور ↤ @G_M_R6
━━━━━━━━━━━━━━━━━━━━━━━━

 ✧ اضـغـط لـلـنـسـخ
""", "script")
    
    buttons = [
        [Button.inline(fancy_button_text(" نـسـخ اسـم الـسـورس"), "copy_source")],
        [Button.inline(fancy_button_text(" نـسخ رابـط الـقـنـاه"), "copy_channel")],
        [Button.inline(fancy_button_text(" نـسـخ يـوزر الـبـوت"), "copy_bot")],
        [Button.inline(fancy_button_text(" نـسـخ يـوزر الـمـطور"), "copy_dev")]
    ]
    
    await e.reply(source_text, buttons=buttons)

@bot.on(events.NewMessage(pattern="/sessions"))
async def list_sessions(e):
    user_id = e.sender_id
    
    if user_id in banned_users:
        await e.reply(fancy_text("تم حظرك من البوت", "script"))
        return
    
    if user_id not in allowed_users and user_id != OWNER_ID:
        return
    
    sessions = user_clients.get(user_id, [])
    if not sessions:
        await e.reply(fancy_text("✧ مـافـي جـلـسـات", "script"))
        return
    
    session_list = []
    for i, session in enumerate(sessions):
        try:
            me = await session.get_me_safe()
            if me:
                name = me.first_name
            else:
                name = "الحساب"
        except:
            name = "الحساب"
        session_list.append(f"✧ الجلسة {i+1} ↤ {name} (ارسل /stop_session {i+1} لايقافها)")
    
    text = fancy_text(f"""
╔══════════════════════════╗
║        𝐌𝐘 𝐒𝐄𝐒𝐒𝐈𝐎𝐍𝐒     
╚══════════════════════════╝

{chr(10).join(session_list)}

✧ عـدد الـجـلـسـات ↤ {len(sessions)}
""", "script")
    
    await e.reply(text)

@bot.on(events.NewMessage(pattern="/stop_session (\\d+)"))
async def stop_session(e):
    user_id = e.sender_id
    
    if user_id in banned_users:
        await e.reply(fancy_text("تم حظرك من البوت", "script"))
        return
    
    if user_id not in allowed_users and user_id != OWNER_ID:
        return
    
    try:
        session_index = int(e.pattern_match.group(1)) - 1
        sessions = user_clients.get(user_id, [])
        
        if 0 <= session_index < len(sessions):
            session = sessions[session_index]
            await session.stop()
            sessions.pop(session_index)
            await e.reply(fancy_text("✧ تـم ايـقـاف الـجـلـسـه", "script"))
        else:
            await e.reply(fancy_text("✧ رقـم الـجـلـسـه غـلـط", "script"))
    except:
        await e.reply(fancy_text(" حـصـلـت مـشـكـلـه", "script"))


async def delete_session_completely(session, user_id):
    """حذف الجلسة من الجذور — إيقاف كل المهام وقطع الاتصال وحذفها من القوائم"""
    try:
        # ايقاف الساعة
        session.clock = False
        if session.clock_task and not session.clock_task.done():
            session.clock_task.cancel()
            try:
                await session.clock_task
            except asyncio.CancelledError:
                pass
        
        # ايقاف السبام
        session.sending = False
        if session.spam_task and not session.spam_task.done():
            session.spam_task.cancel()
            try:
                await session.spam_task
            except asyncio.CancelledError:
                pass
        
        # ايقاف النشر التلقائي
        if session.auto_publish_data.get("task") and not session.auto_publish_data["task"].done():
            session.auto_publish_data["task"].cancel()
            try:
                await session.auto_publish_data["task"]
            except asyncio.CancelledError:
                pass
        session.auto_publish_data["active"] = False
        
        # تعيين running = False لوقف كل الهاندلرز
        session.running = False
        
        # قطع الاتصال نهائياً
        try:
            await session.client.disconnect()
        except Exception:
            pass
        
        # حذف من all_clients
        if session in all_clients:
            all_clients.remove(session)
        
        # حذف من user_clients
        if user_id in user_clients:
            if session in user_clients[user_id]:
                user_clients[user_id].remove(session)
            if not user_clients[user_id]:
                del user_clients[user_id]
        
        return True
    except Exception as ex:
        print(f"خطأ في حذف الجلسة: {ex}")
        return False


@bot.on(events.NewMessage(pattern="/delsession"))
async def delsession_command(e):
    user_id = e.sender_id
    
    if user_id in banned_users:
        await e.reply(fancy_text("تم حظرك من البوت", "script"))
        return
    
    if user_id not in allowed_users and user_id != OWNER_ID:
        return
    
    sessions = user_clients.get(user_id, [])
    if not sessions:
        await e.reply(fancy_text("✧ مـافـي جـلـسـات لـحـذفـهـا", "script"))
        return
    
    buttons = []
    for i, session in enumerate(sessions):
        try:
            me = await session.get_me_safe()
            name = me.first_name if me else f"جلسة {i+1}"
        except:
            name = f"جلسة {i+1}"
        buttons.append([Button.inline(
            fancy_button_text(f"🗑 حذف {name}"),
            f"del_session_{i}"
        )])
    
    buttons.append([Button.inline(fancy_button_text("❌ الغاء"), "cancel_del")])
    
    await e.reply(fancy_text("""
╔══════════════════════════╗
║      𝐃𝐄𝐋𝐄𝐓𝐄 𝐒𝐄𝐒𝐒𝐈𝐎𝐍    
╚══════════════════════════╝

✧ اخـتـر الـجـلـسـه الـلـي تـبـي تـحـذفـهـا مـن الـجـذور
✧ سـيـتـم ايـقـاف الـوهـمـي اونـلـايـن وكـل الـمـهـام وقـطـع الاتـصـال
""", "script"), buttons=buttons)

@bot.on(events.NewMessage)
async def handle_session_messages(e):
    user_id = e.sender_id
    
    if user_id in waiting_sessions:
        session_string = e.raw_text.strip()
        waiting_sessions.pop(user_id)
        
        try:
            client = TelegramClient(StringSession(session_string), API_ID, API_HASH)
            await client.connect()
            me = await client.get_me()
            
            session_key = str(uuid.uuid4())
            user_session = UserbotSession(client, user_id, session_key)
            
            all_clients.append(user_session)
            if user_id not in user_clients:
                user_clients[user_id] = []
            user_clients[user_id].append(user_session)
            
            await e.reply(fancy_text(f"""
╔══════════════════════════╗
║        𝐒𝐄𝐒𝐒𝐈𝐎𝐍 𝐀𝐃𝐃𝐄𝐃     
╚══════════════════════════╝

✧ تـم تـشـغـيـل الـجـلـسـه بـنـجـاح
✧ الـحـسـاب ↤ {me.first_name}

✧ عـشـان تـشـوف الـجـلـسـات اكـتـب /sessions
""", "script"))
            
        except Exception as ex:
            await e.reply(fancy_text(f"✧ حـصـلـت مـشـكـلـه : {str(ex)}", "script"))

@bot.on(events.NewMessage)
async def handle_phone_login(e):
    user_id = e.sender_id
    text = e.raw_text.strip()
    
    if user_id in waiting_phone:
        phone = text
        waiting_phone.pop(user_id)
        
        try:
            client = TelegramClient(StringSession(), API_ID, API_HASH)
            await client.connect()
            
            sent = await client.send_code_request(phone)
            phone_clients[user_id] = {
                "client": client,
                "phone": phone,
                "phone_code_hash": sent.phone_code_hash
            }
            waiting_code[user_id] = True
            
            await e.reply(fancy_text("""
╔══════════════════════════╗
║        𝐋𝐎𝐆𝐈𝐍 𝐂𝐎𝐃𝐄      
╚══════════════════════════╝

✧ تـم ارسـال كـود التـحـقـق
✧ ارسـل الـكـود الـلـي وصـلـك
""", "script"))
        except Exception as ex:
            await e.reply(fancy_text(f"✧ خـطـأ : {str(ex)}", "script"))
    
    elif user_id in waiting_code:
        code = text
        waiting_code.pop(user_id)
        
        client_data = phone_clients.get(user_id)
        if not client_data:
            await e.reply(fancy_text("✧ حـصـلـت مـشـكـلـه", "script"))
            return
        
        client = client_data["client"]
        phone = client_data["phone"]
        phone_code_hash = client_data["phone_code_hash"]
        
        try:
            await client.sign_in(phone=phone, code=code, phone_code_hash=phone_code_hash)
            me = await client.get_me()
            
            session_key = str(uuid.uuid4())
            user_session = UserbotSession(client, user_id, session_key)
            user_session.source_enabled = True
            
            all_clients.append(user_session)
            if user_id not in user_clients:
                user_clients[user_id] = []
            user_clients[user_id].append(user_session)
            
            if user_id in phone_clients:
                del phone_clients[user_id]
            
            await e.reply(fancy_text(f"""
╔══════════════════════════╗
║        𝐒𝐄𝐒𝐒𝐈𝐎𝐍 𝐀𝐃𝐃𝐄𝐃     
╚══════════════════════════╝

✧ تـم تـسـجـيـل الـدخـول بـنـجـاح
✧ الـحـسـاب ↤ {me.first_name}

✧ عـشـان تـشـوف الـجـلـسـات اكـتـب /sessions
""", "script"))
        
        except Exception as ex:
            err_str = str(ex)
            if "SessionPasswordNeededError" in err_str or "password" in err_str.lower():
                waiting_2fa[user_id] = True
                await e.reply(fancy_text("""
╔══════════════════════════╗
║       𝐓𝐖𝐎 𝐅𝐀𝐂𝐓𝐎𝐑 𝐀𝐔𝐓𝐇   
╚══════════════════════════╝

✧ حـسـابـك يـحـتـاج كـلـمـة مـرور الـتـحـقـق الـثـنـائـي
✧ ارسـل كـلـمـة الـمـرور
""", "script"))
            else:
                if user_id in phone_clients:
                    del phone_clients[user_id]
                await e.reply(fancy_text(f"✧ خـطـأ : {err_str}", "script"))
    
    elif user_id in waiting_2fa:
        password = text
        waiting_2fa.pop(user_id)
        
        client_data = phone_clients.get(user_id)
        if not client_data:
            await e.reply(fancy_text("✧ حـصـلـت مـشـكـلـه", "script"))
            return
        
        client = client_data["client"]
        
        try:
            from telethon.errors import PasswordHashInvalidError
            await client.sign_in(password=password)
            me = await client.get_me()
            
            session_key = str(uuid.uuid4())
            user_session = UserbotSession(client, user_id, session_key)
            user_session.source_enabled = True
            
            all_clients.append(user_session)
            if user_id not in user_clients:
                user_clients[user_id] = []
            user_clients[user_id].append(user_session)
            
            if user_id in phone_clients:
                del phone_clients[user_id]
            
            await e.reply(fancy_text(f"""
╔══════════════════════════╗
║        𝐒𝐄𝐒𝐒𝐈𝐎𝐍 𝐀𝐃𝐃𝐄𝐃     
╚══════════════════════════╝

✧ تـم تـسـجـيـل الـدخـول بـنـجـاح
✧ الـحـسـاب ↤ {me.first_name}

✧ عـشـان تـشـوف الـجـلـسـات اكـتـب /sessions
""", "script"))
        
        except Exception as ex:
            if user_id in phone_clients:
                del phone_clients[user_id]
            await e.reply(fancy_text(f"✧ كـلـمـة الـمـرور غـلـط : {str(ex)}", "script"))

@bot.on(events.NewMessage)
async def handle_admin_requests(e):
    user_id = e.sender_id
    
    if user_id in waiting_user_add:
        try:
            target_user_id = int(e.raw_text.strip())
            allowed_users.add(target_user_id)
            waiting_user_add.remove(user_id)
            await e.reply(fancy_text(f"""
╔══════════════════════════╗
║          𝐔𝐒𝐄𝐑 𝐀𝐃𝐃𝐄𝐃      
╚══════════════════════════╝

✧ تـم اضـافـة الـمـسـتـخـدم {target_user_id} بـنـجـاح
""", "script"))
        except:
            await e.reply(fancy_text("✧ ايـدي غـلـط", "script"))
    
    elif user_id in waiting_user_ban:
        try:
            target_user_id = int(e.raw_text.strip())
            banned_users.add(target_user_id)
            waiting_user_ban.remove(user_id)
            await e.reply(fancy_text(f"""
╔══════════════════════════╗
║          𝐔𝐒𝐄𝐑 𝐁𝐀𝐍𝐍𝐄𝐃     
╚══════════════════════════╝

✧ تـم حـظـر الـمـسـتـخـدم {target_user_id} بـنـجـاح
""", "script"))
        except:
            await e.reply(fancy_text("✧ ايـدي غـلـط", "script"))
    
    elif user_id in waiting_user_unban:
        try:
            target_user_id = int(e.raw_text.strip())
            if target_user_id in banned_users:
                banned_users.remove(target_user_id)
            waiting_user_unban.remove(user_id)
            await e.reply(fancy_text(f"""
╔══════════════════════════╗
║        𝐔𝐒𝐄𝐑 𝐔𝐍𝐁𝐀𝐍𝐍𝐄𝐃     
╚══════════════════════════╝

✧ تـم الـغـاء حـظـر الـمـسـتـخـدم {target_user_id} بـنـجـاح
""", "script"))
        except:
            await e.reply(fancy_text("✧ ايـدي غـلـط", "script"))

@bot.on(events.CallbackQuery)
async def callback_handler(e):
    user_id = e.sender_id
    data = e.data.decode('utf-8')
    
    if data == "addsession":
        if user_id != OWNER_ID and user_id not in allowed_users:
            await e.answer("غير مسموح", alert=True)
            return
        
        waiting_sessions[user_id] = True
        await e.edit(fancy_text("""
╔══════════════════════════╗
║        𝐀𝐃𝐃 𝐒𝐄𝐒𝐒𝐈𝐎𝐍      
╚══════════════════════════╝

✧ ارسـل سـتـرنـج الـجـلـسـه 
""", "script"))
        
    elif data == "adduser":
        if user_id != OWNER_ID:
            await e.answer("متاح فقط للمطور", alert=True)
            return
        
        waiting_user_add.add(user_id)
        await e.edit(fancy_text("""
╔══════════════════════════╗
║        𝐀𝐃𝐃 𝐔𝐒𝐄𝐑        
╚══════════════════════════╝

✧ ارسـل ايـدي الـمـسـتـخـدم لـتـفـعـيـلـه
""", "script"))
        
    elif data == "banuser":
        if user_id != OWNER_ID:
            await e.answer("متاح فقط للمطور", alert=True)
            return
        
        waiting_user_ban.add(user_id)
        await e.edit(fancy_text("""
╔══════════════════════════╗
║        𝐁𝐀𝐍 𝐔𝐒𝐄𝐑        
╚══════════════════════════╝

✧ ارسـل ايـدي الـمـسـتـخـدم لـحـظـره
""", "script"))
        
    elif data == "unbanuser":
        if user_id != OWNER_ID:
            await e.answer("متاح فقط للمطور", alert=True)
            return
        
        waiting_user_unban.add(user_id)
        await e.edit(fancy_text("""
╔══════════════════════════╗
║       𝐔𝐍𝐁𝐀𝐍 𝐔𝐒𝐄𝐑      
╚══════════════════════════╝

✧ ارسـل ايـدي الـمـسـتـخـدم لـفـك الـحـظـر
""", "script"))
    
    elif data.startswith("acc_"):
        if user_id != OWNER_ID:
            await e.answer("متاح فقط للمطور", alert=True)
            return
        
        target_user = int(data.split("_")[1])
        allowed_users.add(target_user)
        if target_user in pending_requests:
            del pending_requests[target_user]
        
        await e.edit(fancy_text(f"""
╔══════════════════════════╗
║        𝐀𝐂𝐂𝐄𝐏𝐓𝐄𝐃       
╚══════════════════════════╝

✧ تـم تـفـعـيـل الـمـسـتـخـدم {target_user}
""", "script"))
        
        try:
            await bot.send_message(target_user, fancy_text("""
╔══════════════════════════╗
║          𝐒𝐎𝐔𝐑𝐂𝐄 GMR     
╚══════════════════════════╝

✧ تـم تـفـعـيـل حـسـابـك
✧ اسـتـخـدم /start لـتـشـغـيـل الـبـوت
""", "script"))
        except:
            pass
    
    elif data.startswith("rej_"):
        if user_id != OWNER_ID:
            await e.answer("متاح فقط للمطور", alert=True)
            return
        
        target_user = int(data.split("_")[1])
        if target_user in pending_requests:
            del pending_requests[target_user]
        
        await e.edit(fancy_text(f"""
╔══════════════════════════╗
║        𝐑𝐄𝐉𝐄𝐂𝐓𝐄𝐃       
╚══════════════════════════╝

✧ تـم رفـض الـمـسـتـخـدم {target_user}
""", "script"))
        
        try:
            await bot.send_message(target_user, fancy_text("""
╔══════════════════════════╗
║          𝐒𝐎𝐔𝐑𝐂𝐄 GMR     
╚══════════════════════════╝

✧ تـم رفـض طـلـبـك       
✧ لـمـراسـلـه الـمـطـور @TopKevo
""", "script"))
        except:
            pass
    
    elif data == "copy_source":
        await e.answer("تـم الـنـسـخ", alert=True)
        await e.edit("```\n@HBBBHBB\n```")
    
    elif data == "copy_channel":
        await e.answer("تـم الـنـسـخ", alert=True)
        await e.edit("```\nhttps://t.me/@HBBBHBB\n```")
    
    elif data == "copy_bot":
        await e.answer("تـم الـنـسـخ", alert=True)
        await e.edit("```\n@TelethonByKevobot\n```")
    
    elif data == "copy_dev":
        await e.answer("تـم الـنـسـخ", alert=True)
        await e.edit("```\n@TopKevo\n```")
    
    elif data == "enable_source":
        if user_id != OWNER_ID and user_id not in allowed_users:
            await e.answer("غير مسموح", alert=True)
            return
        
        sessions = user_clients.get(user_id, [])
        if not sessions:
            await e.answer("مافي جلسات مضافه", alert=True)
            return
        
        for session in sessions:
            session.source_enabled = True
        
        await e.edit(fancy_text("""
╔══════════════════════════╗
║       𝐒𝐎𝐔𝐑𝐂𝐄 𝐄𝐍𝐀𝐁𝐋𝐄𝐃    
╚══════════════════════════╝

✧ تـم تـفـعـيـل الـسـورس
✧ كـل الاوامـر تـعـمـل الان
""", "script"))
    
    elif data == "disable_source":
        if user_id != OWNER_ID and user_id not in allowed_users:
            await e.answer("غير مسموح", alert=True)
            return
        
        sessions = user_clients.get(user_id, [])
        if not sessions:
            await e.answer("مافي جلسات مضافه", alert=True)
            return
        
        for session in sessions:
            session.source_enabled = False
        
        await e.edit(fancy_text("""
╔══════════════════════════╗
║       𝐒𝐎𝐔𝐑𝐂𝐄 𝐃𝐈𝐒𝐀𝐁𝐋𝐄𝐃   
╚══════════════════════════╝

✧ تـم تـعـطـيـل الـسـورس
✧ الاوامـر مـوقـوفـه
✧ اضـغـط تـفـعـيـل الـسـورس لـتـشـغـيـلـهـا مـره اخـرى
""", "script"))
    
    elif data == "login_phone":
        if user_id != OWNER_ID and user_id not in allowed_users:
            await e.answer("غير مسموح", alert=True)
            return
        
        waiting_phone[user_id] = True
        await e.edit(fancy_text("""
╔══════════════════════════╗
║       𝐋𝐎𝐆𝐈𝐍 𝐁𝐘 𝐏𝐇𝐎𝐍𝐄    
╚══════════════════════════╝

✧ ارسـل رقـم الـهـاتـف مـع الـكـود الـدولـي
✧ مـثـال: +9665xxxxxxxx
""", "script"))

    elif data.startswith("del_session_"):
        if user_id != OWNER_ID and user_id not in allowed_users:
            await e.answer("غير مسموح", alert=True)
            return
        
        try:
            session_index = int(data.split("del_session_")[1])
            sessions = user_clients.get(user_id, [])
            
            if 0 <= session_index < len(sessions):
                session = sessions[session_index]
                try:
                    me = await session.get_me_safe()
                    acc_name = me.first_name if me else "الحساب"
                except:
                    acc_name = "الحساب"
                
                success = await delete_session_completely(session, user_id)
                
                if success:
                    await e.edit(fancy_text(f"""
╔══════════════════════════╗
║      𝐒𝐄𝐒𝐒𝐈𝐎𝐍 𝐃𝐄𝐋𝐄𝐓𝐄𝐃   
╚══════════════════════════╝

✧ تـم حـذف جـلـسـة ↤ {acc_name} مـن الـجـذور
✧ تـم ايـقـاف الـوهـمـي اونـلـايـن والـسـاعـه وكـل الـمـهـام
✧ تـم قـطـع الاتـصـال نـهـائـيـاً
""", "script"))
                else:
                    await e.answer("حصلت مشكله اثناء الحذف", alert=True)
            else:
                await e.answer("رقم الجلسة غلط", alert=True)
        except Exception as ex:
            await e.answer(f"خطأ: {str(ex)}", alert=True)

    elif data == "cancel_del":
        await e.edit(fancy_text("""
╔══════════════════════════╗
║          𝐂𝐀𝐍𝐂𝐄𝐋𝐋𝐄𝐃     
╚══════════════════════════╝

✧ تـم الـغـاء الـحـذف
""", "script"))

# ============================================================
# أمر .م8 - التحويل والتتبع المتقدم
# ============================================================
@bot.on(events.NewMessage(pattern="/م8"))
async def convert_menu(e):
    user_id = e.sender_id
    if user_id in banned_users:
        return
    if user_id not in allowed_users and user_id != OWNER_ID:
        return
    text = """
🇷🇺 **أوامر التحويل والتتبع** 🇷🇺

🔥 **الأوامر المتاحة:**

• `.بلش وتحويل` ← (بالرد على شخص) يتتبع الشخص ويحول آخر رسالة له من المحفوظات إلى المحادثة الحالية

💀 **الاستخدام:**
رد على رسالة الشخص واكتب:
`.بلش وتحويل`

سيتم:
1️⃣ تتبع الشخص
2️⃣ تحويل آخر رسالة من المحفوظات إلى المحادثة
3️⃣ الرد على آخر رسالة يرسلها في المحادثة

🔥 **تيم الروس 🇷🇺**
"""
    await e.reply(text)

@bot.on(events.NewMessage(pattern=".بلش وتحويل", outgoing=True))
async def convert_and_track(e):
    if not e.is_reply:
        await e.edit("⚠️ يرجى الرد على رسالة الشخص المراد تتبعه")
        return
    
    reply_msg = await e.get_reply_message()
    if not reply_msg or not reply_msg.sender_id:
        await e.edit("⚠️ لا يمكن تحديد المستخدم")
        return
    
    target_user_id = reply_msg.sender_id
    chat_id = e.chat_id
    
    # جلب اسم المستخدم
    try:
        target_entity = await bot.get_entity(target_user_id)
        target_name = target_entity.first_name or "المستخدم"
        if target_entity.username:
            target_name += f" (@{target_entity.username})"
    except:
        target_name = f"المستخدم ({target_user_id})"
    
    status_msg = f"🎯 جاري تتبع {target_name}...\n"
    await e.edit(status_msg)
    
    try:
        # البحث عن آخر رسالة من الهدف في المحفوظات وتحويلها
        forwarded_count = 0
        last_forwarded_msg = None
        
        async for msg in bot.iter_messages("me", from_user=target_user_id, limit=5):
            if msg:
                await msg.forward_to(chat_id)
                forwarded_count += 1
                last_forwarded_msg = msg
                break
        
        if forwarded_count == 0:
            await e.edit(status_msg + "⚠️ لا توجد رسائل محفوظة من هذا الشخص")
        else:
            await e.edit(status_msg + f"✅ تم تحويل آخر رسالة من المحفوظات\n")
        
        # البحث عن آخر رسالة من الهدف في المحادثة والرد عليها
        last_msg = None
        async for msg in bot.iter_messages(chat_id, from_user=target_user_id, limit=1):
            if msg:
                last_msg = msg
                break
        
        if last_msg:
            # الرد على آخر رسالة
            spam_words = []
            await e.edit(status_msg + f"✅ تم الرد على آخر رسالة من {target_name}")
        else:
            await e.edit(status_msg + "⚠️ لا توجد رسائل من هذا الشخص في المحادثة")
        
        await e.edit(f"✅ تم تتبع {target_name} بنجاح!")
        
    except Exception as ex:
        await e.edit(f"❌ خطأ: {str(ex)}")

print("تم تشغيل البوت بنجاح")
print("𝐃𝐄𝐕𝐄𝐋𝐎𝐏𝐄𝐑 : @G_M_R6")
print("Telethon By GMR ")
bot.run_until_disconnected()
