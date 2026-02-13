import description_normalizer as dn


def test_normalize_description_expands_abbreviation_and_accents():
    assert dn.normalize_description("TRANSF DEBITO COMISION") == "Transferencia Débito Comisión"


def test_normalize_description_canonicalizes_fintech_variants():
    assert dn.normalize_description("merpago netflix 12345") == "MercadoPago Netflix"
    assert dn.normalize_description("mercado pago oxxo") == "MercadoPago Oxxo"


def test_normalize_description_preserves_known_acronyms():
    assert dn.normalize_description("pago spei iva rfc") == "Pago SPEI IVA RFC"


def test_normalize_description_is_deterministic_and_idempotent():
    raw = "  MERPAGO   TRANSF   DEBITO  "
    once = dn.normalize_description(raw)
    twice = dn.normalize_description(raw)
    assert once == twice
    assert dn.normalize_description(once) == once


def test_normalize_tokens_removes_trailing_reference_noise():
    toks = ["NETFLIX", "MEXICO", "12345", "67890"]
    out = dn.normalize_tokens(toks)
    assert out == ["Netflix", "Mexico"]
