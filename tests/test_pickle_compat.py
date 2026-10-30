import pickle
from pathlib import Path
import tempfile
import unittest
from types import SimpleNamespace
from unittest.mock import Mock

import numpy as np

from pymovie.pickle_compat import load_numpy_pickle


class NumpyPickleCompatibilityTests(unittest.TestCase):
    def load_payload(self, payload):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "digits.p"
            path.write_bytes(payload)
            result = load_numpy_pickle(path)
            self.assertEqual(path.read_bytes(), payload)
            return result

    def test_existing_arrays_and_missing_digits(self):
        digits = [np.arange(12, dtype=np.uint8).reshape(3, 4), None]
        for protocol in (0, 4, 5):
            with self.subTest(protocol=protocol):
                result = self.load_payload(pickle.dumps(digits, protocol=protocol))
                np.testing.assert_array_equal(result[0], digits[0])
                self.assertEqual(result[0].dtype, digits[0].dtype)
                self.assertIsNone(result[1])

    def test_numpy_2_module_path(self):
        digits = [np.arange(12, dtype=np.uint8).reshape(3, 4), None]
        # Protocol 0 uses newline-delimited names, so the rename does not
        # require adjusting binary string lengths or frame sizes.
        payload = pickle.dumps(digits, protocol=0).replace(
            b"cnumpy.core.multiarray\n", b"cnumpy._core.multiarray\n"
        )
        self.assertIn(b"cnumpy._core.multiarray\n", payload)
        result = self.load_payload(payload)
        np.testing.assert_array_equal(result[0], digits[0])
        self.assertEqual(result[0].dtype, digits[0].dtype)
        self.assertIsNone(result[1])

    def test_unrelated_missing_module_is_not_hidden(self):
        with self.assertRaises(ModuleNotFoundError):
            self.load_payload(b"cmissing_pymovie_test_module\nthing\n.")

    def test_corrupt_pickle_is_not_hidden(self):
        with self.assertRaises(pickle.UnpicklingError):
            self.load_payload(b"not a pickle")

    def check_application_load(self, observation_copy):
        from pymovie.main import PyMovie

        digits = [np.arange(12, dtype=np.uint8).reshape(3, 4)] + [None] * 9
        payload = pickle.dumps(digits, protocol=0).replace(
            b"cnumpy.core.multiarray\n", b"cnumpy._core.multiarray\n"
        )
        with tempfile.TemporaryDirectory() as directory:
            home = Path(directory) / "home"
            observation = Path(directory) / "observation"
            home.mkdir()
            observation.mkdir()
            folder = observation if observation_copy else home
            path = folder / "custom-digits.p"
            path.write_bytes(payload)
            if observation_copy:
                # A stale global profile must not override the video profile.
                (home / path.name).write_bytes(pickle.dumps([None] * 10))
            state = SimpleNamespace(
                modelDigitsFilename=path.name, ocrDigitsDir=str(observation),
                homeDir=str(home), showMissingModelDigits=Mock(),
            )
            PyMovie.loadModelDigits(state)
            np.testing.assert_array_equal(state.modelDigits[0], digits[0])
            self.assertEqual(len(state.modelDigits), 10)
            state.showMissingModelDigits.assert_called_once()
            self.assertEqual(path.read_bytes(), payload)

    def test_application_prefers_observation_profile(self):
        self.check_application_load(observation_copy=True)

    def test_application_falls_back_to_home_profile(self):
        self.check_application_load(observation_copy=False)


if __name__ == "__main__":
    unittest.main()
