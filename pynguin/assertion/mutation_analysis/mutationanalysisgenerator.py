#  This file is part of Pynguin.
#
#  SPDX-FileCopyrightText: 2019–2021 Pynguin Contributors
#
#  SPDX-License-Identifier: LGPL-3.0-or-later
#
"""Provides a assertion generation by utilizing the mutation-analysis approach."""
import logging
from types import ModuleType
from typing import Any, Dict, List, Optional, Set, Tuple, cast

import pynguin.assertion.complexassertion as ca
import pynguin.assertion.fieldassertion as fa
import pynguin.assertion.mutation_analysis.collectorstorage as cs
import pynguin.assertion.mutation_analysis.mutationadapter as ma
import pynguin.assertion.mutation_analysis.mutationanalysisexecution as ce
import pynguin.assertion.mutation_analysis.statecollectingobserver as sco
import pynguin.ga.chromosomevisitor as cv
import pynguin.ga.testsuitechromosome as tsc
import pynguin.testcase.defaulttestcase as dtc
import pynguin.testcase.execution.testcaseexecutor as ex
import pynguin.testcase.statements.parametrizedstatements as ps
import pynguin.testcase.statements.statement as st
import pynguin.testcase.testcase as tc
import pynguin.testcase.variable.variablereference as vr
import pynguin.utils.collection_utils as cu


class MutationAnalysisGenerator(cv.ChromosomeVisitor):
    """Assertion generator using the mutation analysis approach."""

    _logger = logging.getLogger(__name__)

    def __init__(self, executor: ex.TestCaseExecutor):
        """
        Create new assertion generator.

        Args:
            executor: the executor that will be used to execute the test cases.
        """
        self._storage = cs.CollectorStorage()
        # TODO(fk) permanently disable tracer
        self._executor = executor
        # TODO(fk) what to do with existing observers?
        self._executor.add_observer(sco.StateCollectingObserver(self._storage))
        self._global_assertions: Set[fa.FieldAssertion] = set()
        self._field_assertions: Set[fa.FieldAssertion] = set()
        self._last_obj_assertion: Optional[ca.ComplexAssertion] = None

    def visit_test_suite_chromosome(self, chromosome: tsc.TestSuiteChromosome) -> None:
        test_cases = [chrom.test_case for chrom in chromosome.test_case_chromosomes]

        mutated_modules = [x for x, _ in self._mutate_module()]

        execution = ce.MutationAnalysisExecution(
            self._executor, mutated_modules, self._storage
        )
        execution.execute(test_cases)

        self._generate_assertions(test_cases)

    def visit_test_case_chromosome(self, chromosome: tsc.TestSuiteChromosome) -> None:
        pass  # nothing to do here

    @staticmethod
    def _mutate_module() -> List[Tuple[ModuleType, Any]]:
        adapter = ma.MutationAdapter()
        return adapter.mutate_module()

    # pylint: disable=too-many-locals
    def _generate_assertions(self, test_cases: List[tc.TestCase]) -> None:
        # Get the reference data from the execution on the not mutate module
        reference = self._storage.get_items(0)

        # Iterate over all dataframes for the reference execution
        for ref_dataframe in reference:

            # Get the test case id and position of the frame
            tc_id = cast(int, ref_dataframe[cs.KEY_TEST_ID])
            pos = cast(int, ref_dataframe[cs.KEY_POSITION])

            # Get the corresponding test case and statement
            test_case = self._get_testcase_by_id(test_cases, tc_id)
            assert test_case is not None, "Expected a testcase to be found."
            statement = self._get_statement_by_pos(test_case, pos)
            assert statement is not None, "Expected a statement to be found."

            # Get the mutated frames corresponding to the id and position
            mutated_dataframes = self._storage.get_dataframe_of_mutations(tc_id, pos)

            # Get the reference state of the return value of the current statement
            ref_rv = ref_dataframe[cs.KEY_RETURN_VALUE]

            # Get the reference states of the global fields at this dataframe
            ref_globals = ref_dataframe[cs.KEY_GLOBALS]

            # Get all stored object fragments
            remainders = cu.dict_without_keys(
                ref_dataframe,
                {cs.KEY_TEST_ID, cs.KEY_POSITION, cs.KEY_RETURN_VALUE, cs.KEY_GLOBALS},
            )

            self._last_obj_assertion = None

            # Iterate over all mutated dataframes and compare
            for dataframe in mutated_dataframes:

                # Compare the Return Value
                self._compare_return_value(
                    dataframe[cs.KEY_RETURN_VALUE], ref_rv, statement
                )

                # Compare the global fields
                self._compare_globals(dataframe[cs.KEY_GLOBALS], ref_globals, statement)

                # Compare the remaining objects
                for key, ref_fragment in remainders.items():
                    fragment = dataframe.get(key)
                    assert (
                        fragment is not None
                    ), "Expected any data from the datafragment"
                    for frag_key, ref_frag_val in ref_fragment.items():
                        frag_val = fragment.get(frag_key)
                        if frag_key == cs.KEY_CLASS_FIELD:
                            # Class fields
                            self._compare_class_fields(
                                frag_val, pos, ref_frag_val, statement, test_case
                            )
                        elif frag_key == cs.KEY_OBJECT_ATTRIBUTE:
                            # Object attributes
                            self._compare_object_attributes(
                                frag_val, pos, ref_frag_val, statement, test_case
                            )

    # pylint: disable=too-many-arguments
    def _compare_class_fields(
        self,
        frag_val: Dict[str, Any],
        pos: int,
        ref_frag_val: Dict[str, Any],
        statement: st.Statement,
        test_case: tc.TestCase,
    ) -> None:
        for field, ref_value in ref_frag_val.items():
            value = frag_val.get(field)
            if ref_value != value:
                obj_vr = self._get_current_object_ref(test_case, pos)
                obj_class = self._get_current_object_class(obj_vr)
                obj_module = self._get_current_object_module(obj_vr)
                assertion = fa.FieldAssertion(
                    None, ref_value, field, obj_module, [obj_class]
                )
                if assertion not in self._field_assertions:
                    self._field_assertions.add(assertion)
                    statement.add_assertion(assertion)

    # pylint: disable=too-many-arguments
    def _compare_object_attributes(
        self,
        frag_val: Dict[str, Any],
        pos: int,
        ref_frag_val: Dict[str, Any],
        statement: st.Statement,
        test_case: tc.TestCase,
    ) -> None:
        for field, ref_value in ref_frag_val.items():
            value = frag_val.get(field)
            if ref_value != value:
                obj_vr = self._get_current_object_ref(test_case, pos)
                assertion = fa.FieldAssertion(obj_vr, ref_value, field)
                if assertion not in self._field_assertions:
                    self._field_assertions.add(assertion)
                    statement.add_assertion(assertion)

    def _compare_globals(
        self,
        globals_frame: Dict[str, Dict[str, Any]],
        globals_frame_ref: Dict[str, Dict[str, Any]],
        statement: st.Statement,
    ) -> None:
        for module_alias in globals_frame_ref.keys():
            globals_frame_ref_modules = globals_frame_ref.get(module_alias)
            assert (
                globals_frame_ref_modules is not None
            ), "Expected a module for the module alias"
            for global_field, ref_value in globals_frame_ref_modules.items():
                value = globals_frame[module_alias][global_field]
                if ref_value != value:
                    assertion = fa.FieldAssertion(
                        None, ref_value, global_field, module_alias
                    )
                    if assertion not in self._global_assertions:
                        self._global_assertions.add(assertion)
                        statement.add_assertion(assertion)

    def _compare_return_value(
        self, retval, ref_rv: Any, statement: st.Statement
    ) -> None:
        if retval != ref_rv:
            statement_vr = statement.ret_val
            assertion = ca.ComplexAssertion(statement_vr, ref_rv)
            if (
                self._last_obj_assertion
                and self._last_obj_assertion.value is assertion.value
            ):
                return
            self._last_obj_assertion = assertion
            statement.add_assertion(assertion)

    @staticmethod
    def _get_testcase_by_id(
        test_cases: List[tc.TestCase], test_case_id: int
    ) -> Optional[tc.TestCase]:
        for test_case in test_cases:
            if (
                isinstance(test_case, dtc.DefaultTestCase)
                and test_case.id == test_case_id
            ):
                return test_case
        return None

    @staticmethod
    def _get_statement_by_pos(
        test_case: tc.TestCase, position: int
    ) -> Optional[st.Statement]:
        if 0 <= position < len(test_case.statements):
            return test_case.statements[position]
        return None

    @staticmethod
    def _get_current_object_ref(
        test_case: tc.TestCase, position: int
    ) -> Optional[vr.VariableReference]:
        while position >= 0:
            if isinstance(test_case.statements[position], ps.ConstructorStatement):
                return test_case.statements[position].ret_val
            position -= 1
        return None

    @staticmethod
    def _get_current_object_class(
        var_ref: Optional[vr.VariableReference],
    ) -> Optional[str]:
        if var_ref and var_ref.variable_type:
            return var_ref.variable_type.__name__
        return None

    @staticmethod
    def _get_current_object_module(
        var_ref: Optional[vr.VariableReference],
    ) -> Optional[str]:
        if var_ref and var_ref.variable_type:
            return var_ref.variable_type.__module__
        return None
