# [20260103_TEST] Sample classes for update_symbol testing


class SimpleClass:
    """Simple class for testing."""

    def __init__(self, name):
        self.name = name

    def get_name(self):
        """Get the name."""
        return self.name

    def set_name(self, name):
        """Set the name."""
        self.name = name


class ClassWithStaticMethod:
    """Class with static method."""

    @staticmethod
    def static_operation(x, y):
        """Perform static operation."""
        return x + y

    @classmethod
    def create_from_string(cls, data):
        """Create instance from string."""
        return cls(data)


class ClassWithProperties:
    """Class with property decorators."""

    def __init__(self, value):
        self._value = value

    @property
    def value(self):
        """Get value property."""
        return self._value

    @value.setter
    def value(self, val):
        """Set value property."""
        if val < 0:
            raise ValueError("Value cannot be negative")
        self._value = val


class ParentClass:
    """Parent class for inheritance testing."""

    def parent_method(self):
        """Parent class method."""
        return "parent"

    def shared_method(self):
        """Method shared with child."""
        return "parent_shared"


class ChildClass(ParentClass):
    """Child class inheriting from ParentClass."""

    def child_method(self):
        """Child class method."""
        return "child"

    def shared_method(self):
        """Override parent method."""
        return "child_shared"


class ClassWithAsync:
    """Class with async methods."""

    async def async_operation(self, data):
        """Async operation in class."""
        return {"result": data, "async": True}

    def sync_operation(self, data):
        """Sync operation in class."""
        return {"result": data, "async": False}


class ClassWithSpecialMethods:
    """Class with special methods."""

    def __init__(self, value):
        self.value = value

    def __str__(self):
        """String representation."""
        return f"ClassWithSpecialMethods({self.value})"

    def __repr__(self):
        """Developer representation."""
        return f"ClassWithSpecialMethods(value={self.value!r})"

    def __eq__(self, other):
        """Equality comparison."""
        return self.value == other.value


class DecoratedClass:
    """Class with decorator."""

    @property
    @staticmethod
    def computed_value():
        """Computed property."""
        return 42
