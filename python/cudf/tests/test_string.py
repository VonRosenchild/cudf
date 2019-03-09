# Copyright (c) 2018, NVIDIA CORPORATION.

import pytest
from contextlib import ExitStack as does_not_raise

import numpy as np
import pandas as pd
import pyarrow as pa
from numba import cuda

from cudf import concat
from cudf.dataframe import DataFrame, Series
from cudf.tests.utils import assert_eq
from librmm_cffi import librmm as rmm


data_list = [
    ['AbC', 'de', 'FGHI', 'j', 'kLm'],
    ['nOPq', None, 'RsT', None, 'uVw'],
    [None, None, None, None, None]
]

data_id_list = [
    "no_nulls",
    "some_nulls",
    "all_nulls"
]

idx_list = [
    None,
    [10, 11, 12, 13, 14]
]

idx_id_list = [
    "None_index",
    "Set_index"
]


def raise_builder(flags, exceptions):
    if any(flags):
        return pytest.raises(exceptions)
    else:
        return does_not_raise()


@pytest.fixture(params=data_list, ids=data_id_list)
def data(request):
    return request.param


@pytest.fixture(params=idx_list, ids=idx_id_list)
def index(request):
    return request.param


@pytest.fixture
def ps_gs(data, index):
    ps = pd.Series(data, index=index, dtype='str')
    gs = Series(data, index=index, dtype='str')
    return (ps, gs)


@pytest.mark.parametrize('construct', [list, np.array, pd.Series, pa.array])
def test_string_ingest(construct):
    expect = ['a', 'a', 'b', 'c', 'a']
    data = construct(expect)
    got = Series(data)
    assert got.dtype == np.dtype('object')
    assert len(got) == 5
    for idx, val in enumerate(expect):
        assert expect[idx] == got[idx]


def test_string_export(ps_gs):
    ps, gs = ps_gs

    expect = ps
    got = gs.to_pandas()
    pd.testing.assert_series_equal(expect, got)

    expect = np.array(ps)
    got = gs.to_array()
    np.testing.assert_array_equal(expect, got)

    expect = pa.Array.from_pandas(ps)
    got = gs.to_arrow()

    assert pa.Array.equals(expect, got)


@pytest.mark.parametrize(
    'item',
    [
        0,
        2,
        4,
        slice(1, 3),
        [1, 1, 1, 1, 1, 1, 1, 1, 1, 1],
        [0, 1, 2, 3, 4, 4, 3, 2, 1, 0],
        np.array([0, 1, 2, 3, 4]),
        rmm.to_device(np.array([0, 1, 2, 3, 4]))
    ]
)
def test_string_get_item(ps_gs, item):
    ps, gs = ps_gs

    got = gs[item]
    if isinstance(got, Series):
        got = got.to_arrow()

    if isinstance(item, cuda.devicearray.DeviceNDArray):
        item = item.copy_to_host()

    expect = ps.iloc[item]
    if isinstance(expect, pd.Series):
        expect = pa.Array.from_pandas(expect)
        pa.Array.equals(expect, got)
    else:
        assert expect == got


@pytest.mark.parametrize(
    'item',
    [
        [True] * 5,
        [False] * 5,
        np.array([True] * 5),
        np.array([False] * 5),
        rmm.to_device(np.array([True] * 5)),
        rmm.to_device(np.array([False] * 5)),
        list(np.random.randint(0, 2, 5).astype('bool')),
        np.random.randint(0, 2, 5).astype('bool'),
        rmm.to_device(np.random.randint(0, 2, 5).astype('bool'))
    ]
)
def test_string_bool_mask(ps_gs, item):
    ps, gs = ps_gs

    got = gs[item]
    if isinstance(got, Series):
        got = got.to_arrow()

    if isinstance(item, cuda.devicearray.DeviceNDArray):
        item = item.copy_to_host()

    expect = ps[item]
    if isinstance(expect, pd.Series):
        expect = pa.Array.from_pandas(expect)
        pa.Array.equals(expect, got)
    else:
        assert expect == got


@pytest.mark.parametrize('item', [0, slice(1, 3), slice(5)])
def test_string_repr(ps_gs, item):
    ps, gs = ps_gs

    got_out = gs[item]
    expect_out = ps.iloc[item]

    expect = str(expect_out)
    got = str(got_out)

    # if isinstance(expect_out, pd.Series):
    #     expect = expect.replace("object", "str")

    assert expect == got


@pytest.mark.parametrize('dtype', ['int8', 'int16', 'int32', 'int64',
                                   'float32', 'float64'])
def test_string_astype(dtype):
    if dtype.startswith('int'):
        data = ["1", "2", "3", "4", "5"]
    elif dtype.startswith('float'):
        data = ["1.0", "2.0", "3.0", "4.0", "5.0"]
    ps = pd.Series(data)
    gs = Series(data)

    expect = ps.astype(dtype)
    got = gs.astype(dtype)

    assert_eq(expect, got)

@pytest.mark.parametrize('dtype', ['bool', 'int8', 'int16', 'int32', 'int64',
                                   'float32', 'float64'])
def test_string_numeric_astype(dtype):
    if dtype.startswith('bool'):
        pytest.xfail("booleans not yet supported")
        data = [1, 0, 1, 0, 1]
    elif dtype.startswith('int'):
        data = [1, 2, 3, 4, 5]
    elif dtype.startswith('float'):
        pytest.xfail("floats not yet supported")
        data = [1.0, 2.0, 3.0, 4.0, 5.0]

    ps = pd.Series(data, dtype=dtype)
    gs = Series(data, dtype=dtype)

    expect = ps.astype('str')
    got = gs.astype('str')

    assert_eq(expect, got)


def test_string_concat():
    data1 = ['a', 'b', 'c', 'd', 'e']
    data2 = ['f', 'g', 'h', 'i', 'j']

    ps1 = pd.Series(data1)
    ps2 = pd.Series(data2)
    gs1 = Series(data1)
    gs2 = Series(data2)

    expect = pd.concat([ps1, ps2])
    got = concat([gs1, gs2])

    assert_eq(expect, got)


@pytest.mark.parametrize('ascending', [True, False])
def test_string_sort(ps_gs, ascending):
    ps, gs = ps_gs

    expect = ps.sort_values(ascending=ascending)
    got = gs.sort_values(ascending=ascending)

    print(expect)
    print(got)

    assert_eq(expect, got)


def test_string_len(ps_gs):
    ps, gs = ps_gs

    expect = ps.str.len()
    got = gs.str.len()

    # Can't handle nulls in Pandas so use PyArrow instead
    # Pandas will return as a float64 so need to typecast to int32
    expect = pa.array(expect, from_pandas=True).cast(pa.int32())
    got = got.to_arrow()
    assert pa.Array.equals(expect, got)


@pytest.mark.parametrize('others', [
    None,
    ['f', 'g', 'h', 'i', 'j'],
    pd.Series(['f', 'g', 'h', 'i', 'j'])
])
@pytest.mark.parametrize('sep', [None, '', ' ', '|', ',', '|||'])
@pytest.mark.parametrize('na_rep', [None, '', 'null', 'a'])
def test_string_cat(ps_gs, others, sep, na_rep):
    ps, gs = ps_gs

    expect = ps.str.cat(others=others, sep=sep, na_rep=na_rep)
    if isinstance(others, pd.Series):
        others = Series(others)
    got = gs.str.cat(others=others, sep=sep, na_rep=na_rep)

    assert_eq(expect, got)


@pytest.mark.xfail(raises=(NotImplementedError, AttributeError))
@pytest.mark.parametrize('sep', [None, '', ' ', '|', ',', '|||'])
def test_string_join(ps_gs, sep):
    ps, gs = ps_gs

    expect = ps.str.join(sep)
    got = gs.str.join(sep)

    assert_eq(expect, got)


@pytest.mark.parametrize('pat', [
    r'(a)',
    r'(f)',
    r'([a-z])',
    r'([A-Z])'
])
@pytest.mark.parametrize('expand', [True, False])
@pytest.mark.parametrize('flags,flags_raise', [
    (0, 0),
    (1, 1)
])
def test_string_extract(ps_gs, pat, expand, flags, flags_raise):
    ps, gs = ps_gs
    expectation = raise_builder([flags_raise], NotImplementedError)

    with expectation:
        expect = ps.str.extract(pat, flags=flags, expand=expand)
        got = gs.str.extract(pat, flags=flags, expand=expand)

        assert_eq(expect, got)


@pytest.mark.parametrize('pat,regex', [
    ('a', False),
    ('f', False),
    (r'[a-z]', True),
    (r'[A-Z]', True)
])
@pytest.mark.parametrize('case,case_raise', [
    (True, 0),
    (False, 1)
])
@pytest.mark.parametrize('flags,flags_raise', [
    (0, 0),
    (1, 1)
])
@pytest.mark.parametrize('na,na_raise', [
    (np.nan, 0),
    (None, 1),
    ('', 1)
])
def test_string_contains(ps_gs, pat, regex, case, case_raise, flags,
                         flags_raise, na, na_raise):
    ps, gs = ps_gs

    expectation = raise_builder(
        [case_raise, flags_raise, na_raise],
        NotImplementedError
    )

    with expectation:
        expect = ps.str.contains(pat, case=case, flags=flags, na=na,
                                 regex=regex)
        got = gs.str.contains(pat, case=case, flags=flags, na=na, regex=regex)

        expect = pa.array(expect, from_pandas=True).cast(pa.bool_())
        got = got.to_arrow()

        assert pa.Array.equals(expect, got)


# Pandas isn't respect the `n` parameter so ignoring it in test parameters
@pytest.mark.parametrize('pat,regex', [
    ('a', False),
    ('f', False),
    (r'[a-z]', True),
    (r'[A-Z]', True)
])
@pytest.mark.parametrize('repl', ['qwerty', '', ' '])
@pytest.mark.parametrize('case,case_raise', [
    (None, 0),
    (True, 1),
    (False, 1)
])
@pytest.mark.parametrize('flags,flags_raise', [
    (0, 0),
    (1, 1)
])
def test_string_replace(ps_gs, pat, repl, case, case_raise, flags,
                        flags_raise, regex):
    ps, gs = ps_gs

    expectation = raise_builder(
        [case_raise, flags_raise],
        NotImplementedError
    )

    with expectation:
        expect = ps.str.replace(pat, repl, case=case, flags=flags,
                                regex=regex)
        got = gs.str.replace(pat, repl, case=case, flags=flags,
                             regex=regex)

        assert_eq(expect, got)


def test_string_lower(ps_gs):
    ps, gs = ps_gs

    expect = ps.str.lower()
    got = ps.str.lower()

    assert_eq(expect, got)


@pytest.mark.parametrize('data', [
    ['a b', ' c ', '   d', 'e   ', 'f'],
    ['a-b', '-c-', '---d', 'e---', 'f'],
    ['ab', 'c', 'd', 'e', 'f'],
    [None, None, None, None, None]
])
@pytest.mark.parametrize('pat', [
    None,
    ' ',
    '-'
])
@pytest.mark.parametrize('n', [-1, 0, 3, 10])
@pytest.mark.parametrize('expand,expand_raise', [
    (True, 0),
    (False, 1)
])
def test_string_split(data, pat, n, expand, expand_raise):
    ps = pd.Series(data, dtype='str')
    gs = Series(data, dtype='str')

    expectation = raise_builder(
        [expand_raise],
        NotImplementedError
    )

    with expectation:
        expect = ps.str.split(pat=pat, n=n, expand=expand)
        got = gs.str.split(pat=pat, n=n, expand=expand)

        assert_eq(expect, got)


@pytest.mark.parametrize('num_keys', [1, 2, 3])
@pytest.mark.parametrize('how', ['left', 'right', 'inner'])
def test_string_join_key(num_keys, how):
    str_data = ['a', 'b', 'c', 'd', 'e']
    other_data = [1, 2, 3, 4, 5]

    pdf = pd.DataFrame()
    gdf = DataFrame()
    for i in range(num_keys):
        pdf[i] = str_data
        gdf[i] = str_data
    pdf['a'] = other_data
    gdf['a'] = other_data

    pdf2 = pdf.copy()
    gdf2 = gdf.copy()

    expect = pdf.merge(pdf2, on=list(range(num_keys)), how=how)
    got = gdf.merge(gdf2, on=list(range(num_keys)), how=how)

    assert_eq(expect, got)


@pytest.mark.parametrize('num_cols', [1, 2, 3])
@pytest.mark.parametrize('how', ['left', 'right', 'inner'])
def test_string_join_non_key(num_cols, how):
    str_data = ['a', 'b', 'c', 'd', 'e']
    other_data = [1, 2, 3, 4, 5]

    pdf = pd.DataFrame()
    gdf = DataFrame()
    for i in range(num_cols):
        pdf[i] = str_data
        gdf[i] = str_data
    pdf['a'] = other_data
    gdf['a'] = other_data

    pdf2 = pdf.copy()
    gdf2 = gdf.copy()

    expect = pdf.merge(pdf2, on=['a'], how=how)
    got = gdf.merge(gdf2, on=['a'], how=how)

    assert_eq(expect, got)


@pytest.mark.parametrize('num_keys', [1, 2, 3])
def test_string_groupby_key(num_keys):
    str_data = ['a', 'b', 'a', 'b', 'a']
    other_data = [1, 2, 3, 4, 5]

    pdf = pd.DataFrame()
    gdf = DataFrame()
    for i in range(num_keys):
        pdf[i] = str_data
        gdf[i] = str_data
    pdf['a'] = other_data
    gdf['a'] = other_data

    expect = pdf.groupby(list(range(num_keys)), as_index=False).count()
    got = gdf.groupby(list(range(num_keys)), as_index=False).count()

    assert_eq(expect, got)


@pytest.mark.parametrize('num_cols', [1, 2, 3])
def test_string_groupby_non_key(num_cols):
    str_data = ['a', 'b', 'c', 'd', 'e']
    other_data = [1, 2, 1, 2, 1]

    pdf = pd.DataFrame()
    gdf = DataFrame()
    for i in range(num_cols):
        pdf[i] = str_data
        gdf[i] = str_data
    pdf['a'] = other_data
    gdf['a'] = other_data

    expect = pdf.groupby('a', as_index=False).count()
    got = gdf.groupby('a', as_index=False).count()
    assert_eq(expect, got)

    expect = pdf.groupby('a', as_index=False).max()
    got = gdf.groupby('a', as_index=False).max()
    assert_eq(expect, got)

    expect = pdf.groupby('a', as_index=False).min()
    got = gdf.groupby('a', as_index=False).min()
    assert_eq(expect, got)