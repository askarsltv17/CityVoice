import re


BAD_WORD_PATTERNS = [
  r"\b(?:наху[йяиею]|нахер|нафиг)\w*\b",
  r"\b(?:хуй|хуя|хуе|хуи|хер|хрен|хуйн)\w*\b",
  r"\b(?:пизд|пезд)\w*\b",
  r"\b(?:еб|ёб|ебл|еба|ебн)\w*\b",
  r"\b(?:бля|бляд|блеа)\w*\b",
  r"\b(?:сука|сучк)\w*\b",
  r"\b(?:мудак|мудил)\w*\b",
  r"\b(?:долбоеб|долбоёб)\w*\b",
  r"\b(?:уеб|уёб)\w*\b",
  r"\b(?:гандон|пидор|пидр)\w*\b",
  r"\b(?:пидорас|член|педофил)\w*\b",
  r"\b(?:гей|лесбианка|ахмед)\w*\b",
]

BAD_WORDS_RE = re.compile("|".join(BAD_WORD_PATTERNS), re.IGNORECASE)


def contains_bad_words(text: str) -> bool:
  normalized = (text or "").lower().replace("ё", "е")
  normalized = re.sub(r"[^а-яa-z0-9]+", " ", normalized)
  return bool(BAD_WORDS_RE.search(normalized))
