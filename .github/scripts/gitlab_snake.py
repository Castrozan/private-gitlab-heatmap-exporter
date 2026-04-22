import datetime
import hashlib
import os
import random
import sys
from collections import Counter

import gitlab
import requests

GITLAB_URL = os.environ.get("GITLAB_URL")
GITLAB_TOKEN = os.environ.get("GITLAB_TOKEN")

GITHUB_DARK_MODE_GREEN_PALETTE = [
    "#161b22",
    "#0e4429",
    "#006d32",
    "#26a641",
    "#39d353",
]
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
DAY_OF_WEEK_LABELS_WITH_ROW_INDEX = [(1, "Mon"), (3, "Wed"), (5, "Fri")]

SNAKE_HEAD_COLOR = "#58a6ff"
SNAKE_HEAD_RADIUS = 5
SNAKE_BODY_SEGMENT_COUNT = 5
SNAKE_BODY_BASE_RADIUS = 4.5
SNAKE_BODY_RADIUS_DECAY_PER_SEGMENT = 0.3
SNAKE_BODY_OPACITY_DECAY_PER_SEGMENT = 0.1

SECONDS_PER_CELL_STEP = 0.30
TRAVERSAL_END_FRACTION = 0.78
SNAKE_HIDE_FRACTION = 0.82
CELL_RESTORE_START_FRACTION = 0.90
CELL_RESTORE_END_FRACTION = 0.95
SNAKE_SHOW_FRACTION = 0.97


def get_contribution_dates(gitlab_client):
    today = datetime.datetime.utcnow().date()
    since = today - datetime.timedelta(days=365)
    events = gitlab_client.events.list(
        action="pushed", after=since.isoformat(), get_all=True, sort="asc"
    )
    return Counter(event.created_at[:10] for event in events)


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


def build_contribution_grid(contribution_counter):
    today = datetime.date.today()
    one_year_ago = today - datetime.timedelta(days=365)
    sunday_aligned_start = calculate_sunday_aligned_start_date(one_year_ago)

    grid = []
    for column_index in range(GRID_COLUMN_COUNT):
        column = []
        for row_index in range(GRID_ROW_COUNT):
            cell_date = sunday_aligned_start + datetime.timedelta(
                weeks=column_index, days=row_index
            )
            if cell_date < one_year_ago or cell_date > today:
                column.append(None)
            else:
                count = contribution_counter.get(cell_date.isoformat(), 0)
                column.append({"color": contribution_count_to_color_level(count)})
        grid.append(column)

    return grid, sunday_aligned_start, one_year_ago, today


def count_unvisited_exits(cell, all_cells, visited):
    column, row = cell
    neighbors = [
        (column + 1, row),
        (column - 1, row),
        (column, row + 1),
        (column, row - 1),
    ]
    return sum(1 for n in neighbors if n in all_cells and n not in visited)


def build_randomized_hamiltonian_path(grid):
    seed = hashlib.md5(datetime.date.today().isoformat().encode()).hexdigest()
    rng = random.Random(seed)

    all_cells = set()
    for column_index in range(GRID_COLUMN_COUNT):
        for row_index in range(GRID_ROW_COUNT):
            if grid[column_index][row_index] is not None:
                all_cells.add((column_index, row_index))

    total_cell_count = len(all_cells)

    first_column_cells = [
        (0, row) for row in range(GRID_ROW_COUNT) if (0, row) in all_cells
    ]
    start = (
        rng.choice(first_column_cells) if first_column_cells else next(iter(all_cells))
    )

    path = [start]
    visited = {start}
    current = start

    while len(visited) < total_cell_count:
        column, row = current
        neighbors = [
            (column + 1, row),
            (column - 1, row),
            (column, row + 1),
            (column, row - 1),
        ]
        unvisited_neighbors = [
            n for n in neighbors if n in all_cells and n not in visited
        ]

        if unvisited_neighbors:
            exit_counts = {
                n: count_unvisited_exits(n, all_cells, visited)
                for n in unvisited_neighbors
            }
            minimum_exit_count = min(exit_counts.values())

            remaining_fraction = (total_cell_count - len(visited)) / total_cell_count
            warnsdorff_relaxation = 1 if remaining_fraction > 0.3 else 0
            exit_threshold = minimum_exit_count + warnsdorff_relaxation

            candidates = [
                n for n in unvisited_neighbors if exit_counts[n] <= exit_threshold
            ]
            next_cell = rng.choice(candidates)
        else:
            remaining = all_cells - visited
            next_cell = min(
                remaining, key=lambda c: abs(c[0] - column) + abs(c[1] - row)
            )

        path.append(next_cell)
        visited.add(next_cell)
        current = next_cell

    return path


def grid_area_left_x():
    return CARD_PADDING + DAY_OF_WEEK_LABEL_WIDTH


def grid_area_top_y():
    return CARD_PADDING + HEADER_TEXT_HEIGHT + MONTH_LABEL_ROW_HEIGHT


def cell_center_x(column_index):
    return (
        grid_area_left_x()
        + column_index * (CELL_SIZE_PIXELS + CELL_GAP_PIXELS)
        + CELL_SIZE_PIXELS / 2
    )


def cell_center_y(row_index):
    return (
        grid_area_top_y()
        + row_index * (CELL_SIZE_PIXELS + CELL_GAP_PIXELS)
        + CELL_SIZE_PIXELS / 2
    )


def cell_top_left_x(column_index):
    return grid_area_left_x() + column_index * (CELL_SIZE_PIXELS + CELL_GAP_PIXELS)


def cell_top_left_y(row_index):
    return grid_area_top_y() + row_index * (CELL_SIZE_PIXELS + CELL_GAP_PIXELS)


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


def generate_cell_eating_keyframes(path, grid, total_animation_seconds):
    lines = []
    path_length = len(path)

    for step_index, (column_index, row_index) in enumerate(path):
        cell = grid[column_index][row_index]
        original_color = cell["color"]

        if original_color == GITHUB_DARK_MODE_GREEN_PALETTE[0]:
            continue

        cell_id = f"s{column_index}_{row_index}"
        arrival_percent = (step_index / max(path_length - 1, 1)) * (
            TRAVERSAL_END_FRACTION * 100
        )
        eaten_start_percent = min(arrival_percent + 0.5, TRAVERSAL_END_FRACTION * 100)
        restore_start_percent = CELL_RESTORE_START_FRACTION * 100
        restore_end_percent = CELL_RESTORE_END_FRACTION * 100

        lines.append(f"@keyframes {cell_id} {{")
        lines.append(f"  0%, {arrival_percent:.2f}% {{ fill: {original_color} }}")
        lines.append(
            f"  {eaten_start_percent:.2f}%, {restore_start_percent:.1f}%"
            f" {{ fill: {GITHUB_DARK_MODE_GREEN_PALETTE[0]} }}"
        )
        lines.append(f"  {restore_end_percent:.1f}%, 100% {{ fill: {original_color} }}")
        lines.append("}")
        lines.append(
            f"#{cell_id} {{"
            f" animation: {cell_id} {total_animation_seconds:.1f}s"
            f" linear infinite;"
            f" }}"
        )

    return "\n".join(lines)


def generate_snake_visibility_keyframes(total_animation_seconds):
    traversal_end = TRAVERSAL_END_FRACTION * 100
    hide_at = SNAKE_HIDE_FRACTION * 100
    show_at = SNAKE_SHOW_FRACTION * 100

    lines = [
        "@keyframes snake-visibility {",
        f"  0%, {traversal_end:.1f}% {{ opacity: 1 }}",
        f"  {hide_at:.1f}%, {show_at:.1f}% {{ opacity: 0 }}",
        "  100% { opacity: 1 }",
        "}",
        ".snake-element {"
        f" animation: snake-visibility {total_animation_seconds:.1f}s"
        " linear infinite;"
        " }",
    ]
    return "\n".join(lines)


def build_snake_element_position_values(path, body_delay_steps):
    path_length = len(path)
    cx_values = []
    cy_values = []
    key_times = []

    for step_index in range(path_length):
        source_index = max(0, step_index - body_delay_steps)
        column_index, row_index = path[source_index]
        cx_values.append(f"{cell_center_x(column_index):.0f}")
        cy_values.append(f"{cell_center_y(row_index):.0f}")

        if step_index == 0:
            key_times.append("0")
        else:
            key_time = (step_index / max(path_length - 1, 1)) * TRAVERSAL_END_FRACTION
            key_times.append(f"{key_time:.4f}")

    cx_values.append(cx_values[-1])
    cy_values.append(cy_values[-1])
    key_times.append("1")

    return (
        ";".join(cx_values),
        ";".join(cy_values),
        ";".join(key_times),
    )


def build_svg_card_background(total_width, total_height):
    return (
        f'<rect width="{total_width}" height="{total_height}"'
        f' fill="{GITHUB_DARK_MODE_CARD_BACKGROUND_COLOR}"'
        f' stroke="{GITHUB_DARK_MODE_CARD_BORDER_COLOR}"'
        f' stroke-width="1" rx="6" ry="6"/>'
    )


def build_svg_header_text(total_contributions):
    header_y = CARD_PADDING + 14
    formatted_count = f"{total_contributions:,}"
    return (
        f'<text x="{grid_area_left_x()}" y="{header_y}"'
        f' fill="{GITHUB_DARK_MODE_HEADER_TEXT_COLOR}"'
        f' style="font-family: {GITHUB_FONT_FAMILY}; font-size: 14px;">'
        f"{formatted_count} contributions in the last year</text>"
    )


def build_svg_month_labels(sunday_aligned_start):
    lines = []
    baseline_y = CARD_PADDING + HEADER_TEXT_HEIGHT + 12
    already_labeled_months = set()

    for week_index in range(GRID_COLUMN_COUNT):
        first_day_of_week = sunday_aligned_start + datetime.timedelta(weeks=week_index)
        if first_day_of_week.day <= 7:
            month_number = first_day_of_week.month
            if month_number not in already_labeled_months:
                already_labeled_months.add(month_number)
                label_x = cell_top_left_x(week_index)
                lines.append(
                    f'<text x="{label_x}" y="{baseline_y}"'
                    f' fill="{GITHUB_DARK_MODE_LABEL_TEXT_COLOR}"'
                    f' style="font-family: {GITHUB_FONT_FAMILY};'
                    f' font-size: 12px;">'
                    f"{MONTH_ABBREVIATIONS[month_number - 1]}</text>"
                )

    return "\n".join(lines)


def build_svg_day_of_week_labels():
    lines = []
    label_right_edge_x = grid_area_left_x() - 6

    for row_index, label_text in DAY_OF_WEEK_LABELS_WITH_ROW_INDEX:
        label_y = cell_top_left_y(row_index) + 9
        lines.append(
            f'<text x="{label_right_edge_x}" y="{label_y}" text-anchor="end"'
            f' fill="{GITHUB_DARK_MODE_LABEL_TEXT_COLOR}"'
            f' style="font-family: {GITHUB_FONT_FAMILY};'
            f' font-size: 12px;">{label_text}</text>'
        )

    return "\n".join(lines)


def build_svg_contribution_grid_cells(grid, colored_cells_in_path):
    lines = []

    for column_index in range(GRID_COLUMN_COUNT):
        for row_index in range(GRID_ROW_COUNT):
            cell = grid[column_index][row_index]
            if cell is None:
                continue

            x = cell_top_left_x(column_index)
            y = cell_top_left_y(row_index)

            id_attribute = ""
            if (column_index, row_index) in colored_cells_in_path:
                id_attribute = f' id="s{column_index}_{row_index}"'

            lines.append(
                f"<rect{id_attribute}"
                f' x="{x}" y="{y}"'
                f' width="{CELL_SIZE_PIXELS}" height="{CELL_SIZE_PIXELS}"'
                f' fill="{cell["color"]}"'
                f' rx="{CELL_BORDER_RADIUS}" ry="{CELL_BORDER_RADIUS}"/>'
            )

    return "\n".join(lines)


def build_svg_legend(total_width):
    lines = []
    grid_height = (
        GRID_ROW_COUNT * (CELL_SIZE_PIXELS + CELL_GAP_PIXELS) - CELL_GAP_PIXELS
    )
    legend_baseline_y = grid_area_top_y() + grid_height + LEGEND_TOP_MARGIN + 14
    swatch_top_y = legend_baseline_y - 9

    swatch_size = 10
    swatch_gap = 3
    swatch_count = len(GITHUB_DARK_MODE_GREEN_PALETTE)
    more_text_width = 30
    less_text_width = 28
    total_swatches_width = swatch_count * swatch_size + (swatch_count - 1) * swatch_gap
    legend_block_width = (
        less_text_width + 4 + total_swatches_width + 4 + more_text_width
    )
    legend_block_start_x = total_width - CARD_PADDING - legend_block_width

    lines.append(
        f'<text x="{legend_block_start_x}" y="{legend_baseline_y}"'
        f' fill="{GITHUB_DARK_MODE_LABEL_TEXT_COLOR}"'
        f' style="font-family: {GITHUB_FONT_FAMILY};'
        f' font-size: 12px;">Less</text>'
    )

    first_swatch_x = legend_block_start_x + less_text_width + 4
    for swatch_index, swatch_color in enumerate(GITHUB_DARK_MODE_GREEN_PALETTE):
        swatch_x = first_swatch_x + swatch_index * (swatch_size + swatch_gap)
        lines.append(
            f'<rect x="{swatch_x}" y="{swatch_top_y}"'
            f' width="{swatch_size}" height="{swatch_size}"'
            f' fill="{swatch_color}"'
            f' rx="{CELL_BORDER_RADIUS}" ry="{CELL_BORDER_RADIUS}"/>'
        )

    more_text_x = first_swatch_x + total_swatches_width + 4
    lines.append(
        f'<text x="{more_text_x}" y="{legend_baseline_y}"'
        f' fill="{GITHUB_DARK_MODE_LABEL_TEXT_COLOR}"'
        f' style="font-family: {GITHUB_FONT_FAMILY};'
        f' font-size: 12px;">More</text>'
    )

    return "\n".join(lines)


def build_svg_snake_elements(path, total_animation_seconds):
    lines = []

    first_column, first_row = path[0]
    initial_cx = f"{cell_center_x(first_column):.0f}"
    initial_cy = f"{cell_center_y(first_row):.0f}"

    head_cx_values, head_cy_values, head_key_times = (
        build_snake_element_position_values(path, 0)
    )
    lines.append(
        f'<circle class="snake-element"'
        f' cx="{initial_cx}" cy="{initial_cy}"'
        f' r="{SNAKE_HEAD_RADIUS}" fill="{SNAKE_HEAD_COLOR}">'
    )
    lines.append(
        f'  <animate attributeName="cx"'
        f' values="{head_cx_values}" keyTimes="{head_key_times}"'
        f' dur="{total_animation_seconds:.1f}s" repeatCount="indefinite"/>'
    )
    lines.append(
        f'  <animate attributeName="cy"'
        f' values="{head_cy_values}" keyTimes="{head_key_times}"'
        f' dur="{total_animation_seconds:.1f}s" repeatCount="indefinite"/>'
    )
    lines.append("</circle>")

    for segment_number in range(1, SNAKE_BODY_SEGMENT_COUNT + 1):
        delay_steps = segment_number
        segment_radius = (
            SNAKE_BODY_BASE_RADIUS
            - (segment_number - 1) * SNAKE_BODY_RADIUS_DECAY_PER_SEGMENT
        )
        segment_opacity = (
            1.0 - (segment_number - 1) * SNAKE_BODY_OPACITY_DECAY_PER_SEGMENT
        )

        segment_cx_values, segment_cy_values, segment_key_times = (
            build_snake_element_position_values(path, delay_steps)
        )

        lines.append(
            f'<circle class="snake-element"'
            f' cx="{initial_cx}" cy="{initial_cy}"'
            f' r="{segment_radius:.1f}" fill="{SNAKE_HEAD_COLOR}"'
            f' opacity="{segment_opacity:.1f}">'
        )
        lines.append(
            f'  <animate attributeName="cx"'
            f' values="{segment_cx_values}"'
            f' keyTimes="{segment_key_times}"'
            f' dur="{total_animation_seconds:.1f}s"'
            f' repeatCount="indefinite"/>'
        )
        lines.append(
            f'  <animate attributeName="cy"'
            f' values="{segment_cy_values}"'
            f' keyTimes="{segment_key_times}"'
            f' dur="{total_animation_seconds:.1f}s"'
            f' repeatCount="indefinite"/>'
        )
        lines.append("</circle>")

    return "\n".join(lines)


def identify_colored_cells_in_path(path, grid):
    colored_cells = set()
    for column_index, row_index in path:
        cell = grid[column_index][row_index]
        if cell["color"] != GITHUB_DARK_MODE_GREEN_PALETTE[0]:
            colored_cells.add((column_index, row_index))
    return colored_cells


def generate_snake_svg(contribution_counter, output_path="gitlab-snk.svg"):
    total_contributions = sum(contribution_counter.values())
    grid, sunday_aligned_start, one_year_ago, today = build_contribution_grid(
        contribution_counter
    )
    path = build_randomized_hamiltonian_path(grid)
    path_length = len(path)

    traversal_seconds = path_length * SECONDS_PER_CELL_STEP
    total_animation_seconds = traversal_seconds / TRAVERSAL_END_FRACTION

    total_width, total_height = calculate_total_svg_dimensions()
    colored_cells = identify_colored_cells_in_path(path, grid)

    svg_parts = [
        f'<svg xmlns="http://www.w3.org/2000/svg"'
        f' width="{total_width}" height="{total_height}">',
        "<style>",
        generate_cell_eating_keyframes(path, grid, total_animation_seconds),
        generate_snake_visibility_keyframes(total_animation_seconds),
        "</style>",
        build_svg_card_background(total_width, total_height),
        build_svg_header_text(total_contributions),
        build_svg_month_labels(sunday_aligned_start),
        build_svg_day_of_week_labels(),
        build_svg_contribution_grid_cells(grid, colored_cells),
        build_svg_legend(total_width),
        build_svg_snake_elements(path, total_animation_seconds),
        "</svg>",
    ]

    svg_content = "\n".join(svg_parts)

    with open(output_path, "w") as output_file:
        output_file.write(svg_content)

    colored_count = len(colored_cells)
    print(
        f"Generated {output_path}"
        f" ({path_length} cells in path,"
        f" {colored_count} colored,"
        f" {total_animation_seconds:.1f}s animation)"
    )


def validate_gitlab_environment_variables():
    if not GITLAB_TOKEN:
        print("Error: GITLAB_TOKEN not set.", file=sys.stderr)
        sys.exit(1)
    if not GITLAB_URL:
        print("Error: GITLAB_URL not set.", file=sys.stderr)
        sys.exit(1)


def attempt_gitlab_connection(gitlab_client):
    try:
        gitlab_client.auth()
        print("Connected to GitLab.")
    except (
        requests.exceptions.ConnectionError,
        gitlab.exceptions.GitlabAuthenticationError,
    ) as connection_error:
        print(
            f"GitLab not available at {GITLAB_URL}. Skipping.",
            file=sys.stderr,
        )
        print(f"Error: {connection_error}", file=sys.stderr)
        sys.exit(0)


def main():
    validate_gitlab_environment_variables()
    print(f"Connecting to GitLab at {GITLAB_URL}...")
    gitlab_client = gitlab.Gitlab(GITLAB_URL, private_token=GITLAB_TOKEN, timeout=10)
    attempt_gitlab_connection(gitlab_client)
    print("Fetching contribution data...")
    contribution_counter = get_contribution_dates(gitlab_client)
    total = sum(contribution_counter.values())
    print(f"Found {total} contributions in the last year.")
    generate_snake_svg(contribution_counter)


if __name__ == "__main__":
    main()
