import os
import sys

import gitlab
import requests

from gitlab_heatmap import get_contribution_dates, generate_svg
from gitlab_snake import generate_snake_svg

GITLAB_URL = os.environ.get("GITLAB_URL")
GITLAB_TOKEN = os.environ.get("GITLAB_TOKEN")


def main():
    if not GITLAB_TOKEN or not GITLAB_URL:
        print("Error: GITLAB_TOKEN and GITLAB_URL must be set.", file=sys.stderr)
        sys.exit(1)

    print(f"Connecting to GitLab at {GITLAB_URL}...")
    gitlab_client = gitlab.Gitlab(GITLAB_URL, private_token=GITLAB_TOKEN, timeout=10)

    try:
        gitlab_client.auth()
        print("Connected.")
    except (
        requests.exceptions.ConnectionError,
        gitlab.exceptions.GitlabAuthenticationError,
    ) as connection_error:
        print(f"GitLab not available: {connection_error}", file=sys.stderr)
        sys.exit(0)

    print("Fetching contributions...")
    contribution_counts = get_contribution_dates(gitlab_client)
    total_contributions = sum(contribution_counts.values())
    print(f"Found {total_contributions} contributions.")

    print("Generating heatmap...")
    generate_svg(contribution_counts, total_contributions)

    print("Generating snake animation...")
    generate_snake_svg(contribution_counts)


if __name__ == "__main__":
    main()
