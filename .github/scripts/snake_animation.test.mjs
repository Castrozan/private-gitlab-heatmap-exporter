import assert from "node:assert/strict";
import test from "node:test";
import { createSnakeSvgs } from "./snake_animation.mjs";

test("exports both palettes with a shared loop and one contribution total", async () => {
  const today = new Date().toISOString().slice(0, 10);
  const results = await createSnakeSvgs({ [today]: 12 });
  assert.match(results.light, /12 contributions in the last year/);
  assert.match(results.dark, /12 contributions in the last year/);
  assert.match(results.light, /--cs:#0969da/);
  assert.match(results.dark, /--cs:#79c0ff/);
  for (const svg of Object.values(results)) {
    assert.match(svg, /Generated with https:\/\/github.com\/Platane\/snk/);
    const expectedDuration = Number(
      svg.match(/data-animation-duration="(\d+)"/)[1],
    );
    assert.ok(expectedDuration >= 2400);
    const durations = [...svg.matchAll(/animation:[^;}]*?\b([\d.]+)ms/g)].map(
      (match) => Number(match[1]),
    );
    assert.ok(durations.length >= 2);
    assert.ok(durations.every((duration) => duration === expectedDuration));
    for (const label of ["Mon", "Wed", "Fri", "Less", "More"]) {
      assert.ok(svg.includes(`>${label}</text>`));
    }
    assert.doesNotMatch(svg, /\d{4}-\d{2}-\d{2} to/);
    assert.doesNotMatch(svg, /<rect class="u /);
    assert.match(svg, /<rect[^>]+rx="6"/);
  }
});

test("an empty contribution calendar still renders a valid loop", async () => {
  const results = await createSnakeSvgs({});
  assert.match(results.light, /0 contributions in the last year/);
  assert.match(results.dark, /@keyframes/);
});

test("rejects invalid counts instead of publishing a misleading calendar", async () => {
  await assert.rejects(createSnakeSvgs({ "2026-10-18": -1 }), TypeError);
});

function snakeTracks(svg) {
  return [...svg.matchAll(/@keyframes s\d+\{((?:[^{}]+\{[^{}]+\})+)\}/g)].map(
    ([, body]) =>
      [
        ...body.matchAll(
          /([\d.% ,]+)\{transform:translate\(([-\d.]+)px,([-\d.]+)px\)\}/g,
        ),
      ]
        .flatMap(([, offsets, x, y]) =>
          offsets.split(",").map((offset) => ({
            time: Number.parseFloat(offset),
            x: Number(x),
            y: Number(y),
          })),
        )
        .sort((left, right) => left.time - right.time),
  );
}

function positionAt(track, time) {
  const following = track.findIndex((point) => point.time > time);
  if (following < 0) return track.at(-1);
  const start = track[following - 1];
  const end = track[following];
  const progress = (time - start.time) / (end.time - start.time);
  return {
    x: start.x + progress * (end.x - start.x),
    y: start.y + progress * (end.y - start.y),
  };
}

test("dense routes turn on grid cells, avoid their own body and return to the starting pose", async () => {
  const calendar = {};
  const today = new Date();
  for (let days = 0; days < 365; days += 2) {
    const date = new Date(today);
    date.setUTCDate(date.getUTCDate() - days);
    calendar[date.toISOString().slice(0, 10)] = (days % 13) + 1;
  }
  const { light } = await createSnakeSvgs(calendar);
  const tracks = snakeTracks(light);
  const duration = Number(light.match(/data-animation-duration="(\d+)"/)[1]);
  assert.equal(tracks.length, 4);
  for (const track of tracks) {
    assert.deepEqual(
      [track[0].x, track[0].y],
      [track.at(-1).x, track.at(-1).y],
    );
    for (let index = 1; index < track.length; index++) {
      const previous = track[index - 1];
      const current = track[index];
      const distance =
        Math.abs(current.x - previous.x) + Math.abs(current.y - previous.y);
      const seconds = ((current.time - previous.time) * duration) / 100000;
      assert.ok(
        distance === 0 || distance / seconds < 48,
        "Snake exceeded one cell per 300ms",
      );
      assert.ok(
        current.x === previous.x || current.y === previous.y,
        "A snake segment cut diagonally across a corner",
      );
    }
  }
  for (const time of tracks[0].map((point) => point.time)) {
    const positions = tracks.map((track) => positionAt(track, time));
    for (let left = 0; left < positions.length; left++) {
      for (let right = left + 1; right < positions.length; right++) {
        const distance =
          Math.abs(positions[left].x - positions[right].x) +
          Math.abs(positions[left].y - positions[right].y);
        assert.ok(distance > 12, `Snake segments overlap at ${time}%`);
      }
    }
  }
});
