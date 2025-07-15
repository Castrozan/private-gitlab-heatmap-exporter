# .github/scripts/gitlab_heatmap.py

import os
import datetime
import gitlab
import svgwrite
from collections import Counter
import sys
import requests

# Configuration from environment variables
GITLAB_URL = os.environ.get('GITLAB_URL')
GITLAB_TOKEN = os.environ.get('GITLAB_TOKEN')

def get_contribution_dates(gl):
    """Fetches user contribution events (commits) from the last year."""
    gl.auth()
    
    today = datetime.datetime.utcnow().date()
    since = today - datetime.timedelta(days=365)
    
    contribution_dates = []

    # GitLab API returns events in reverse chronological order.
    # 'pushed' action corresponds to commits.
    events = gl.events.list(action='pushed', after=since.isoformat(), get_all=True, sort='asc')

    for event in events:
        contribution_dates.append(event.created_at[:10])
    
    return Counter(contribution_dates)

def generate_svg(counter, path="gitlab-graph.svg"):
    """Generates a GitHub-style heatmap SVG."""
    box_size = 10
    box_margin = 3
    width = (box_size + box_margin) * 53
    height = (box_size + box_margin) * 7
    
    dwg = svgwrite.Drawing(path, size=(f"{width}px", f"{height}px"))
    
    today = datetime.date.today()
    start_date = today - datetime.timedelta(days=365)
    
    # Start the graph on the Sunday of the week `start_date` is in.
    start_of_graph = start_date - datetime.timedelta(days=(start_date.weekday() + 1) % 7)
    
    # Colors for GitHub's dark mode theme
    colors = ["#161b22", "#0e4429", "#006d32", "#26a641", "#39d353"]

    def get_color(count):
        if count == 0: return colors[0]
        if count < 3: return colors[1]
        if count < 6: return colors[2]
        if count < 10: return colors[3]
        return colors[4]

    for week in range(53):
        for day_of_week in range(7):
            current_date = start_of_graph + datetime.timedelta(weeks=week, days=day_of_week)
            
            if current_date >= start_date and current_date <= today:
                date_str = current_date.isoformat()
                count = counter.get(date_str, 0)
                color = get_color(count)
                
                x = week * (box_size + box_margin)
                y = day_of_week * (box_size + box_margin)
                
                dwg.add(dwg.rect(
                    insert=(x, y),
                    size=(box_size, box_size),
                    fill=color,
                    rx="2", ry="2"
                ))
    dwg.save()

def main():
    """Main function to generate the heatmap."""
    if not GITLAB_TOKEN:
        print("Error: GITLAB_TOKEN environment variable not set.", file=sys.stderr)
        print("Please set it to your GitLab Personal Access Token.", file=sys.stderr)
        sys.exit(1)

    if not GITLAB_URL:
        print("Error: GITLAB_URL environment variable not set.", file=sys.stderr)
        print("Please set it to your GitLab URL.", file=sys.stderr)
        sys.exit(1)

    print(f"Connecting to GitLab at {GITLAB_URL}...")
    gl = gitlab.Gitlab(GITLAB_URL, private_token=GITLAB_TOKEN, timeout=10)

    try:
        # Check if the GitLab instance is reachable before proceeding
        gl.auth()
        print("Successfully connected to GitLab.")
    except (requests.exceptions.ConnectionError, gitlab.exceptions.GitlabAuthenticationError) as e:
        print(f"GitLab not available at {GITLAB_URL}. Skipping update.", file=sys.stderr)
        print(f"Error: {e}", file=sys.stderr)
        # Exit gracefully so the workflow doesn't report a failure
        sys.exit(0)
    
    print("Fetching GitLab contribution data...")
    try:
        contribution_counts = get_contribution_dates(gl)
        total_contributions = sum(contribution_counts.values())
        print(f"Found {total_contributions} contributions in the last year.")
        
        if total_contributions == 0:
            print("No contributions found. The generated graph will be empty.")

        print("Generating SVG heatmap...")
        generate_svg(contribution_counts)
        print("Successfully generated gitlab-graph.svg")

    except Exception as e:
        print(f"An unexpected error occurred: {e}", file=sys.stderr)
        sys.exit(1)

if __name__ == "__main__":
    main() 