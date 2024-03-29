#!/usr/bin/env python3
import os
import json
import re
from typing import List, Tuple, Dict

from ucd.unicode import UNICODE_VERSION_MAJOR, UNICODE_VERSION_MINOR, UNICODE_VERSION_UPDATE
from ucd.unicode import EMOJI_VERSION_MAJOR, EMOJI_VERSION_MINOR
from ucd.collections import CodePointRange, TwoStageTable, Missing


UNICODE_DATA_DIR = 'data/{}.{}.{}'.format(
    UNICODE_VERSION_MAJOR,
    UNICODE_VERSION_MINOR,
    UNICODE_VERSION_UPDATE
)

property_info = {
    'bc': {
        'repr_size': 1,
        'alias_key': 'bc',
    },
    'gc': {
        'repr_size': 1,
        'alias_key': 'gc',
    },
    'hst': {
        'repr_size': 1,
        'alias_key': 'hst',
    },
    'gcb': {
        'repr_size': 1,
        'alias_key': 'GCB',
    },
    'ccc': {
        'repr_size': 1,
        'alias_key': 'ccc',
    },
    'dt': {
        'repr_size': 1,
    },
    'blk': {
        'repr_size': 2,
    },
    'sc': {
        'repr_size': 1,
    },
    'age': {
        'repr_size': 1,
    },
    'wb': {
        'repr_size': 1,
    },
    'insc': {
        'repr_size': 1,
        'alias_key': 'InSC',
    },
}

# Unicode Table 4-8.
# List of the ranges that na (Name) property is derived from it's code point or
# special derivation rule (currently only for hangul).
derived_na_ranges = [
    CodePointRange.parse('AC00..D7A3'),     # HANGUL SYLLABLE
    CodePointRange.parse('3400..4DBF'),     # CJK UNIFIED IDEOGRAPH-
    CodePointRange.parse('4E00..9FFF'),     # CJK UNIFIED IDEOGRAPH-
    CodePointRange.parse('20000..2A6DF'),   # CJK UNIFIED IDEOGRAPH-
    CodePointRange.parse('2A700..2B739'),   # CJK UNIFIED IDEOGRAPH-
    CodePointRange.parse('2B740..2B81D'),   # CJK UNIFIED IDEOGRAPH-
    CodePointRange.parse('2B820..2CEA1'),   # CJK UNIFIED IDEOGRAPH-
    CodePointRange.parse('2CEB0..2EBE0'),   # CJK UNIFIED IDEOGRAPH-
    CodePointRange.parse('2EBF0..2EE5D'),   # Added from 15.1.0. Not listed in the table.
    CodePointRange.parse('30000..3134A'),   # CJK UNIFIED IDEOGRAPH-
    CodePointRange.parse('31350..323AF'),   # CJK UNIFIED IDEOGRAPH-
    CodePointRange.parse('17000..187F7'),   # TANGUT IDEOGRAPH-
    CodePointRange.parse('18D00..18D08'),   # TANGUT IDEOGRAPH-
    CodePointRange.parse('18B00..18CD5'),   # KHITAN SMALL SCRIPT CHARACTER-
    CodePointRange.parse('1B170..1B2FB'),   # NUSHU CHARACTER-
    CodePointRange.parse('F900..FA6D'),     # CJK COMPATIBILITY IDEOGRAPH-
    CodePointRange.parse('FA70..FAD9'),     # CJK COMPATIBILITY IDEOGRAPH-
    CodePointRange.parse('2F800..2FA1D'),   # CJK COMPATIBILITY IDEOGRAPH-
]


with open(os.path.join(UNICODE_DATA_DIR, 'PropertyAliases.json')) as f:
    property_aliases = json.load(f)

with open(os.path.join(UNICODE_DATA_DIR, 'PropertyValueAliases.json')) as f:
    property_value_aliases = json.load(f)


def find_key_by_value(d: Dict, val: str) -> str:
    for k, v in d.items():
        if v == val:
            return k


def find_key_by_value_ci(d: Dict, val: str) -> str:
    """Case insensitive version of find_key_by_value function."""
    for k, v in d.items():
        value = val.replace('-', ' ')
        value = value.replace('_', ' ')
        value = value.upper()

        cmp_val = v.replace('_', ' ')
        cmp_val = cmp_val.replace('-', ' ')
        cmp_val = cmp_val.upper()

        if value == cmp_val:
            return k


def to_snake_case(val: str):
    if val == 'ExtPict':
        return 'ext_pict'

    return val.lower()


def to_pascal_case(val: str) -> str:
    """Convert underscore_delimitered_string to PacalCase string."""
    words = val.split('_')
    result = ''.join(list(map(lambda x: x.title(), words)))

    return result


def str_as_escaped(s: str) -> str:
    escaped = ''
    for ch in s:
        escaped += '\\u{{{:04X}}}'.format(ord(ch))

    return escaped


def data_value_as_abbr(data: List[Tuple[CodePointRange, str]], prop: str):
    """Some property data file using (range, full_name) pair instead of (range, abbr_name).
This function converts these data to abbr version."""
    aliases = property_value_aliases[prop]
    new_data = []
    for pair in data:
        new_pair = (pair[0], find_key_by_value(aliases, pair[1]))
        new_data.append(new_pair)

    return new_data


def data_value_as_abbr_ccc(data: List[Tuple[CodePointRange, str]]):
    aliases = property_value_aliases['ccc']
    new_data = []
    for pair in data:
        new_pair = (pair[0], aliases[pair[1]])
        new_data.append(new_pair)

    return new_data


def data_value_as_abbr_blk(data: List[Tuple[CodePointRange, str]]):
    """Specialized version function for Block property."""
    aliases = property_value_aliases['blk']
    new_data = []
    for pair in data:
        # Replace all delimiter to underscore.
        value = pair[1].replace(' ', '_')
        value = value.replace('-', '_')

        key = find_key_by_value_ci(aliases, value)

        new_pair = (pair[0], to_pascal_case(key))
        new_data.append(new_pair)

    return new_data


def select_minimal_tst(prop: str, data: List[Tuple[CodePointRange, str]],
        repr_size: int, default_prop: str=None,
        missing: Missing=None) -> TwoStageTable:
    print('Select minimal table for: {}'.format(prop))
    tables = {64: None, 128: None, 256: None, 512: None}
    for block_size in tables.keys():
        tst = TwoStageTable.make(prop, data, block_size, default_prop, missing)
        print('Block size {}: {}'.format(block_size, tst.table_bytes(repr_size)))
        tables[block_size] = tst
    print('----------------------------')

    return min(tables.values(), key=lambda x: x.table_bytes(repr_size))


def make_data(filename: str):
    """Make data used by argument of two-stage table.
filename: str - Path of JSON file."""
    filename = os.path.join(UNICODE_DATA_DIR, filename)
    f = open(filename)
    json_str = f.read()
    f.close()
    d = json.loads(json_str)
    data = []
    for k, v in d.items():
        cp_range = CodePointRange.parse(k)
        data.append((cp_range, v))
    data = sorted(data, key=lambda x: x[0])

    return data


def patch_data(filename: str, prop: str) -> Missing:
    filename = os.path.join(UNICODE_DATA_DIR, filename)
    f = open(filename)
    json_str = f.read()
    f.close()

    alias_key = property_info[prop]['alias_key']

    d = json.loads(json_str)
    missing = Missing()
    for k, v in d.items():
        alias = find_key_by_value(property_value_aliases[alias_key], v)
        cp_range = CodePointRange.parse(k)
        missing.append(cp_range, alias)

    return missing



def to_age_data(data: List[Tuple[CodePointRange, str]]):
    """Use this function after make_data for age property."""
    new_data = []
    for pair in data:
        ver = pair[1].split('.')
        new_data.append((pair[0], 'V{}_{}'.format(ver[0], ver[1])))

    return new_data


def make_grouped_data(filename: str):
    """e.g. emoji/emoji-data.json"""
    filename = os.path.join(UNICODE_DATA_DIR, filename)
    f = open(filename)
    json_str = f.read()
    f.close()
    d = json.loads(json_str)
    data_dict = {}
    for prop, ranges in d.items():
        data_dict[prop] = []
        for rng in ranges:
            rng = CodePointRange.parse(rng)
            data_dict[prop].append((rng, "true"))
        data_dict[prop] = sorted(data_dict[prop], key=lambda x: x[0])

    return data_dict


def binary_props_rs() -> str:
    filename = os.path.join(UNICODE_DATA_DIR, 'PropList.json')
    f = open(filename)
    json_str = f.read()
    f.close()
    d = json.loads(json_str)
    txt = ''
    prev_prop = ''
    for k, ranges in d.items():
        # Closing function.
        if prev_prop != k and prev_prop != '':
            txt += '\n    false\n'
            txt += '}\n\n'
        # Opening function.
        if prev_prop != k:
            fn_name = ''
            for alias, long in property_aliases.items():
                if long == k:
                    fn_name = to_snake_case(alias)
            txt += 'pub(crate) fn {fn_name}(cp: u32) -> bool {{\n'.format(fn_name=fn_name)
        for r in ranges:
            r = CodePointRange.parse(r)
            txt += '    if (0x{:04X}..0x{:04X} + 1).contains(&cp) {{\n'.format(r.start, r.end)
            txt += '        return true;\n'
            txt += '    }\n'
        prev_prop = k
    txt += '\n    false\n'
    txt += '}\n'

    return txt


def na_table_rs() -> str:
    # Unicode Table 4-8.
    filename = os.path.join(UNICODE_DATA_DIR, 'extracted/DerivedName.json')
    f = open(filename)
    json_str = f.read()
    f.close()
    d = json.loads(json_str)
    txt = '#[allow(dead_code)]\n'
    txt += 'pub(super) const NA_MAP: &[(u32, &\'static str)] = &[\n'
    for k, name in d.items():
        cp = CodePointRange.parse(k).start
        # Ignore if in the derivation ranges.
        ignore = False
        for rng in derived_na_ranges:
            if cp in rng:
                ignore = True
        # Add to the table.
        if ignore is False:
            txt += '    (0x{:04X}, "{}"),\n'.format(cp, name)
    txt += '];\n'

    return txt


def dm_map_rs():
    filename = os.path.join(UNICODE_DATA_DIR, 'UnicodeData.json')
    with open(filename) as f:
        json_str = f.read()
    unicode_data = json.loads(json_str)
    # Make DM_MAP.
    txt = 'pub(super) const DM_MAP: &[(u32, &str)] = &[\n'
    for k, props in unicode_data.items():
        dm_raw = props['dm']
        if dm_raw == '':
            continue
        cp = CodePointRange.parse(k)
        # Make dm_raw to str.
        if dm_raw.startswith('<'):
            dm_raw = re.sub('<.+> ', '', dm_raw)
        dm_str = ''
        for code in dm_raw.split(' '):
            dm_str += '\\u{{{}}}'.format(code)
        txt += '    (0x{:04X}, "{}"),\n'.format(cp.start, dm_str)
    txt += '];\n\n'
    # Make RDM_MAP.
    rdm_list = []
    txt += 'pub(super) const RDM_MAP: &[(&str, u32)] = &[\n'
    for k, props in unicode_data.items():
        dm_raw = props['dm']
        if dm_raw == '':
            continue
        if dm_raw.startswith('<'):
            continue
            dm_raw = re.sub('<.+> ', '', dm_raw)
        dm_str = ''.join(map(lambda x: chr(int(x, 16)), dm_raw.split(' ')))
        rdm_list.append((dm_str, k))
    rdm_list = sorted(rdm_list, key=lambda x: x[0])
    for pair in rdm_list:
        txt += '    ("{}", 0x{}),\n'.format(str_as_escaped(pair[0]), pair[1])
    txt += '];\n'

    return txt


def normalization_props_data_rs():
    filename = os.path.join(UNICODE_DATA_DIR, 'DerivedNormalizationProps.json')
    with open(filename) as f:
        json_str = f.read()
    normalization_props_data = json.loads(json_str)
    # Comp_Ex (Full_Composition_Exclusion)
    # NFD_QC


def ce_rs():
    filename = os.path.join(UNICODE_DATA_DIR, 'CompositionExclusions.json')
    with open(filename) as f:
        json_str = f.read()
    ce_data = json.loads(json_str)
    txt = 'const CE_LIST: &[u32] = &[\n'
    for code in ce_data:
        txt += '    0x{:04X},\n'.format(CodePointRange.parse(code).start)
    txt += '];\n\n'
    txt += 'pub(crate) fn ce(cp: u32) -> bool {\n'
    txt += '    if CE_LIST.contains(&cp) {\n'
    txt += '        return true;\n'
    txt += '    }\n'
    txt += '    false\n'
    txt += '}\n'
    return txt


if __name__ == '__main__':
    from pprint import pprint

    # Make gc data.
    gc_data = make_data('extracted/DerivedGeneralCategory.json')
    tst = select_minimal_tst('Gc', gc_data, property_info['gc']['repr_size'])
    f = open('../../src/unicode/ucd/gc.rs', 'w')
    f.write(tst.to_seshat())
    f.close()
    # Make blk data.
    blk_data = make_data('Blocks.json')
    blk_data = data_value_as_abbr_blk(blk_data)
    tst = select_minimal_tst('Blk', blk_data, property_info['blk']['repr_size'], default_prop='Nb')
    f = open('../../src/unicode/ucd/blk.rs', 'w')
    f.write(tst.to_seshat())
    f.close()
    # Make sc data.
    sc_data = make_data('Scripts.json')
    sc_data = data_value_as_abbr(sc_data, 'sc')
    tst = select_minimal_tst('Sc', sc_data, property_info['sc']['repr_size'], default_prop='Zzzz')
    f = open('../../src/unicode/ucd/sc.rs', 'w')
    f.write(tst.to_seshat())
    f.close()
    # Make age data.
    age_data = make_data('DerivedAge.json')
    age_data = to_age_data(age_data)
    tst = select_minimal_tst('Age', age_data, property_info['age']['repr_size'], default_prop='NA')
    f = open('../../src/unicode/ucd/age.rs', 'w')
    f.write(tst.to_seshat())
    f.close()
    # Make binary properties data.
    f = open('../../src/unicode/ucd/binary_props.rs', 'w')
    f.write(binary_props_rs())
    f.close()
    # Make na data table.
    f = open('../../src/unicode/ucd/na/na_table.rs', 'w')
    f.write(na_table_rs())
    f.close()
    # Make hst properties data.
    hst_data = make_data('HangulSyllableType.json')
    tst = select_minimal_tst('Hst', hst_data, property_info['hst']['repr_size'], default_prop='NA')
    f = open('../../src/unicode/ucd/hst.rs', 'w')
    f.write(tst.to_seshat())
    f.close()
    # Make Emoji data properties data.
    emoji_props_rs = ''
    emoji_data_dict = make_grouped_data('emoji/emoji-data.json')
    for i, prop in enumerate(emoji_data_dict.keys()):
        use = False
        if i == 0:
            use = True
        prop_alias = to_snake_case(find_key_by_value(property_aliases, prop))
        tst = select_minimal_tst(prop_alias, emoji_data_dict[prop], 1, default_prop='false')
        emoji_props_rs += tst.to_seshat(use=use, prefix=True, boolean=True)
    with open('../../src/unicode/ucd/emoji_props.rs', 'w') as f:
        f.write(emoji_props_rs)
    # Make GCB data.
    gcb_data = make_data('auxiliary/GraphemeBreakProperty.json')
    gcb_data = data_value_as_abbr(gcb_data, "GCB")
    tst = select_minimal_tst('Gcb', gcb_data, property_info['gcb']['repr_size'], default_prop='XX')
    with open('../../src/unicode/ucd/gcb.rs', 'w') as f:
        f.write(tst.to_seshat())
    # Make bc data.
    bc_data = make_data('extracted/DerivedBidiClass.json')
    bc_missing = patch_data('extracted/DerivedBidiClass.missing.json', 'bc')
    tst = select_minimal_tst('Bc', bc_data, property_info['bc']['repr_size'], default_prop='L', missing=bc_missing)
    with open('../../src/unicode/ucd/bc.rs', 'w') as f:
        f.write(tst.to_seshat())
    # Make ccc data.
    ccc_data = make_data('extracted/DerivedCombiningClass.json')
    ccc_data = data_value_as_abbr_ccc(ccc_data)
    tst = select_minimal_tst('Ccc', ccc_data, property_info['ccc']['repr_size'], default_prop='NR')
    with open('../../src/unicode/ucd/ccc.rs', 'w') as f:
        f.write(tst.to_seshat())
    # Make dt data.
    dt_data = make_data('extracted/DerivedDecompositionType.json')
    dt_data = data_value_as_abbr(dt_data, 'dt')
    tst = select_minimal_tst('Dt', dt_data, property_info['dt']['repr_size'], default_prop='None')
    with open('../../src/unicode/ucd/dt.rs', 'w') as f:
        f.write(tst.to_seshat())
    # Make dm data.
    with open('../../src/unicode/ucd/dm/dm_map.rs', 'w') as f:
        f.write(dm_map_rs())
    # Make CE data.
    with open('../../src/unicode/ucd/ce.rs', 'w') as f:
        f.write(ce_rs())
    # Make WB data.
    wb_data = make_data('auxiliary/WordBreakProperty.json')
    wb_data = data_value_as_abbr(wb_data, 'WB')
    tst = select_minimal_tst('Wb', wb_data, property_info['wb']['repr_size'],
        default_prop='XX')
    with open('../../src/unicode/ucd/wb.rs', 'w') as f:
        f.write(tst.to_seshat())
    # Make InSC data.
    insc_data = make_data('IndicSyllabicCategory.json')
    tst = select_minimal_tst('Insc', insc_data, property_info['insc']['repr_size'],
        default_prop='Other')
    with open('../../src/unicode/ucd/insc.rs', 'w') as f:
        f.write(tst.to_seshat())
