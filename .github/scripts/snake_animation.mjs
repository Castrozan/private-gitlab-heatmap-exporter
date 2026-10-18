import { once } from "node:events";
import { readFileSync, writeFileSync } from "node:fs";
import { createServer } from "node:http";
import { pathToFileURL } from "node:url";
import { generateSnakeAnimation } from "generate-snake-animation";

const palettes = {
  light: {
    colorDots: { 1: "#9be9a8", 2: "#40c463", 3: "#30a14e", 4: "#216e39" },
    colorEmpty: "#ebedf0",
    colorDotBorder: "#d0d7de",
    colorSnake: "#0969da",
    foreground: "#1f2328",
    muted: "#59636e",
  },
  dark: {
    colorDots: { 1: "#0e4429", 2: "#006d32", 3: "#26a641", 4: "#39d353" },
    colorEmpty: "#161b22",
    colorDotBorder: "#30363d",
    colorSnake: "#79c0ff",
    foreground: "#e6edf3",
    muted: "#9198a1",
  },
};

function contributionLevel(count) {
  if (count === 0) return 0;
  if (count < 3) return 1;
  if (count < 6) return 2;
  if (count < 10) return 3;
  return 4;
}

function frameSnake(svg, contributions, palette) {
  const width = Number(svg.match(/\bwidth="(\d+)"/)[1]);
  const height = Number(svg.match(/\bheight="(\d+)"/)[1]);
  const today = new Date().toISOString().slice(0, 10);
  const start = new Date(`${today}T00:00:00Z`);
  start.setUTCDate(start.getUTCDate() - 365);
  const startDate = start.toISOString().slice(0, 10);
  const total = Object.entries(contributions)
    .filter(([date]) => startDate <= date && date <= today)
    .reduce((sum, [, count]) => sum + count, 0);
  const animation = svg
    .replace(
      /(animation:[^;}]*?)\b[\d.]+ms/g,
      (_, prefix) => `${prefix}24000ms`,
    )
    .replace("<svg ", '<svg x="24" y="30" ');
  return `<svg xmlns="http://www.w3.org/2000/svg" width="${width + 48}" height="${height + 42}" viewBox="0 0 ${width + 48} ${height + 42}" data-animation-duration="24000">
<title>${total.toLocaleString("en-US")} GitLab contributions</title>
<text x="38" y="20" fill="${palette.foreground}" font-family="-apple-system,BlinkMacSystemFont,Segoe UI,sans-serif" font-size="14">${total.toLocaleString("en-US")} GitLab contributions</text>
<text x="${width + 24}" y="20" text-anchor="end" fill="${palette.muted}" font-family="-apple-system,BlinkMacSystemFont,Segoe UI,sans-serif" font-size="12">${startDate} to ${today}</text>
${animation}
</svg>`;
}

export async function createSnakeSvgs(contributions) {
  for (const [date, count] of Object.entries(contributions)) {
    if (
      !/^\d{4}-\d{2}-\d{2}$/.test(date) ||
      !Number.isSafeInteger(count) ||
      count < 0
    ) {
      throw new TypeError(
        "Contributions must contain dates and nonnegative integer counts",
      );
    }
  }
  const server = createServer((request, response) => {
    if (request.url !== "/users/calendar/calendar.json") {
      response.writeHead(404).end();
      return;
    }
    response.writeHead(200, { "content-type": "application/json" });
    response.end(
      JSON.stringify(
        Object.fromEntries(
          Object.entries(contributions).map(([date, count]) => [
            date,
            contributionLevel(count),
          ]),
        ),
      ),
    );
  });
  server.listen(0, "127.0.0.1");
  await once(server, "listening");
  try {
    const themes = Object.keys(palettes);
    const results = await generateSnakeAnimation(
      {
        platform: "gitlab",
        username: "calendar",
        baseUrl: `http://127.0.0.1:${server.address().port}`,
      },
      themes.map((theme) => ({
        format: "svg",
        drawOptions: {
          ...palettes[theme],
          sizeCell: 13,
          sizeDot: 10,
          sizeDotBorderRadius: 2,
        },
        animationOptions: { stepDurationMs: 100, frameByStep: 1 },
      })),
    );
    return Object.fromEntries(
      themes.map((theme, index) => [
        theme,
        frameSnake(results[index], contributions, palettes[theme]),
      ]),
    );
  } finally {
    server.closeAllConnections();
    await new Promise((resolve) => server.close(resolve));
  }
}

if (
  process.argv[1] &&
  import.meta.url === pathToFileURL(process.argv[1]).href
) {
  const contributions = JSON.parse(readFileSync(0, "utf8"));
  const output = process.argv[2];
  const results = await createSnakeSvgs(contributions);
  writeFileSync(output, results.dark);
  writeFileSync(output.replace(/\.svg$/, "-light.svg"), results.light);
}
