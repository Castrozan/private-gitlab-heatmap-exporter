from contextlib import redirect_stderr
import io
import os
import unittest
from unittest.mock import patch

import gitlab
import requests

import gitlab_snake


class SnakeCommandTests(unittest.TestCase):
    def test_missing_credentials_exit_unsuccessfully(self):
        with patch.dict(os.environ, {}, clear=True), redirect_stderr(io.StringIO()):
            with self.assertRaises(SystemExit) as result:
                gitlab_snake.main()
        self.assertEqual(result.exception.code, 1)

    def test_unreachable_or_unauthorized_gitlab_skips_rendering(self):
        failures = [
            requests.ConnectionError("offline"),
            gitlab.GitlabAuthenticationError("unauthorized"),
        ]
        for failure in failures:
            with (
                self.subTest(failure=type(failure).__name__),
                patch.dict(
                    os.environ,
                    {"GITLAB_URL": "https://gitlab.example", "GITLAB_TOKEN": "fixture"},
                ),
                patch("gitlab_snake.get_contribution_dates", side_effect=failure),
                patch("gitlab_snake.generate_snake_svg") as renderer,
                redirect_stderr(io.StringIO()),
            ):
                self.assertIsNone(gitlab_snake.main())
                renderer.assert_not_called()


if __name__ == "__main__":
    unittest.main()
