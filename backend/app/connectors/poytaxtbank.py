"""poytaxtbank.uz — jismoniy shaxslar uchun omonat/kredit. turonbank.uz
bilan bir xil Bitrix shablonini (".item"/".item__info") ishlatadi, shu
bois uning parserini qayta ishlatamiz."""

from app.connectors.turonbank import TuronbankConnector


class PoytaxtbankConnector(TuronbankConnector):
    bank_code = "POYTAXT"
    source = "poytaxtbank.uz"
