import json
import os
from pathlib import Path
import subprocess
import sys

import gitlab
import requests

from gitlab_heatmap import get_contribution_dates


def generate_snake_svg(contribution_counter, output_path="gitlab-snk.svg"):
    renderer = Path(__file__).with_name("snake_animation.mjs")
    subprocess.run(
        ["node", str(renderer), str(output_path)],
        input=json.dumps(contribution_counter),
        text=True,
        check=True,
    )


def main():
    url = os.environ.get("GITLAB_URL")
    token = os.environ.get("GITLAB_TOKEN")
    if not url or not token:
        print("Error: GITLAB_URL and GITLAB_TOKEN must be set.", file=sys.stderr)
        raise SystemExit(1)
    client = gitlab.Gitlab(url, private_token=token, timeout=10)
    try:
        contributions = get_contribution_dates(client)
    except (
        requests.exceptions.ConnectionError,
        gitlab.exceptions.GitlabAuthenticationError,
    ) as connection_error:
        print(f"GitLab not available. Skipping: {connection_error}", file=sys.stderr)
        return
    generate_snake_svg(contributions)


if __name__ == "__main__":
    main()
