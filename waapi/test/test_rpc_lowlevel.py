import unittest

from waapi import WaapiClient


class TestRpcLowLevel(unittest.TestCase):
    def setUp(self):
        self.client = WaapiClient()

    def tearDown(self):
        self.client.disconnect()

    def test_invalid(self):
        result = self.client.call("ak.wwise.idontexist")
        self.assertIs(result, None)  # Noexcept

    def test_no_argument(self):
        result = self.client.call("ak.wwise.core.getInfo")
        self.assertIsNotNone(result)
        self.assertTrue(isinstance(result, dict))
        self.assertIn("apiVersion", result)
        self.assertIn("version", result)

        version = result.get("version")
        self.assertIsNotNone(version)
        self.assertTrue(isinstance(result, dict))
        self.assertIn("build", version)
        self.assertEqual(type(version.get("build")), int)

    def test_with_argument(self):
        myargs = {
            "from": {
                "ofType": [
                    "Project"
                ]
            }
        }
        result = self.client.call("ak.wwise.core.object.get", **myargs)
        self.assertIsNotNone(result)
        self.assertTrue(isinstance(result, dict))
        self.assertIn("return", result)
        result_return = result.get("return")

        self.assertIsNotNone(result_return)
        self.assertTrue(isinstance(result_return, list))
        self.assertEqual(len(result_return), 1)
        self.assertTrue(isinstance(result_return[0], dict))
        result_return = result_return[0]

        # Default is (id, name)
        self.assertIn("id", result_return)
        self.assertIsInstance(result_return.get("id"), str)  # GUID
        self.assertIsInstance(result_return.get("name"), str)

    def test_with_argument_and_return_options(self):
        myargs = {
            "from": {
                "ofType": [
                    "Project"
                ]
            },
            "options": {
                "return": [
                    "name",
                    "filePath",
                    "workunit:isDirty"
                ]
            }
        }
        result = self.client.call("ak.wwise.core.object.get", **myargs)
        self.assertIsNotNone(result)
        self.assertTrue(isinstance(result, dict))
        self.assertIn("return", result)
        result_return = result.get("return")
        result_return = result_return[0]

        self.assertIn("filePath", result_return)
        self.assertIsInstance(result_return.get("filePath"), str)
        self.assertIn("name", result_return)
        self.assertIsInstance(result_return.get("name"), str)
        self.assertIn("workunit:isDirty", result_return)
        self.assertIsInstance(result_return.get("workunit:isDirty"), bool)
