import json
import os
from pathlib import Path
import subprocess

import gitlab

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
    client = gitlab.Gitlab(
        os.environ["GITLAB_URL"], private_token=os.environ["GITLAB_TOKEN"], timeout=10
    )
    contributions = get_contribution_dates(client)
    generate_snake_svg(contributions)


if __name__ == "__main__":
    main()
