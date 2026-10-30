"""Read saved NumPy arrays across the NumPy 1.x/2.x module rename."""

import pickle


class _NumpyCompatUnpickler(pickle.Unpickler):
    def find_class(self, module, name):
        try:
            return super().find_class(module, name)
        except ModuleNotFoundError as error:
            # NumPy 2 stores array constructors under numpy._core. NumPy 1.23
            # provides those constructors under numpy.core instead.
            if (
                (module == "numpy._core" or module.startswith("numpy._core."))
                and error.name is not None
                and (error.name == "numpy._core" or error.name.startswith("numpy._core."))
            ):
                module = "numpy.core" + module[len("numpy._core"):]
                return super().find_class(module, name)
            raise


def load_numpy_pickle(path):
    """Load an existing trusted pickle without rewriting it."""
    with open(path, "rb") as stream:
        return _NumpyCompatUnpickler(stream).load()
