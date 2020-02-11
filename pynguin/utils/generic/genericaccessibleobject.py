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
"""
Provide wrappers around constructors, methods, function and fields.
Think of these like the reflection classes in Java.
"""
import abc
from typing import Optional, Type, Callable

from pynguin.typeinference.strategy import InferredSignature


class GenericAccessibleObject(metaclass=abc.ABCMeta):
    """Abstract base class for something that can be accessed."""

    def __init__(self, owner: Optional[Type]):
        self._owner = owner

    @abc.abstractmethod
    def generated_type(self) -> Optional[Type]:
        """Provides the type that is generated by this accessible object."""

    @property
    def owner(self) -> Optional[Type]:
        """The type which owns this accessible object."""
        return self._owner


class GenericCallableAccessibleObject(
    GenericAccessibleObject, metaclass=abc.ABCMeta
):  # pylint: disable=W0223
    """Abstract base class for something that can be called."""

    def __init__(
        self,
        owner: Optional[Type],
        callable_: Callable,
        inferred_signature: InferredSignature,
    ) -> None:
        super().__init__(owner)
        self._callable = callable_
        self._inferred_signature = inferred_signature

    def generated_type(self) -> Optional[Type]:
        return self._inferred_signature.return_type

    @property
    def inferred_signature(self) -> InferredSignature:
        """Provides access to the inferred type signature information."""
        return self._inferred_signature

    @property
    def callable(self) -> Callable:
        """Provides the callable."""
        return self._callable


class GenericConstructor(GenericCallableAccessibleObject):
    """A constructor."""

    def __init__(self, owner: Type, inferred_signature: InferredSignature) -> None:
        super().__init__(owner, owner.__init__, inferred_signature)
        assert owner

    def generated_type(self) -> Optional[Type]:
        return self.owner

    def __eq__(self, other):
        if self is other:
            return True
        if not isinstance(other, GenericConstructor):
            return False
        return self._owner == other._owner

    def __hash__(self):
        return hash(self._owner)

    def __repr__(self):
        return f"{self.__class__.__name__}({self.owner}, {self.inferred_signature})"


class GenericMethod(GenericCallableAccessibleObject):
    """A method."""

    def __init__(
        self, owner: Type, method: Callable, inferred_signature: InferredSignature
    ) -> None:
        super().__init__(owner, method, inferred_signature)
        assert owner

    def __eq__(self, other):
        if self is other:
            return True
        if not isinstance(other, GenericMethod):
            return False
        return self._callable == other._callable

    def __hash__(self):
        return hash(self._callable)

    def __repr__(self):
        return (
            f"{self.__class__.__name__}({self.owner},"
            f" {self._callable.__name__}, {self.inferred_signature})"
        )


class GenericFunction(GenericCallableAccessibleObject):
    """A function, which does not belong to any class."""

    def __init__(
        self, function: Callable, inferred_signature: InferredSignature
    ) -> None:
        super().__init__(None, function, inferred_signature)

    def __eq__(self, other):
        if self is other:
            return True
        if not isinstance(other, GenericFunction):
            return False
        return self._callable == other._callable

    def __hash__(self):
        return hash(self._callable)

    def __repr__(self):
        return f"{self.__class__.__name__}({self._callable.__name__}, {self.inferred_signature})"


class GenericField(GenericAccessibleObject):
    """A field."""

    def __init__(self, owner: Type, field: str, field_type: Optional[Type]) -> None:
        super().__init__(owner)
        self._field = field
        self._field_type = field_type

    def generated_type(self) -> Optional[Type]:
        return self._field_type

    @property
    def field(self) -> str:
        """Provides the name of the field."""
        return self._field

    def __eq__(self, other):
        if self is other:
            return True
        if not isinstance(other, GenericField):
            return False
        return self._owner == other._owner and self._field == self._field

    def __hash__(self):
        return 31 + 17 * hash(self._owner) + 17 * hash(self._field)

    def __repr__(self):
        return f"{self.__class__.__name__}({self.owner}, {self._field}, {self._field_type})"