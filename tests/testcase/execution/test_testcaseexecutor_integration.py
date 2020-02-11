# This file is part of Pynguin.
#
# Pynguin is free software: you can redistribute it and/or modify
# it under the terms of the GNU Lesser General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# Pynguin is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU Lesser General Public License for more details.
#
# You should have received a copy of the GNU Lesser General Public License
# along with Pynguin.  If not, see <https://www.gnu.org/licenses/>.
"""Integration tests for the executor."""

from pynguin.testcase.execution.testcaseexecutor import TestCaseExecutor
import pynguin.testcase.defaulttestcase as dtc
import pynguin.testcase.statements.primitivestatements as prim_stmt
import pynguin.testcase.statements.parametrizedstatements as param_stmt


def test_simple_execution():
    test_case = dtc.DefaultTestCase()
    test_case.add_statement(prim_stmt.IntPrimitiveStatement(test_case, 5))
    executor = TestCaseExecutor()
    assert not executor.execute(test_case).has_test_exceptions()


def test_illegal_call(method_mock):
    test_case = dtc.DefaultTestCase()
    int_stmt = prim_stmt.IntPrimitiveStatement(test_case, 5)
    method_stmt = param_stmt.MethodStatement(
        test_case, method_mock, int_stmt.return_value
    )
    test_case.add_statement(int_stmt)
    test_case.add_statement(method_stmt)
    executor = TestCaseExecutor()
    result = executor.execute(test_case)
    assert result.has_test_exceptions()


def test_create_object(constructor_mock):
    test_case = dtc.DefaultTestCase()
    int_stmt = prim_stmt.IntPrimitiveStatement(test_case, 5)
    constructor_stmt = param_stmt.ConstructorStatement(
        test_case, constructor_mock, [int_stmt.return_value]
    )
    test_case.add_statement(int_stmt)
    test_case.add_statement(constructor_stmt)
    executor = TestCaseExecutor()
    result = executor.execute(test_case)
    assert not result.has_test_exceptions()