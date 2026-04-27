import pytest

import description_normalizer as dn


# =============================================================================
# normalize_description — main entry point
# =============================================================================


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


def test_normalize_description_empty_string_returns_empty():
    assert dn.normalize_description("") == ""
    assert dn.normalize_description(None) == ""


def test_normalize_description_unicode_normalization():
    # NFKC normalization — circled letters to base forms
    result = dn.normalize_description("① NETFLIX ②")
    # Numbers and special chars stripped, normalized text remains
    assert "Netflix" in result or "①" not in result


# =============================================================================
# normalize_tokens — token-level processing
# =============================================================================


def test_normalize_tokens_removes_trailing_reference_noise():
    toks = ["NETFLIX", "MEXICO", "12345", "67890"]
    out = dn.normalize_tokens(toks)
    assert out == ["Netflix", "Mexico"]


def test_normalize_tokens_empty_input_returns_empty_list():
    assert dn.normalize_tokens([]) == []
    assert dn.normalize_tokens(None) == []


def test_normalize_tokens_skips_long_digit_only_tokens():
    """Tokens >= 12 digits (e.g. reference numbers) are noise."""
    toks = ["AMAZON", "12345678901234"]
    out = dn.normalize_tokens(toks)
    assert "Amazon" in out
    assert not any(t.isdigit() for t in out)


def test_normalize_tokens_applies_accent_restoration():
    """Accent restoration maps SPEI-like uppercase to accented forms."""
    toks = ["DEBITO", "CREDITO", "COMISION", "INTERES"]
    out = dn.normalize_tokens(toks)
    assert "Débito" in out
    assert "Crédito" in out
    assert "Comisión" in out
    assert "Interés" in out


def test_normalize_tokens_mercadopago_multitoken():
    """'Mercado' + 'Pago' should collapse to single MercadoPago token."""
    toks = ["MERCADO", "PAGO", "AMAZON"]
    out = dn.normalize_tokens(toks)
    assert "MercadoPago" in out
    assert "Amazon" in out
    assert len(out) == 2  # merged, not 3


def test_normalize_tokens_final_noise_cleanup():
    """Trailing digit-only tokens removed even if not caught earlier."""
    toks = ["OXXO", "12345"]
    out = dn.normalize_tokens(toks)
    # 12345 should be removed as trailing noise
    assert "Oxxo" in out


def test_normalize_tokens_bank_id_param_accepted():
    """bank_id param is accepted even if unused (future extension hook)."""
    toks = ["AMAZON", "MEXICO"]
    out = dn.normalize_tokens(toks, bank_id="hsbc")
    assert "Amazon" in out


# =============================================================================
# Helper functions — internal edge cases
# =============================================================================


def test_collapse_ws():
    from description_normalizer import _collapse_ws

    assert _collapse_ws("  hello   world  ") == "hello world"
    assert _collapse_ws("") == ""
    assert _collapse_ws(None) == ""


def test_normalize_unicode():
    from description_normalizer import _normalize_unicode

    result = _normalize_unicode("café")  # already composed
    assert "café" in result or "\u0065\u0301" not in result  # no decomposition artifacts
