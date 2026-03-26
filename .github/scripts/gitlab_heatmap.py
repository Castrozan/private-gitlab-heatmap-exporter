import os
import datetime
import gitlab
import svgwrite
from collections import Counter
import sys
import requests

GITLAB_URL = os.environ.get("GITLAB_URL")
GITLAB_TOKEN = os.environ.get("GITLAB_TOKEN")

GITHUB_DARK_MODE_GREEN_PALETTE = ["#161b22", "#0e4429", "#006d32", "#26a641", "#39d353"]
GITHUB_DARK_MODE_CARD_BACKGROUND_COLOR = "#0d1117"
GITHUB_DARK_MODE_CARD_BORDER_COLOR = "#30363d"
GITHUB_DARK_MODE_HEADER_TEXT_COLOR = "#e6edf3"
GITHUB_DARK_MODE_LABEL_TEXT_COLOR = "#9198a1"
GITHUB_FONT_FAMILY = (
    "-apple-system, BlinkMacSystemFont, 'Segoe UI', 'Noto Sans',"
    " Helvetica, Arial, sans-serif"
)

CELL_SIZE_PIXELS = 10
CELL_GAP_PIXELS = 3
CELL_BORDER_RADIUS = 2
GRID_COLUMN_COUNT = 53
GRID_ROW_COUNT = 7

CARD_PADDING = 12
DAY_OF_WEEK_LABEL_WIDTH = 32
HEADER_TEXT_HEIGHT = 20
MONTH_LABEL_ROW_HEIGHT = 18
LEGEND_ROW_HEIGHT = 20
LEGEND_TOP_MARGIN = 8

MONTH_ABBREVIATIONS = [
    "Jan",
    "Feb",
    "Mar",
    "Apr",
    "May",
    "Jun",
    "Jul",
    "Aug",
    "Sep",
    "Oct",
    "Nov",
    "Dec",
]

DAY_OF_WEEK_LABELS_WITH_ROW_INDEX = [
    (1, "Mon"),
    (3, "Wed"),
    (5, "Fri"),
]


def get_contribution_dates(gl):
    gl.auth()

    today = datetime.datetime.utcnow().date()
    since = today - datetime.timedelta(days=365)

    contribution_dates = []

    events = gl.events.list(
        action="pushed", after=since.isoformat(), get_all=True, sort="asc"
    )

    for event in events:
        contribution_dates.append(event.created_at[:10])

    return Counter(contribution_dates)


def contribution_count_to_color_level(contribution_count):
    if contribution_count == 0:
        return GITHUB_DARK_MODE_GREEN_PALETTE[0]
    if contribution_count < 3:
        return GITHUB_DARK_MODE_GREEN_PALETTE[1]
    if contribution_count < 6:
        return GITHUB_DARK_MODE_GREEN_PALETTE[2]
    if contribution_count < 10:
        return GITHUB_DARK_MODE_GREEN_PALETTE[3]
    return GITHUB_DARK_MODE_GREEN_PALETTE[4]


def calculate_sunday_aligned_start_date(reference_date):
    days_since_sunday = (reference_date.weekday() + 1) % 7
    return reference_date - datetime.timedelta(days=days_since_sunday)


def build_label_font_style(font_size_pixels):
    return f"font-family: {GITHUB_FONT_FAMILY}; font-size: {font_size_pixels}px;"


def calculate_total_svg_dimensions():
    grid_width = (
        GRID_COLUMN_COUNT * (CELL_SIZE_PIXELS + CELL_GAP_PIXELS) - CELL_GAP_PIXELS
    )
    grid_height = (
        GRID_ROW_COUNT * (CELL_SIZE_PIXELS + CELL_GAP_PIXELS) - CELL_GAP_PIXELS
    )

    total_width = CARD_PADDING + DAY_OF_WEEK_LABEL_WIDTH + grid_width + CARD_PADDING
    total_height = (
        CARD_PADDING
        + HEADER_TEXT_HEIGHT
        + MONTH_LABEL_ROW_HEIGHT
        + grid_height
        + LEGEND_TOP_MARGIN
        + LEGEND_ROW_HEIGHT
        + CARD_PADDING
    )
    return total_width, total_height


def add_card_background_to_drawing(drawing, total_width, total_height):
    drawing.add(
        drawing.rect(
            insert=(0, 0),
            size=(total_width, total_height),
            fill=GITHUB_DARK_MODE_CARD_BACKGROUND_COLOR,
            stroke=GITHUB_DARK_MODE_CARD_BORDER_COLOR,
            stroke_width=1,
            rx=6,
            ry=6,
        )
    )


def add_contribution_header_text_to_drawing(
    drawing, total_contributions, grid_area_left_x
):
    header_y = CARD_PADDING + 14
    formatted_contribution_count = f"{total_contributions:,}"
    drawing.add(
        drawing.text(
            f"{formatted_contribution_count} contributions in the last year",
            insert=(grid_area_left_x, header_y),
            fill=GITHUB_DARK_MODE_HEADER_TEXT_COLOR,
            style=build_label_font_style(14),
        )
    )


def add_month_labels_to_drawing(
    drawing, sunday_aligned_start_date, grid_area_left_x, month_label_baseline_y
):
    already_labeled_months = set()
    for week_index in range(GRID_COLUMN_COUNT):
        first_day_of_week = sunday_aligned_start_date + datetime.timedelta(
            weeks=week_index
        )
        if first_day_of_week.day <= 7:
            month_number = first_day_of_week.month
            if month_number not in already_labeled_months:
                already_labeled_months.add(month_number)
                label_x = grid_area_left_x + week_index * (
                    CELL_SIZE_PIXELS + CELL_GAP_PIXELS
                )
                drawing.add(
                    drawing.text(
                        MONTH_ABBREVIATIONS[month_number - 1],
                        insert=(label_x, month_label_baseline_y),
                        fill=GITHUB_DARK_MODE_LABEL_TEXT_COLOR,
                        style=build_label_font_style(12),
                    )
                )


def add_day_of_week_labels_to_drawing(drawing, grid_area_left_x, grid_top_y):
    label_right_edge_x = grid_area_left_x - 6
    for row_index, label_text in DAY_OF_WEEK_LABELS_WITH_ROW_INDEX:
        label_y = grid_top_y + row_index * (CELL_SIZE_PIXELS + CELL_GAP_PIXELS) + 9
        drawing.add(
            drawing.text(
                label_text,
                insert=(label_right_edge_x, label_y),
                fill=GITHUB_DARK_MODE_LABEL_TEXT_COLOR,
                style=build_label_font_style(12),
                text_anchor="end",
            )
        )


def add_contribution_cells_to_drawing(
    drawing,
    contribution_counter,
    sunday_aligned_start_date,
    one_year_ago_date,
    today_date,
    grid_area_left_x,
    grid_top_y,
):
    for week_index in range(GRID_COLUMN_COUNT):
        for day_of_week_index in range(GRID_ROW_COUNT):
            current_date = sunday_aligned_start_date + datetime.timedelta(
                weeks=week_index, days=day_of_week_index
            )
            if current_date < one_year_ago_date or current_date > today_date:
                continue

            date_string = current_date.isoformat()
            contribution_count = contribution_counter.get(date_string, 0)
            cell_fill_color = contribution_count_to_color_level(contribution_count)

            cell_x = grid_area_left_x + week_index * (
                CELL_SIZE_PIXELS + CELL_GAP_PIXELS
            )
            cell_y = grid_top_y + day_of_week_index * (
                CELL_SIZE_PIXELS + CELL_GAP_PIXELS
            )

            drawing.add(
                drawing.rect(
                    insert=(cell_x, cell_y),
                    size=(CELL_SIZE_PIXELS, CELL_SIZE_PIXELS),
                    fill=cell_fill_color,
                    rx=CELL_BORDER_RADIUS,
                    ry=CELL_BORDER_RADIUS,
                )
            )


def add_less_more_legend_to_drawing(drawing, total_width, legend_baseline_y):
    legend_swatch_size = 10
    legend_swatch_gap = 3
    legend_swatch_count = len(GITHUB_DARK_MODE_GREEN_PALETTE)
    more_text_width = 30
    less_text_width = 28

    legend_total_swatches_width = (
        legend_swatch_count * legend_swatch_size
        + (legend_swatch_count - 1) * legend_swatch_gap
    )
    legend_block_width = (
        less_text_width + 4 + legend_total_swatches_width + 4 + more_text_width
    )
    legend_right_edge_x = total_width - CARD_PADDING
    legend_block_start_x = legend_right_edge_x - legend_block_width

    drawing.add(
        drawing.text(
            "Less",
            insert=(legend_block_start_x, legend_baseline_y),
            fill=GITHUB_DARK_MODE_LABEL_TEXT_COLOR,
            style=build_label_font_style(12),
        )
    )

    first_swatch_x = legend_block_start_x + less_text_width + 4
    swatch_top_y = legend_baseline_y - 9
    for swatch_index, swatch_color in enumerate(GITHUB_DARK_MODE_GREEN_PALETTE):
        swatch_x = first_swatch_x + swatch_index * (
            legend_swatch_size + legend_swatch_gap
        )
        drawing.add(
            drawing.rect(
                insert=(swatch_x, swatch_top_y),
                size=(legend_swatch_size, legend_swatch_size),
                fill=swatch_color,
                rx=CELL_BORDER_RADIUS,
                ry=CELL_BORDER_RADIUS,
            )
        )

    more_text_x = first_swatch_x + legend_total_swatches_width + 4
    drawing.add(
        drawing.text(
            "More",
            insert=(more_text_x, legend_baseline_y),
            fill=GITHUB_DARK_MODE_LABEL_TEXT_COLOR,
            style=build_label_font_style(12),
        )
    )


def generate_svg(counter, total_contributions, path="gitlab-graph.svg"):
    total_width, total_height = calculate_total_svg_dimensions()
    drawing = svgwrite.Drawing(path, size=(f"{total_width}px", f"{total_height}px"))

    add_card_background_to_drawing(drawing, total_width, total_height)

    grid_area_left_x = CARD_PADDING + DAY_OF_WEEK_LABEL_WIDTH
    grid_top_y = CARD_PADDING + HEADER_TEXT_HEIGHT + MONTH_LABEL_ROW_HEIGHT

    add_contribution_header_text_to_drawing(
        drawing, total_contributions, grid_area_left_x
    )

    today = datetime.date.today()
    one_year_ago = today - datetime.timedelta(days=365)
    sunday_aligned_start = calculate_sunday_aligned_start_date(one_year_ago)

    month_label_baseline_y = CARD_PADDING + HEADER_TEXT_HEIGHT + 12
    add_month_labels_to_drawing(
        drawing, sunday_aligned_start, grid_area_left_x, month_label_baseline_y
    )

    add_day_of_week_labels_to_drawing(drawing, grid_area_left_x, grid_top_y)

    add_contribution_cells_to_drawing(
        drawing,
        counter,
        sunday_aligned_start,
        one_year_ago,
        today,
        grid_area_left_x,
        grid_top_y,
    )

    grid_height = (
        GRID_ROW_COUNT * (CELL_SIZE_PIXELS + CELL_GAP_PIXELS) - CELL_GAP_PIXELS
    )
    legend_baseline_y = grid_top_y + grid_height + LEGEND_TOP_MARGIN + 14

    add_less_more_legend_to_drawing(drawing, total_width, legend_baseline_y)

    drawing.save()


def validate_gitlab_environment_variables():
    if not GITLAB_TOKEN:
        print(
            "Error: GITLAB_TOKEN environment variable not set.",
            file=sys.stderr,
        )
        print(
            "Please set it to your GitLab Personal Access Token.",
            file=sys.stderr,
        )
        sys.exit(1)

    if not GITLAB_URL:
        print(
            "Error: GITLAB_URL environment variable not set.",
            file=sys.stderr,
        )
        print(
            "Please set it to your GitLab URL.",
            file=sys.stderr,
        )
        sys.exit(1)


def attempt_gitlab_connection(gl):
    try:
        gl.auth()
        print("Successfully connected to GitLab.")
    except (
        requests.exceptions.ConnectionError,
        gitlab.exceptions.GitlabAuthenticationError,
    ) as connection_error:
        print(
            f"GitLab not available at {GITLAB_URL}. Skipping update.",
            file=sys.stderr,
        )
        print(f"Error: {connection_error}", file=sys.stderr)
        sys.exit(0)


def fetch_contributions_and_generate_heatmap(gl):
    print("Fetching GitLab contribution data...")
    try:
        contribution_counts = get_contribution_dates(gl)
        total_contributions = sum(contribution_counts.values())
        print(f"Found {total_contributions} contributions in the last year.")

        if total_contributions == 0:
            print("No contributions found. The generated graph will be empty.")

        print("Generating SVG heatmap...")
        generate_svg(contribution_counts, total_contributions)
        print("Successfully generated gitlab-graph.svg")

    except Exception as unexpected_error:
        print(
            f"An unexpected error occurred: {unexpected_error}",
            file=sys.stderr,
        )
        sys.exit(1)


def main():
    validate_gitlab_environment_variables()

    print(f"Connecting to GitLab at {GITLAB_URL}...")
    gitlab_client = gitlab.Gitlab(GITLAB_URL, private_token=GITLAB_TOKEN, timeout=10)

    attempt_gitlab_connection(gitlab_client)
    fetch_contributions_and_generate_heatmap(gitlab_client)


if __name__ == "__main__":
    main()
