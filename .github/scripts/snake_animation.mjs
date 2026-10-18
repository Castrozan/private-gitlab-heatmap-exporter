import { once } from "node:events";
import { readFileSync, writeFileSync } from "node:fs";
import { createServer } from "node:http";
import { pathToFileURL } from "node:url";
import { generateSnakeAnimation } from "generate-snake-animation";
import { frameSnake } from "./snake_calendar.mjs";

const palettes = {
  light: {
    colorDots: { 1: "#9be9a8", 2: "#40c463", 3: "#30a14e", 4: "#216e39" },
    colorEmpty: "#ebedf0",
    colorDotBorder: "#d0d7de",
    colorSnake: "#0969da",
    background: "#ffffff",
    foreground: "#1f2328",
    muted: "#59636e",
  },
  dark: {
    colorDots: { 1: "#0e4429", 2: "#006d32", 3: "#26a641", 4: "#39d353" },
    colorEmpty: "#161b22",
    colorDotBorder: "#30363d",
    colorSnake: "#79c0ff",
    background: "#0d1117",
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
          colorDotBorder: "none",
          sizeCell: 13,
          sizeDot: 10,
          sizeDotBorderRadius: 2,
        },
        animationOptions: { stepDurationMs: 300, frameByStep: 1 },
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
