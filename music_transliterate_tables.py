# https://github.com/mtxadmin/music_transliterate/
# Many thanks to Deepseek AI, who greatly helped with writing and debugging of this script


# Таблицы транслитерации: расширенная кириллица, декоративная латиница и сборка таблиц по языкам.


from typing import Dict


class TransliterationTablesMixin:
    def _add_extra_cyrillic(self, table: Dict[str, str]) -> None:
        """Добавляет в таблицу транслитерации символы расширенной кириллицы."""
        extra_cyrillic = {
            # Азербайджанский, башкирский, казахский, татарский и др.
            'Ә': 'A', 'ә': 'a',      # A with diaeresis (азерб., башк., каз., тат.)
            'Ғ': 'G', 'ғ': 'g',      # G with stroke (башк., каз., тадж., тат., уйг.)
            'Ҙ': 'Z', 'ҙ': 'z',      # Z with descender (башк.)
            'Ҡ': 'K', 'ҡ': 'k',      # K with descender (башк.)
            'Ң': 'N', 'ң': 'n',      # N with descender (башк., каз., кирг., тат., уйг.)
            'Ө': 'O', 'ө': 'o',      # O with bar (башк., бурят., калм., каз., монг., тат., тув., якут.)
            'Ү': 'U', 'ү': 'u',      # U with straight stroke (башк., бурят., калм., каз., кирг., монг., тат., тув., якут.)
            'Һ': 'H', 'һ': 'h',      # Shha (башк., бурят., калм., каз., тат., якут.)
            'Ҷ': 'Ch', 'ҷ': 'ch',    # Che with descender (тадж.)
            'Ҳ': 'H', 'ҳ': 'h',      # Ha with descender (тадж., узб.)
            'Қ': 'Q', 'қ': 'q',      # Ka with descender (каз., тадж., узб., уйг.)
            'Ӯ': 'U', 'ӯ': 'u',      # U with macron (тадж.)
            'Ғ': 'G', 'ғ': 'g',      # (повтор для единообразия)
            'Ҷ': 'J', 'ҷ': 'j',      # вариант транслитерации
            # Белорусский, украинский
            'Ў': 'U', 'ў': 'u',      # Short U (белорус., узб.)
            'І': 'I', 'і': 'i',      # Belarusian/Ukrainian I (уже есть в ukrainian_table)
            'Ґ': 'G', 'ґ': 'g',      # G with upturn (укр.)
            'Є': 'Ye', 'є': 'ye',    # Ukrainian Ye
            'Ї': 'Yi', 'ї': 'yi',    # Ukrainian Yi
            # Дополнительные буквы с диакритикой, встречающиеся в именах
            'Ӂ': 'Zh', 'ӂ': 'zh',    # Zhe with breve (молд., гагауз.)
            'Ӌ': 'Ch', 'ӌ': 'ch',    # Che with descender (хакас.)
            'Ӑ': 'A', 'ӑ': 'a',      # A with breve (чуваш.)
            'Ӗ': 'E', 'ӗ': 'e',      # E with breve (чуваш.)
            'Ҫ': 'S', 'ҫ': 's',      # Es with descender (башк., чуваш.)
            'Ҭ': 'T', 'ҭ': 't',      # Te with descender (абхаз.)
            'Ӳ': 'U', 'ӳ': 'u',      # U with double acute (чуваш.)
            'Ӱ': 'U', 'ӱ': 'u',      # U with diaeresis (алт., хакас., марийск.)
            'Ӹ': 'Y', 'ӹ': 'y',      # Yeru with diaeresis (марийск.)
            'Ӓ': 'A', 'ӓ': 'a',      # A with diaeresis (марийск., саам.)
            'Ӛ': 'E', 'ӛ': 'e',      # E with diaeresis (ненецк.)
            'Ӝ': 'Zh', 'ӝ': 'zh',    # Zhe with diaeresis (удм.)
            'Ӟ': 'Dz', 'ӟ': 'dz',    # Ze with diaeresis (удм.)
            'Ӥ': 'I', 'ӥ': 'i',      # I with diaeresis (удм.)
            'Ӧ': 'O', 'ӧ': 'o',      # O with diaeresis (коми, марийск., удм.)
            'Ӫ': 'O', 'ӫ': 'o',      # O with diaeresis and macron (эвенк.)
            'Ӭ': 'E', 'ӭ': 'e',      # E with diaeresis and macron (эвенк.)
            'Ӵ': 'Ch', 'ӵ': 'ch',    # Che with diaeresis (удм.)
            'Ҕ': 'G', 'ҕ': 'g',      # Ghe with middle hook (абхазский, якутский)
            'Ӄ': 'K', 'ӄ': 'k',      # Ka with vertical stroke (чукотский, корякский)
        }
        table.update(extra_cyrillic)

    def _add_decorative_latin(self, table: Dict[str, str]) -> None:
        """Добавляет в таблицу транслитерации декоративные латинские символы (Small Caps, коптские буквы и др.).

        Слой не привязан к языку: это не «русские буквы», а универсальная
        декорация. Вызывается для русской и европейской таблиц, потому что
        detect_language() выбирает одну таблицу на всё имя, а в имени может
        встретиться и кириллица, и декорация одновременно.
        """
        decorative = {
            # Small Caps (U+1D00 – U+1D7F, выборочно)
            'ᴀ': 'A', 'ʙ': 'B', 'ᴄ': 'C', 'ᴅ': 'D', 'ᴇ': 'E',
            'ꜰ': 'F', 'ɢ': 'G', 'ʜ': 'H', 'ɪ': 'I', 'ᴊ': 'J',
            'ᴋ': 'K', 'ʟ': 'L', 'ᴍ': 'M', 'ɴ': 'N', 'ᴏ': 'O',
            'ᴘ': 'P', 'ꞯ': 'Q', 'ʀ': 'R', 'ꜱ': 'S', 'ᴛ': 'T',
            'ᴜ': 'U', 'ᴠ': 'V', 'ᴡ': 'W', 'ʏ': 'Y',
            # Латинская "x" здесь не указана специально: отдельного small-cap X
            # в Unicode нет, а отображение 'x' -> 'X' ломало обычные имена
            # (Maxx -> MaXX). Обычная "x" должна оставаться как есть.
            'ᴢ': 'Z',
            # Latin Letter Yr (стилизованная R)
            'Ʀ': 'R',
            # Декоративная "e" и родственные символы.
            # Встречаются в названиях треков, например:
            # "Onǝ More & Irenika - Na Padio (Shadow UA RemiX)".
            # Без этих замен транслитерация оставляла не-ASCII символ,
            # и файл отбраковывался проверкой has_non_ascii.
            'Ǝ': 'E',   # U+018E LATIN CAPITAL LETTER REVERSED E
            'ǝ': 'e',   # U+01DD LATIN SMALL LETTER TURNED E
            'Ə': 'E',   # U+018F LATIN CAPITAL LETTER SCHWA
            'ə': 'e',   # U+0259 LATIN SMALL LETTER SCHWA
            # Коптские буквы (часто используются для стилизации)
            'Ⲁ': 'A', 'ⲁ': 'a',
            'Ⲃ': 'B', 'ⲃ': 'b',
            'Ⲅ': 'G', 'ⲅ': 'g',
            'Ⲇ': 'D', 'ⲇ': 'd',
            'Ⲉ': 'E', 'ⲉ': 'e',
            'Ⲋ': 'S', 'ⲋ': 's',
            'Ⲍ': 'Z', 'ⲍ': 'z',
            'Ⲏ': 'I', 'ⲏ': 'i',
            'Ⲑ': 'Th', 'ⲑ': 'th',
            'Ⲓ': 'I', 'ⲓ': 'i',
            'Ⲕ': 'K', 'ⲕ': 'k',
            'Ⲗ': 'L', 'ⲗ': 'l',
            'Ⲙ': 'M', 'ⲙ': 'm',
            'Ⲛ': 'N', 'ⲛ': 'n',
            'Ⲝ': 'X', 'ⲝ': 'x',
            'Ⲟ': 'O', 'ⲟ': 'o',
            'Ⲡ': 'P', 'ⲡ': 'p',
            'Ⲣ': 'R', 'ⲣ': 'r',
            'Ⲥ': 'S', 'ⲥ': 's',
            'Ⲧ': 'T', 'ⲧ': 't',
            'Ⲩ': 'U', 'ⲩ': 'u',
            'Ⲫ': 'Ph', 'ⲫ': 'ph',
            'Ⲭ': 'Kh', 'ⲭ': 'kh',
            'Ⲯ': 'Ps', 'ⲯ': 'ps',
            'Ⲱ': 'O', 'ⲱ': 'o',
            'Ⲳ': 'Sh', 'ⲳ': 'sh',
            'Ⲵ': 'F', 'ⲵ': 'f',
            'Ⲷ': 'Kh', 'ⲷ': 'kh',
            'Ⲹ': 'H', 'ⲹ': 'h',
            'Ⲻ': 'Ch', 'ⲻ': 'ch',
            'Ⲽ': 'Ti', 'ⲽ': 'ti',
            # Декоративные буквы из других письменностей (похожие на латиницу)
            # Канадское слоговое письмо и чероки
            'ᗰ': 'M',   # U+15F0
            'Ꮌ': 'M',   # U+13BC (Cherokee)
            'Ꮗ': 'W',   # U+13C7 (Cherokee)
            'Ꭵ': 'i',   # U+13A5
            'Ꮢ': 'R',   # U+13D2
            # Грузинский (Mkhedruli) – визуально похожие на латиницу
            'ყ': 'y',   # U+10E7
            'მ': 'm',   # U+10DB
            'ნ': 'n',   # U+10DC
            'ა': 'a',   # U+10D0
            'ბ': 'b',   # U+10D1
            'გ': 'g',   # U+10D2
            'დ': 'd',   # U+10D3
            'ე': 'e',   # U+10D4
            'ვ': 'v',   # U+10D5
            'ზ': 'z',   # U+10D6
            'თ': 't',   # U+10D7
            'ი': 'i',   # U+10D8
            'კ': 'k',   # U+10D9
            'ლ': 'l',   # U+10DA
            'ო': 'o',   # U+10DD
            'პ': 'p',   # U+10DE
            'ჟ': 'zh',  # U+10DF
            'რ': 'r',   # U+10E0
            'ს': 's',   # U+10E1
            'ტ': 't',   # U+10E2
            'უ': 'u',   # U+10E3
            'ფ': 'p',   # U+10E4
            'ქ': 'k',   # U+10E5
            'ღ': 'gh',  # U+10E6
            'შ': 'sh',  # U+10E8
            'ჩ': 'ch',  # U+10E9
            'ც': 'ts',  # U+10EA
            'ძ': 'dz',  # U+10EB
            'წ': 'ts',  # U+10EC
            'ჭ': 'ch',  # U+10ED
            'ხ': 'kh',  # U+10EE
            'ჯ': 'j',   # U+10EF
            'ჰ': 'h',   # U+10F0
            # Греческие буквы (стилистические)
            'ϐ': 'b',   # U+03D0 (Greek beta symbol)
            # Тайские буквы (стилизация)
            'ค': 'a',   # U+0E04 (kho khwai, визуально 'a')
            # Гурмукхи (пенджаби)
            'ਮ': 'm',   # U+0A2E  # indents are ok here
            # Other
            'ʍ': 'w',   # U+028D LATIN SMALL LETTER TURNED W
            'ნ': 'n',   # U+10DC (уже добавлен выше, но оставлен для ясности)
        }
        table.update(decorative)

    def _create_transliteration_tables(self) -> Dict[str, Dict[str, str]]:
        """Создает таблицы транслитерации для всех языков"""
        
        # Русский язык по ГОСТ 7.79-2000 (система B) с изменениями:
        # - ъ -> '
        # - й -> y (вместо j)
        russian_table = {
            'А': 'A', 'Б': 'B', 'В': 'V', 'Г': 'G', 'Д': 'D',
            'Е': 'E', 'Ё': 'Yo', 'Ж': 'Zh', 'З': 'Z', 'И': 'I',
            'Й': 'Y', 'К': 'K', 'Л': 'L', 'М': 'M', 'Н': 'N',  # Й -> Y
            'О': 'O', 'П': 'P', 'Р': 'R', 'С': 'S', 'Т': 'T',
            'У': 'U', 'Ф': 'F', 'Х': 'Kh', 'Ц': 'Ts', 'Ч': 'Ch',
            'Ш': 'Sh', 'Щ': 'Shch', 'Ъ': "'", 'Ы': 'Y', 'Ь': "'",
            'Э': 'E', 'Ю': 'Yu', 'Я': 'Ya',
            'а': 'a', 'б': 'b', 'в': 'v', 'г': 'g', 'д': 'd',
            'е': 'e', 'ё': 'yo', 'ж': 'zh', 'з': 'z', 'и': 'i',
            'й': 'y', 'к': 'k', 'л': 'l', 'м': 'm', 'н': 'n',  # й -> y
            'о': 'o', 'п': 'p', 'р': 'r', 'с': 's', 'т': 't',
            'у': 'u', 'ф': 'f', 'х': 'kh', 'ц': 'ts', 'ч': 'ch',
            'ш': 'sh', 'щ': 'shch', 'ъ': "'", 'ы': 'y', 'ь': "'",
            'э': 'e', 'ю': 'yu', 'я': 'ya'
        }
        
        # Украинский язык
        ukrainian_table = {
            'А': 'A', 'Б': 'B', 'В': 'V', 'Г': 'G', 'Ґ': 'G', 'Д': 'D',
            'Е': 'E', 'Є': 'Ye', 'Ж': 'Zh', 'З': 'Z', 'И': 'Y', 'І': 'I',
            'Ї': 'Yi', 'Й': 'Y', 'К': 'K', 'Л': 'L', 'М': 'M', 'Н': 'N',
            'О': 'O', 'П': 'P', 'Р': 'R', 'С': 'S', 'Т': 'T', 'У': 'U',
            'Ф': 'F', 'Х': 'Kh', 'Ц': 'Ts', 'Ч': 'Ch', 'Ш': 'Sh', 'Щ': 'Shch',
            'Ь': "'", 'Ю': 'Yu', 'Я': 'Ya',
            'а': 'a', 'б': 'b', 'в': 'v', 'г': 'g', 'ґ': 'g', 'д': 'd',
            'е': 'e', 'є': 'ye', 'ж': 'zh', 'з': 'z', 'и': 'y', 'і': 'i',
            'ї': 'yi', 'й': 'y', 'к': 'k', 'л': 'l', 'м': 'm', 'н': 'n',
            'о': 'o', 'п': 'p', 'р': 'r', 'с': 's', 'т': 't', 'у': 'u',
            'ф': 'f', 'х': 'kh', 'ц': 'ts', 'ч': 'ch', 'ш': 'sh', 'щ': 'shch',
            'ь': "'", 'ю': 'yu', 'я': 'ya'
        }
        
        # Польский язык
        polish_table = {
            'Ą': 'A', 'Ć': 'C', 'Ę': 'E', 'Ł': 'L', 'Ń': 'N',
            'Ó': 'O', 'Ś': 'S', 'Ź': 'Z', 'Ż': 'Z',
            'ą': 'a', 'ć': 'c', 'ę': 'e', 'ł': 'l', 'ń': 'n',
            'ó': 'o', 'ś': 's', 'ź': 'z', 'ż': 'z'
        }
        
        # Болгарский язык
        bulgarian_table = {
            'А': 'A', 'Б': 'B', 'В': 'V', 'Г': 'G', 'Д': 'D',
            'Е': 'E', 'Ж': 'Zh', 'З': 'Z', 'И': 'I', 'Й': 'Y',
            'К': 'K', 'Л': 'L', 'М': 'M', 'Н': 'N', 'О': 'O',
            'П': 'P', 'Р': 'R', 'С': 'S', 'Т': 'T', 'У': 'U',
            'Ф': 'F', 'Х': 'H', 'Ц': 'Ts', 'Ч': 'Ch', 'Ш': 'Sh',
            'Щ': 'Sht', 'Ъ': 'A', 'Ь': 'Y', 'Ю': 'Yu', 'Я': 'Ya',
            'а': 'a', 'б': 'b', 'в': 'v', 'г': 'g', 'д': 'd',
            'е': 'e', 'ж': 'zh', 'з': 'z', 'и': 'i', 'й': 'y',
            'к': 'k', 'л': 'l', 'м': 'm', 'н': 'n', 'о': 'o',
            'п': 'p', 'р': 'r', 'с': 's', 'т': 't', 'у': 'u',
            'ф': 'f', 'х': 'h', 'ц': 'ts', 'ч': 'ch', 'ш': 'sh',
            'щ': 'sht', 'ъ': 'a', 'ь': 'y', 'ю': 'yu', 'я': 'ya'
        }
        
        # Немецкий язык
        german_table = {
            'Ä': 'Ae', 'Ö': 'Oe', 'Ü': 'Ue', 'ß': 'ss',
            'ä': 'ae', 'ö': 'oe', 'ü': 'ue'
        }
        
        # Общая таблица для европейских языков с диакритикой и другими символами Unicode
        european_table = {
            # Latin-1 Supplement (ISO-8859-1)
            'À': 'A', 'Á': 'A', 'Â': 'A', 'Ã': 'A', 'Ä': 'A',
            'Å': 'A', 'Æ': 'AE', 'Ç': 'C', 'È': 'E', 'É': 'E',
            'Ê': 'E', 'Ë': 'E', 'Ì': 'I', 'Í': 'I', 'Î': 'I',
            'Ï': 'I', 'Ð': 'D', 'Ñ': 'N', 'Ò': 'O', 'Ó': 'O',
            'Ô': 'O', 'Õ': 'O', 'Ö': 'O', 'Ø': 'O', 'Ù': 'U',
            'Ú': 'U', 'Û': 'U', 'Ü': 'U', 'Ý': 'Y', 'Þ': 'Th',
            'ß': 'ss', 'à': 'a', 'á': 'a', 'â': 'a', 'ã': 'a',
            'ä': 'a', 'å': 'a', 'æ': 'ae', 'ç': 'c', 'è': 'e',
            'é': 'e', 'ê': 'e', 'ë': 'e', 'ì': 'i', 'í': 'i',
            'î': 'i', 'ï': 'i', 'ð': 'd', 'ñ': 'n', 'ò': 'o',
            'ó': 'o', 'ô': 'o', 'õ': 'o', 'ö': 'o', 'ø': 'o',
            'ù': 'u', 'ú': 'u', 'û': 'u', 'ü': 'u', 'ý': 'y',
            'þ': 'th', 'ÿ': 'y',
            
            # Latin Extended-A (часть символов из Unicode диапазона U+0100-U+017F)
            'Ā': 'A', 'ā': 'a', 'Ă': 'A', 'ă': 'a', 'Ą': 'A',
            'ą': 'a', 'Ć': 'C', 'ć': 'c', 'Ĉ': 'C', 'ĉ': 'c',
            'Ċ': 'C', 'ċ': 'c', 'Č': 'C', 'č': 'c', 'Ď': 'D',
            'ď': 'd', 'Đ': 'D', 'đ': 'd', 'Ē': 'E', 'ē': 'e',
            'Ĕ': 'E', 'ĕ': 'e', 'Ė': 'E', 'ė': 'e', 'Ę': 'E',
            'ę': 'e', 'Ě': 'E', 'ě': 'e', 'Ĝ': 'G', 'ĝ': 'g',
            'Ğ': 'G', 'ğ': 'g', 'Ġ': 'G', 'ġ': 'g', 'Ģ': 'G',
            'ģ': 'g', 'Ĥ': 'H', 'ĥ': 'h', 'Ħ': 'H', 'ħ': 'h',
            'Ĩ': 'I', 'ĩ': 'i', 'Ī': 'I', 'ī': 'i', 'Ĭ': 'I',
            'ĭ': 'i', 'Į': 'I', 'į': 'i', 'İ': 'I', 'ı': 'i',
            'Ĵ': 'J', 'ĵ': 'j', 'Ķ': 'K', 'ķ': 'k', 'ĸ': 'k',
            'Ĺ': 'L', 'ĺ': 'l', 'Ļ': 'L', 'ļ': 'l', 'Ľ': 'L',
            'ľ': 'l', 'Ŀ': 'L', 'ŀ': 'l', 'Ł': 'L', 'ł': 'l',
            'Ń': 'N', 'ń': 'n', 'Ņ': 'N', 'ņ': 'n', 'Ň': 'N',
            'ň': 'n', 'ŉ': 'n', 'Ŋ': 'N', 'ŋ': 'n', 'Ō': 'O',
            'ō': 'o', 'Ŏ': 'O', 'ŏ': 'o', 'Ő': 'O', 'ő': 'o',
            'Œ': 'OE', 'œ': 'oe', 'Ŕ': 'R', 'ŕ': 'r', 'Ŗ': 'R',
            'ŗ': 'r', 'Ř': 'R', 'ř': 'r', 'Ś': 'S', 'ś': 's',
            'Ŝ': 'S', 'ŝ': 's', 'Ş': 'S', 'ş': 's', 'Š': 'S',
            'š': 's', 'Ţ': 'T', 'ţ': 't', 'Ť': 'T', 'ť': 't',
            'Ŧ': 'T', 'ŧ': 't', 'Ũ': 'U', 'ũ': 'u', 'Ū': 'U',
            'ū': 'u', 'Ŭ': 'U', 'ŭ': 'u', 'Ů': 'U', 'ů': 'u',
            'Ű': 'U', 'ű': 'u', 'Ų': 'U', 'ų': 'u', 'Ŵ': 'W',
            'ŵ': 'w', 'Ŷ': 'Y', 'ŷ': 'y', 'Ÿ': 'Y', 'Ź': 'Z',
            'ź': 'z', 'Ż': 'Z', 'ż': 'z', 'Ž': 'Z', 'ž': 'z',
            'ſ': 's',
            
            # Latin Extended-B (некоторые символы)
            'ƀ': 'b', 'Ɓ': 'B', 'Ƃ': 'B', 'ƃ': 'b', 'Ƅ': 'B',
            'ƅ': 'b', 'Ɔ': 'O', 'Ƈ': 'C', 'ƈ': 'c', 'Ɖ': 'D',
            'Ɗ': 'D', 'Ƌ': 'D', 'ƌ': 'd', 'ƍ': 'd', 'Ǝ': 'E',
            'Ə': 'E', 'Ɛ': 'E', 'Ƒ': 'F', 'ƒ': 'f', 'Ɠ': 'G',
            'Ɣ': 'G', 'ƕ': 'hv', 'Ɩ': 'I', 'Ɨ': 'I', 'Ƙ': 'K',
            'ƙ': 'k', 'ƚ': 'l', 'ƛ': 'l', 'Ɯ': 'M', 'Ɲ': 'N',
            'ƞ': 'n', 'Ɵ': 'O', 'Ơ': 'O', 'ơ': 'o', 'Ƣ': 'OI',
            'ƣ': 'oi', 'Ƥ': 'P', 'ƥ': 'p', 'Ʀ': 'R', 'Ƨ': 'S',
            'ƨ': 's', 'Ʃ': 'E', 'ƪ': 'E', 'ƫ': 't', 'Ƭ': 'T',
            'ƭ': 't', 'Ʈ': 'T', 'Ư': 'U', 'ư': 'u', 'Ʊ': 'Y',
            'Ʋ': 'V', 'Ƴ': 'Y', 'ƴ': 'y', 'Ƶ': 'Z', 'ƶ': 'z',
            'Ʒ': 'Z', 'Ƹ': 'Z', 'ƹ': 'z', 'ƺ': 'z', 'ƻ': '2',
            'Ƽ': '5', 'ƽ': '5', 'ƾ': 'T', 'ƿ': 'p',
            
            # Latin Extended Additional (некоторые символы)
            'Ḁ': 'A', 'ḁ': 'a', 'Ḃ': 'B', 'ḃ': 'b', 'Ḅ': 'B',
            'ḅ': 'b', 'Ḇ': 'B', 'ḇ': 'b', 'Ḉ': 'C', 'ḉ': 'c',
            'Ḋ': 'D', 'ḋ': 'd', 'Ḍ': 'D', 'ḍ': 'd', 'Ḏ': 'D',
            'ḏ': 'd', 'Ḑ': 'D', 'ḑ': 'd', 'Ḓ': 'D', 'ḓ': 'd',
            'Ḕ': 'E', 'ḕ': 'e', 'Ḗ': 'E', 'ḗ': 'e', 'Ḙ': 'E',
            'ḙ': 'e', 'Ḛ': 'E', 'ḛ': 'e', 'Ḝ': 'E', 'ḝ': 'e',
            'Ḟ': 'F', 'ḟ': 'f', 'Ḡ': 'G', 'ḡ': 'g', 'Ḣ': 'H',
            'ḣ': 'h', 'Ḥ': 'H', 'ḥ': 'h', 'Ḧ': 'H', 'ḧ': 'h',
            'Ḩ': 'H', 'ḩ': 'h', 'Ḫ': 'H', 'ḫ': 'h', 'Ḭ': 'I',
            'ḭ': 'i', 'Ḯ': 'I', 'ḯ': 'i', 'Ḱ': 'K', 'ḱ': 'k',
            'Ḳ': 'K', 'ḳ': 'k', 'Ḵ': 'K', 'ḵ': 'k', 'Ḷ': 'L',
            'ḷ': 'l', 'Ḹ': 'L', 'ḹ': 'l', 'Ḻ': 'L', 'ḻ': 'l',
            'Ḽ': 'L', 'ḽ': 'l', 'Ḿ': 'M', 'ḿ': 'm', 'Ṁ': 'M',
            'ṁ': 'm', 'Ṃ': 'M', 'ṃ': 'm', 'Ṅ': 'N', 'ṅ': 'n',
            'Ṇ': 'N', 'ṇ': 'n', 'Ṉ': 'N', 'ṉ': 'n', 'Ṋ': 'N',
            'ṋ': 'n', 'Ṍ': 'O', 'ṍ': 'o', 'Ṏ': 'O', 'ṏ': 'o',
            'Ṑ': 'O', 'ṑ': 'o', 'Ṓ': 'O', 'ṓ': 'o', 'Ṕ': 'P',
            'ṕ': 'p', 'Ṗ': 'P', 'ṗ': 'p', 'Ṙ': 'R', 'ṙ': 'r',
            'Ṛ': 'R', 'ṛ': 'r', 'Ṝ': 'R', 'ṝ': 'r', 'Ṟ': 'R',
            'ṟ': 'r', 'Ṡ': 'S', 'ṡ': 's', 'Ṣ': 'S', 'ṣ': 's',
            'Ṥ': 'S', 'ṥ': 's', 'Ṧ': 'S', 'ṧ': 's', 'Ṩ': 'S',
            'ṩ': 's', 'Ṫ': 'T', 'ṫ': 't', 'Ṭ': 'T', 'ṭ': 't',
            'Ṯ': 'T', 'ṯ': 't', 'Ṱ': 'T', 'ṱ': 't', 'Ṳ': 'U',
            'ṳ': 'u', 'Ṵ': 'U', 'ṵ': 'u', 'Ṷ': 'U', 'ṷ': 'u',
            'Ṹ': 'U', 'ṹ': 'u', 'Ṻ': 'U', 'ṻ': 'u', 'Ṽ': 'V',
            'ṽ': 'v', 'Ṿ': 'V', 'ṿ': 'v', 'Ẁ': 'W', 'ẁ': 'w',
            'Ẃ': 'W', 'ẃ': 'w', 'Ẅ': 'W', 'ẅ': 'w', 'Ẇ': 'W',
            'ẇ': 'w', 'Ẉ': 'W', 'ẉ': 'w', 'Ẋ': 'X', 'ẋ': 'x',
            'Ẍ': 'X', 'ẍ': 'x', 'Ẏ': 'Y', 'ẏ': 'y', 'Ẑ': 'Z',
            'ẑ': 'z', 'Ẓ': 'Z', 'ẓ': 'z', 'Ẕ': 'Z', 'ẕ': 'z',
            'ẖ': 'h', 'ẗ': 't', 'ẘ': 'w', 'ẙ': 'y', 'ẚ': 'a',
            'ẛ': 's', 'ẜ': 's', 'ẝ': 's', 'ẞ': 'SS', 'ẟ': 'd',
            
            # Latin Extended-C, D, E (некоторые символы)
            'ꞌ': "'", 'Ɥ': 'H', 'ꞎ': 'l', 'ꞏ': '.', 'Ꞑ': 'N',
            'ꞑ': 'n', 'Ꞓ': 'C', 'ꞓ': 'c', 'ꞔ': 'c', 'ꞕ': 'h',
            'Ꞗ': 'B', 'ꞗ': 'b', 'Ꞙ': 'F', 'ꞙ': 'f', 'Ꞛ': 'V',
            'ꞛ': 'v', 'Ꞝ': 'V', 'ꞝ': 'v', 'Ꞟ': 'V', 'ꞟ': 'v',
            
            # Дополнительные символы с диакритикой
            'Ȁ': 'A', 'ȁ': 'a', 'Ȃ': 'A', 'ȃ': 'a', 'Ȅ': 'E',
            'ȅ': 'e', 'Ȇ': 'E', 'ȇ': 'e', 'Ȉ': 'I', 'ȉ': 'i',
            'Ȋ': 'I', 'ȋ': 'i', 'Ȍ': 'O', 'ȍ': 'o', 'Ȏ': 'O',
            'ȏ': 'o', 'Ȑ': 'R', 'ȑ': 'r', 'Ȓ': 'R', 'ȓ': 'r',
            'Ȕ': 'U', 'ȕ': 'u', 'Ȗ': 'U', 'ȗ': 'u', 'Ș': 'S',
            'ș': 's', 'Ț': 'T', 'ț': 't', 'Ȝ': 'Y', 'ȝ': 'y',
            'Ȟ': 'H', 'ȟ': 'h', 'Ƞ': 'N', 'ȡ': 'd', 'Ȣ': 'OU',
            'ȣ': 'ou', 'Ȥ': 'Z', 'ȥ': 'z', 'Ȧ': 'A', 'ȧ': 'a',
            'Ȩ': 'E', 'ȩ': 'e', 'Ȫ': 'O', 'ȫ': 'o', 'Ȭ': 'O',
            'ȭ': 'o', 'Ȯ': 'O', 'ȯ': 'o', 'Ȱ': 'O', 'ȱ': 'o',
            'Ȳ': 'Y', 'ȳ': 'y',
            
            # Символы пунктуации и другие символы Unicode
            # Все кавычки заменяем строго на апостроф '
            '…': '...',   # HORIZONTAL ELLIPSIS (U+2026)
            '«': "'",     # LEFT-POINTING DOUBLE ANGLE QUOTATION MARK (U+00AB) -> апостроф
            '»': "'",     # RIGHT-POINTING DOUBLE ANGLE QUOTATION MARK (U+00BB) -> апостроф
            '„': "'",     # DOUBLE LOW-9 QUOTATION MARK (U+201E) -> апостроф
            '“': "'",     # LEFT DOUBLE QUOTATION MARK (U+201C) -> апостроф
            '”': "'",     # RIGHT DOUBLE QUOTATION MARK (U+201D) -> апостроф
            '‘': "'",     # LEFT SINGLE QUOTATION MARK (U+2018) -> апостроф
            '’': "'",     # RIGHT SINGLE QUOTATION MARK (U+2019) -> апостроф
            '‹': "'",     # SINGLE LEFT-POINTING ANGLE QUOTATION MARK (U+2039) -> апостроф
            '›': "'",     # SINGLE RIGHT-POINTING ANGLE QUOTATION MARK (U+203A) -> апостроф
            '–': '-',     # EN DASH (U+2013)
            '—': '-',     # EM DASH (U+2014)
            '―': '-',     # HORIZONTAL BAR (U+2015)
            '‒': '-',     # FIGURE DASH (U+2012)
            '−': '-',     # MINUS SIGN (U+2212)
            '±': '+/-',   # PLUS-MINUS SIGN (U+00B1)
            '×': 'x',     # MULTIPLICATION SIGN (U+00D7)
            '÷': '/',     # DIVISION SIGN (U+00F7)
            '©': '(c)',   # COPYRIGHT SIGN (U+00A9)
            '®': '(R)',   # REGISTERED SIGN (U+00AE)
            '™': '(TM)',  # TRADE MARK SIGN (U+2122)
            '°': 'deg',   # DEGREE SIGN (U+00B0)
            '№': 'No.',   # NUMERO SIGN (U+2116)
            '§': 'S.',    # SECTION SIGN (U+00A7)
            '¶': 'P.',    # PILCROW SIGN (U+00B6)
            '†': '+',     # DAGGER (U+2020)
            '‡': '++',    # DOUBLE DAGGER (U+2021)
            '•': '*',     # BULLET (U+2022)
            '·': '.',     # MIDDLE DOT (U+00B7)
            '¿': '?',     # INVERTED QUESTION MARK (U+00BF)
            '¡': '!',     # INVERTED EXCLAMATION MARK (U+00A1)
            '¦': '|',     # BROKEN BAR (U+00A6)
            '¬': '-',     # NOT SIGN (U+00AC)
            'µ': 'u',     # MICRO SIGN (U+00B5)
            '€': 'EUR',   # EURO SIGN (U+20AC)
            '£': 'GBP',   # POUND SIGN (U+00A3)
            '¥': 'JPY',   # YEN SIGN (U+00A5)
            '¢': 'cent',  # CENT SIGN (U+00A2)
            'ƒ': 'f',     # LATIN SMALL LETTER F WITH HOOK (U+0192)
            '‰': '%o',    # PER MILLE SIGN (U+2030)
            '‱': '%oo',   # PER TEN THOUSAND SIGN (U+2031)
            '‽': '?!',    # INTERROBANG (U+203D)
            '※': '*',     # REFERENCE MARK (U+203B)
            '⁂': '***',   # ASTERISM (U+2042)
            '⁇': '??',    # DOUBLE QUESTION MARK (U+2047)
            '⁈': '?!',    # QUESTION EXCLAMATION MARK (U+2048)
            '⁉': '!?',    # EXCLAMATION QUESTION MARK (U+2049)
            '⁊': '&',     # TIRONIAN SIGN ET (U+204A)
            '⁋': 'P',     # REVERSED PILCROW SIGN (U+204B)
            '⁌': '<',     # BLACK LEFTWARDS BULLET (U+204C)
            '⁍': '>',     # BLACK RIGHTWARDS BULLET (U+204D)
            
            # Математические символы
            '¼': '1/4',   # VULGAR FRACTION ONE QUARTER (U+00BC)
            '½': '1/2',   # VULGAR FRACTION ONE HALF (U+00BD)
            '¾': '3/4',   # VULGAR FRACTION THREE QUARTERS (U+00BE)
            '⅓': '1/3',   # VULGAR FRACTION ONE THIRD (U+2153)
            '⅔': '2/3',   # VULGAR FRACTION TWO THIRDS (U+2154)
            '⅕': '1/5',   # VULGAR FRACTION ONE FIFTH (U+2155)
            '⅖': '2/5',   # VULGAR FRACTION TWO FIFTHS (U+2156)
            '⅗': '3/5',   # VULGAR FRACTION THREE FIFTHS (U+2157)
            '⅘': '4/5',   # VULGAR FRACTION FOUR FIFTHS (U+2158)
            '⅙': '1/6',   # VULGAR FRACTION ONE SIXTH (U+2159)
            '⅚': '5/6',   # VULGAR FRACTION FIVE SIXTHS (U+215A)
            '⅛': '1/8',   # VULGAR FRACTION ONE EIGHTH (U+215B)
            '⅜': '3/8',   # VULGAR FRACTION THREE EIGHTHS (U+215C)
            '⅝': '5/8',   # VULGAR FRACTION FIVE EIGHTHS (U+215D)
            '⅞': '7/8',   # VULGAR FRACTION SEVEN EIGHTHS (U+215E)
            
            # Другие символы
            '★': '*',     # BLACK STAR (U+2605)
            '☆': '*',     # WHITE STAR (U+2606)
            '☺': ':)',    # WHITE SMILING FACE (U+263A)
            '☹': ':(',    # WHITE FROWNING FACE (U+2639)
            '♡': '<3',    # WHITE HEART SUIT (U+2661)
            '♥': '<3',    # BLACK HEART SUIT (U+2665)
            '♦': '<>',    # BLACK DIAMOND SUIT (U+2666)
            '♣': 'cl',    # BLACK CLUB SUIT (U+2663)
            '♠': 'sp',    # BLACK SPADE SUIT (U+2660)
            '✓': 'V',     # CHECK MARK (U+2713)
            '✔': 'V',     # HEAVY CHECK MARK (U+2714)
            '✗': 'X',     # BALLOT X (U+2717)
            '✘': 'X',     # HEAVY BALLOT X (U+2718)
            '○': 'O',     # WHITE CIRCLE (U+25CB)
            '●': 'O',     # BLACK CIRCLE (U+25CF)
            '◎': '(O)',   # BULLSEYE (U+25CE)
            '◇': '<>',    # WHITE DIAMOND (U+25C7)
            '◆': '<>',    # BLACK DIAMOND (U+25C6)
            '□': '[]',    # WHITE SQUARE (U+25A1)
            '■': '[]',    # BLACK SQUARE (U+25A0)
            '△': '/_\\',  # WHITE UP-POINTING TRIANGLE (U+25B3)
            '▲': '/_\\',  # BLACK UP-POINTING TRIANGLE (U+25B2)
            '▽': '\\_/',  # WHITE DOWN-POINTING TRIANGLE (U+25BD)
            '▼': '\\_/',  # BLACK DOWN-POINTING TRIANGLE (U+25BC)
            '→': '->',    # RIGHTWARDS ARROW (U+2192)
            '←': '<-',    # LEFTWARDS ARROW (U+2190)
            '↑': '^',     # UPWARDS ARROW (U+2191)
            '↓': 'v',     # DOWNWARDS ARROW (U+2193)
            '↔': '<->',   # LEFT RIGHT ARROW (U+2194)
            '↕': '^v',    # UP DOWN ARROW (U+2195)
            '↵': '<-',    # DOWNWARDS ARROW WITH CORNER LEFTWARDS (U+21B5)
            '⇄': '<->',   # RIGHTWARDS ARROW OVER LEFTWARDS ARROW (U+21C4)
            '⇅': '^v',    # UPWARDS ARROW LEFT OF DOWNWARDS ARROW (U+21C5)
            '⇆': '<->',   # LEFTWARDS ARROW OVER RIGHTWARDS ARROW (U+21C6)
            
            # Кириллические символы для других языков (не русский/украинский/болгарский)
            'Ђ': 'Dj',    # CYRILLIC CAPITAL LETTER DJE (U+0402) - сербский
            'ђ': 'dj',    # CYRILLIC SMALL LETTER DJE (U+0452) - сербский
            'Љ': 'Lj',    # CYRILLIC CAPITAL LETTER LJE (U+0409) - сербский/македонский
            'љ': 'lj',    # CYRILLIC SMALL LETTER LJE (U+0459) - сербский/македонский
            'Њ': 'Nj',    # CYRILLIC CAPITAL LETTER NJE (U+040A) - сербский/македонский
            'њ': 'nj',    # CYRILLIC SMALL LETTER NJE (U+045A) - сербский/македонский
            'Ћ': 'C',     # CYRILLIC CAPITAL LETTER TSHE (U+040B) - сербский
            'ћ': 'c',     # CYRILLIC SMALL LETTER TSHE (U+045B) - сербский
            'Џ': 'Dz',    # CYRILLIC CAPITAL LETTER DZHE (U+040F) - сербский/македонский
            'џ': 'dz',    # CYRILLIC SMALL LETTER DZHE (U+045F) - сербский/македонский
            'Ѕ': 'Dz',    # CYRILLIC CAPITAL LETTER DZE (U+0405) - македонский
            'ѕ': 'dz',    # CYRILLIC SMALL LETTER DZE (U+0455) - македонский
            'Ѣ': 'E',     # CYRILLIC CAPITAL LETTER YAT (U+0462) - старославянский
            'ѣ': 'e',     # CYRILLIC SMALL LETTER YAT (U+0463) - старославянский
            'Ѥ': 'Je',    # CYRILLIC CAPITAL LETTER IOTIFIED E (U+0464) - старославянский
            'ѥ': 'je',    # CYRILLIC SMALL LETTER IOTIFIED E (U+0465) - старославянский
            'Ѧ': 'Ja',    # CYRILLIC CAPITAL LETTER LITTLE YUS (U+0466) - старославянский
            'ѧ': 'ja',    # CYRILLIC SMALL LETTER LITTLE YUS (U+0467) - старославянский
            'Ѩ': 'Jja',   # CYRILLIC CAPITAL LETTER IOTIFIED LITTLE YUS (U+0468) - старославянский
            'ѩ': 'jja',   # CYRILLIC SMALL LETTER IOTIFIED LITTLE YUS (U+0469) - старославянский
            'Ѫ': 'O',     # CYRILLIC CAPITAL LETTER BIG YUS (U+046A) - старославянский
            'ѫ': 'o',     # CYRILLIC SMALL LETTER BIG YUS (U+046B) - старославянский
            'Ѭ': 'Jo',    # CYRILLIC CAPITAL LETTER IOTIFIED BIG YUS (U+046C) - старославянский
            'ѭ': 'jo',    # CYRILLIC SMALL LETTER IOTIFIED BIG YUS (U+046D) - старославянский
            'Ѯ': 'Ks',    # CYRILLIC CAPITAL LETTER KSI (U+046E) - старославянский
            'ѯ': 'ks',    # CYRILLIC SMALL LETTER KSI (U+046F) - старославянский
            'Ѱ': 'Ps',    # CYRILLIC CAPITAL LETTER PSI (U+0470) - старославянский
            'ѱ': 'ps',    # CYRILLIC SMALL LETTER PSI (U+0471) - старославянский
            'Ѳ': 'F',     # CYRILLIC CAPITAL LETTER FITA (U+0472) - старославянский
            'ѳ': 'f',     # CYRILLIC SMALL LETTER FITA (U+0473) - старославянский
            'Ѵ': 'I',     # CYRILLIC CAPITAL LETTER IZHITSA (U+0474) - старославянский
            'ѵ': 'i',     # CYRILLIC SMALL LETTER IZHITSA (U+0475) - старославянский
            'Ѷ': 'I',     # CYRILLIC CAPITAL LETTER IZHITSA WITH DOUBLE GRAVE ACCENT (U+0476) - старославянский
            'ѷ': 'i',     # CYRILLIC SMALL LETTER IZHITSA WITH DOUBLE GRAVE ACCENT (U+0477) - старославянский
        }
        
        # Добавляем расширенную кириллицу в русскую и европейскую таблицы
        self._add_extra_cyrillic(russian_table)
        self._add_extra_cyrillic(european_table)

        # Добавляем декоративные латинские и коптские символы в русскую (встречено in the wild) и европейскую таблицы
        self._add_decorative_latin(russian_table)
        self._add_decorative_latin(european_table)
        
        # Добавляем общие символы пунктуации ко всем таблицам
        # Все кавычки заменяем строго на апостроф, звездочки на подчеркивание
        common_punctuation = {
            '…': '...',   # Многоточие
            '–': '-',     # Длинное тире
            '—': '-',     # Длинное тире
            '«': "'",     # Левая кавычка -> апостроф
            '»': "'",     # Правая кавычка -> апостроф
            '„': "'",     # Нижняя кавычка -> апостроф
            '"': "'",     # Двойная кавычка -> апостроф
            '“': "'",     # Левая кавычка -> апостроф
            '”': "'",     # Правая кавычка -> апостроф
            '‘': "'",     # Левая одинарная кавычка -> апостроф
            '’': "'",     # Правая одинарная кавычка -> апостроф
            '‹': "'",     # Левая угловая кавычка -> апостроф
            '›': "'",     # Правая угловая кавычка -> апостроф
            '/': '_',     # Слэш -> подчеркивание
            '\\': '_',    # Обратный слэш -> подчеркивание
            ':': '_',     # Двоеточие -> подчеркивание
            '|': '_',     # Вертикальная черта -> подчеркивание
            '?': '_',     # Вопросительный знак -> подчеркивание
            '*': '_',     # Звездочка -> подчеркивание
            '<': '_',     # Меньше -> подчеркивание
            '>': '_',     # Больше -> подчеркивание
        }
        
        # Объединяем таблицы с общими символами пунктуации
        russian_table.update(common_punctuation)
        ukrainian_table.update(common_punctuation)
        polish_table.update(common_punctuation)
        bulgarian_table.update(common_punctuation)
        german_table.update(common_punctuation)
        
        # Для европейской таблицы добавляем еще больше символов
        european_table.update(common_punctuation)

        # Добавляем базовую кириллицу из русской таблицы в европейскую (встречается смесь)
        european_table.update(russian_table)

        return {
            'russian': russian_table,
            'ukrainian': ukrainian_table,
            'polish': polish_table,
            'bulgarian': bulgarian_table,
            'german': german_table,
            'european': european_table
        }