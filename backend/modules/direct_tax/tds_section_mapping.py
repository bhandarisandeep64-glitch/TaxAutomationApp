# ==========================================
#  Income Tax Act 2025 section mapping
# ==========================================
#
# The old TDS section numbers (194C, 194J, ...) were replaced by a new
# section/table-item structure with numeric TRACES codes. Shared between
# tds_zoho.py and tds_odoo.py so both engines apply exactly the same rules.
#
# Some old sections split into multiple new codes depending on the nature of
# payment -- the "Rate at which deducted" column disambiguates those
# (confirmed with the firm against their own new-section/code/rate table),
# since that's the only distinguishing signal available in either an Odoo
# or Zoho export.
#
# 194J's 10% bucket covers both "Professional services" (1027) and "Director
# remuneration/fees" (1028) under the real table -- the firm confirmed every
# 194J-at-10% row should code to 1027 (Professional services) here, so 1028
# is deliberately not represented. 194R and 194S are out of scope entirely
# (multiple codes with no distinguishing data available) and are left
# unmapped rather than guessed.

# Sections with a single new code regardless of rate.
SECTION_FIXED_MAPPING = {
    '194H': {'new_section': '393(1), Sl. 1(ii)', 'code': '1006'},
    '194M': {'new_section': '393(1), Sl. 6(ii)', 'code': '1025'},
    '194': {'new_section': '393(1), Sl. 7', 'code': '1029'},
    '194DA': {'new_section': '393(1), Sl. 8(i)', 'code': '1030'},
    '194Q': {'new_section': '393(1), Sl. 8(ii)', 'code': '1031'},
    '194P': {'new_section': '393(1), Sl. 8(iii)', 'code': '1032'},
    '194O': {'new_section': '393(1), Sl. 8(v)', 'code': '1035'},
    '194T': {'new_section': '393(3), Sl. 7', 'code': '1067'},
}

# Sections where the rate at which TDS was deducted disambiguates which new
# code applies (keyed by (old section, rate rounded to 2 decimals)).
SECTION_RATE_MAPPING = {
    ('194C', 1.0): {'new_section': '393(1), Sl. 6(i).D(a)', 'code': '1023'},   # Contractor - Individual/HUF
    ('194C', 2.0): {'new_section': '393(1), Sl. 6(i).D(b)', 'code': '1024'},   # Contractor - Others
    ('194J', 2.0): {'new_section': '393(1), Sl. 6(iii).D(a)', 'code': '1026'}, # Technical services/call centres/film royalty
    ('194J', 10.0): {'new_section': '393(1), Sl. 6(iii).D(b)', 'code': '1027'},# Professional services
}


def lookup_new_section(old_section, rate):
    """Returns (new_section, code) for a row, or ('', '') if this old
    section/rate combination isn't in the mapping (e.g. 194R, 194S, or
    anything not yet confirmed)."""
    key = str(old_section or '').strip().upper()
    if key in SECTION_FIXED_MAPPING:
        m = SECTION_FIXED_MAPPING[key]
        return m['new_section'], m['code']
    try:
        rate_key = (key, round(float(rate), 2))
    except (TypeError, ValueError):
        return '', ''
    m = SECTION_RATE_MAPPING.get(rate_key)
    return (m['new_section'], m['code']) if m else ('', '')
