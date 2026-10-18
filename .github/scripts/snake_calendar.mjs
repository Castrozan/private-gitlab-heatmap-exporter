export function frameSnake(svg, contributions, palette) {
  const width = Number(svg.match(/\bwidth="(\d+)"/)[1]);
  const height = 212;
  const today = new Date();
  today.setHours(0, 0, 0, 0);
  const firstDate = new Date(today);
  firstDate.setDate(firstDate.getDate() - 365);
  const firstWeek = new Date(firstDate);
  firstWeek.setDate(firstWeek.getDate() - firstWeek.getDay());
  const start = firstDate.toLocaleDateString("en-CA");
  const end = today.toLocaleDateString("en-CA");
  const total = Object.entries(contributions)
    .filter(([date]) => start <= date && date <= end)
    .reduce((sum, [, count]) => sum + count, 0);
  const labels = [];
  const visitedMonths = new Set();
  for (let column = 0; column * 13 < width - 26; column++) {
    const date = new Date(firstWeek);
    date.setDate(date.getDate() + column * 7);
    const month = date.getMonth();
    if (column !== 0 && (date.getDate() > 7 || visitedMonths.has(month)))
      continue;
    visitedMonths.add(month);
    labels.push(
      `<text x="${44 + column * 13}" y="42">${date.toLocaleDateString("en-US", { month: "short" })}</text>`,
    );
  }
  for (const [row, day] of [
    [1, "Mon"],
    [3, "Wed"],
    [5, "Fri"],
  ]) {
    labels.push(
      `<text x="38" y="${83 + row * 13}" text-anchor="end">${day}</text>`,
    );
  }
  const colors = [palette.colorEmpty, ...Object.values(palette.colorDots)];
  const legendStart = width - 92;
  labels.push(`<text x="${legendStart - 31}" y="200">Less</text>`);
  colors.forEach((color, index) =>
    labels.push(
      `<rect x="${legendStart + index * 13}" y="191" width="10" height="10" rx="2" fill="${color}"/>`,
    ),
  );
  labels.push(`<text x="${legendStart + 69}" y="200">More</text>`);
  const duration = Number(svg.match(/animation:[^;}]*?\b([\d.]+)ms/)[1]);
  const animation = svg
    .replace(/<rect class="u [^>]*\/>/g, "")
    .replace(/<svg /, '<svg x="30" y="48" ');
  return `<svg xmlns="http://www.w3.org/2000/svg" width="${width + 48}" height="${height}" viewBox="0 0 ${width + 48} ${height}" data-animation-duration="${duration}">
<title>${total.toLocaleString("en-US")} contributions in the last year</title>
<rect x="0.5" y="0.5" width="${width + 47}" height="${height - 1}" rx="6" fill="${palette.background}" stroke="${palette.colorDotBorder}"/>
<text x="44" y="26" fill="${palette.foreground}" font-family="-apple-system,BlinkMacSystemFont,Segoe UI,sans-serif" font-size="14">${total.toLocaleString("en-US")} contributions in the last year</text>
<g fill="${palette.muted}" font-family="-apple-system,BlinkMacSystemFont,Segoe UI,sans-serif" font-size="12">${labels.join("")}</g>
${animation}
</svg>`;
}
