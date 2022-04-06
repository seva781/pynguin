#  This file is part of Pynguin.
#
#  SPDX-FileCopyrightText: 2019–2022 Pynguin Contributors
#
#  SPDX-License-Identifier: LGPL-3.0-or-later
#
import enum
import inspect
from typing import Any, Union
from unittest.mock import MagicMock, patch

import pytest

from pynguin.analyses.types import InferredSignature
from pynguin.utils.type_utils import (
    class_in_module,
    function_in_module,
    given_exception_matches,
    is_assertable,
    is_assignable_to,
    is_bytes,
    is_collection_type,
    is_dict,
    is_enum,
    is_ignorable_type,
    is_list,
    is_none_type,
    is_numeric,
    is_optional_parameter,
    is_primitive_type,
    is_set,
    is_string,
    is_tuple,
    is_type_unknown,
    wrap_var_param_type,
)


@pytest.mark.parametrize(
    "type_, result",
    [
        (int, True),
        (float, True),
        (str, True),
        (bool, True),
        (complex, True),
        (type, False),
        (None, False),
    ],
)
def test_is_primitive_type(type_, result):
    assert is_primitive_type(type_) == result


@pytest.mark.parametrize(
    "type_, result",
    [
        (type(None), True),
        (None, False),
        (str, False),
    ],
)
def test_is_none_type(type_, result):
    assert is_none_type(type_) == result


@pytest.mark.parametrize(
    "type_,result",
    [(None, True), (MagicMock, False)],
)
def test_is_type_unknown(type_, result):
    assert is_type_unknown(type_) == result


@pytest.mark.parametrize(
    "module, result",
    [("wrong_module", False), ("unittest.mock", True)],
)
def test_class_in_module(module, result):
    predicate = class_in_module(module)
    assert predicate(MagicMock) == result


@pytest.mark.parametrize(
    "module, result",
    [("wrong_module", False), ("unittest.mock", True)],
)
def test_function_in_module(module, result):
    predicate = function_in_module(module)
    assert predicate(patch) == result


@pytest.mark.parametrize(
    "from_type,to_type,result",
    [
        (int, int, True),
        (float, Union[int, float], True),
        (float, int, False),
        (float, Union[str, int], False),
        (float, Any, True),
        (int, Any, True),
    ],
)
def test_is_assignable_to(from_type, to_type, result):
    assert is_assignable_to(from_type, to_type) == result


@pytest.mark.parametrize(
    "value, result",
    [(5, True), (5.5, True), ("test", False), (None, False)],
)
def test_is_numeric(value, result):
    assert is_numeric(value) == result


@pytest.mark.parametrize(
    "value, result",
    [(5, False), (5.5, False), ("test", True), (None, False)],
)
def test_is_string(value, result):
    assert is_string(value) == result


@pytest.mark.parametrize(
    "value, result",
    [(b"5", True), ("foo", False), (bytearray("test", "ascii"), True), (None, False)],
)
def test_is_bytes(value, result):
    assert is_bytes(value) == result


@pytest.mark.parametrize(
    "value, result",
    [
        (["foo", "bar"], True),
        ({"foo", "bar"}, False),
        ({"foo": "bar"}, False),
        (("foo", "bar"), False),
    ],
)
def test_is_list(value, result):
    assert is_list(value) == result


@pytest.mark.parametrize(
    "value, result",
    [
        (["foo", "bar"], False),
        ({"foo", "bar"}, True),
        ({"foo": "bar"}, False),
        (("foo", "bar"), False),
    ],
)
def test_is_set(value, result):
    assert is_set(value) == result


@pytest.mark.parametrize(
    "value, result",
    [
        (["foo", "bar"], False),
        ({"foo", "bar"}, False),
        ({"foo": "bar"}, True),
        (("foo", "bar"), False),
    ],
)
def test_is_dict(value, result):
    assert is_dict(value) == result


@pytest.mark.parametrize(
    "value, result",
    [
        (["foo", "bar"], False),
        ({"foo", "bar"}, False),
        ({"foo": "bar"}, False),
        (("foo", "bar"), True),
    ],
)
def test_is_tuple(value, result):
    assert is_tuple(value) == result


def test_is_enum():
    class Foo(enum.Enum):
        pass

    assert is_enum(Foo)


@pytest.mark.parametrize(
    "param_name,result",
    [
        ("normal", False),
        ("args", True),
        ("kwargs", True),
        ("default", True),
    ],
)
def test_should_skip_parameter(param_name, result):
    def inner_func(normal: str, *args, default="foo", **kwargs):
        pass  # pragma: no cover

    inf_sig = MagicMock(InferredSignature, signature=inspect.signature(inner_func))
    assert is_optional_parameter(inf_sig, param_name) == result


@pytest.mark.parametrize(
    "kind,type_,result",
    [
        (inspect.Parameter.VAR_POSITIONAL, None, list[Any]),
        (inspect.Parameter.VAR_POSITIONAL, str, list[str]),
        (inspect.Parameter.VAR_KEYWORD, None, dict[str, Any]),
        (inspect.Parameter.VAR_KEYWORD, str, dict[str, str]),
        (inspect.Parameter.POSITIONAL_OR_KEYWORD, dict, dict),
    ],
)
def test_wrap_var_param_type(kind, type_, result):
    assert wrap_var_param_type(type_, kind) == result


@pytest.mark.parametrize(
    "type_,result",
    [
        (list, True),
        (set, True),
        (dict, True),
        (tuple, True),
        (list[str], True),
        (set[str], True),
        (tuple[str], True),
        (dict[str, str], True),
        (str, False),
    ],
)
def test_is_collection_type(type_, result):
    assert is_collection_type(type_) == result


def test_is_ignorable_type():
    def generator():  # pragma: no cover
        yield from range(10)

    generator_type = type(generator())
    assert is_ignorable_type(generator_type)


def test_is_ignorable_type_async():
    async def async_generator():  # pragma: no cover
        yield "foo"

    generator_type = type(async_generator())
    assert is_ignorable_type(generator_type)


def test_is_ignorable_type_false():
    assert not is_ignorable_type(str)


@pytest.mark.parametrize(
    "exception,ex_match,result",
    [
        (ValueError, ValueError, True),
        (ValueError(), ValueError, True),
        (ValueError(), Exception, True),
        (ValueError(), NameError, False),
        (None, None, False),
    ],
)
def test_given_exception_matches(exception, ex_match, result):
    assert given_exception_matches(exception, ex_match) == result


@pytest.mark.parametrize(
    "value,result",
    [
        (1, True),
        (MagicMock(), False),
        (enum.Enum("Dummy", "a").a, True),
        ({1, 2}, True),
        ({1, MagicMock()}, False),
        ([1, 2], True),
        ([1, MagicMock()], False),
        ((1, 2), True),
        ((1, MagicMock()), False),
        ({1: 2}, True),
        ({1: MagicMock()}, False),
        ([[[[[[[[]]]]]]]], False),
        ((), True),
        (set(), True),
        ({}, True),
        ([], True),
        ([[]], True),
        ("foobar", True),
        (["a", "b", ["a", "b", MagicMock()]], False),
        (1.5, False),
        ([1, 1.5], False),
        (None, True),
        ([None], True),
    ],
)
def test_is_assertable(value, result):
    assert is_assertable(value) == result
