// Units are one key pitch. Both the markup and the recognition templates use these rows.
export const rows = ['qwertyuiop', 'asdfghjkl', 'zxcvbnm'];
export const keyCenters = Object.fromEntries(rows.flatMap((row, r) =>
  [...row].map((letter, i) => [letter, [i + [0.5, 1, 2][r], r + 0.5]])
));

const sampleCount = 32;

function resample(points) {
  const distances = [0];
  for (let i = 1; i < points.length; i++) {
    const [x, y] = points[i];
    distances.push(distances[i - 1] + Math.hypot(x - points[i - 1][0], y - points[i - 1][1]));
  }
  const total = distances.at(-1);
  const samples = new Float32Array(sampleCount * 2);
  let right = 1;
  for (let i = 0; i < sampleCount; i++) {
    const at = total * i / (sampleCount - 1);
    while (right < points.length - 1 && distances[right] < at) right++;
    const a = points[right - 1];
    const b = points[right] ?? a;
    const fraction = (at - distances[right - 1]) / ((distances[right] - distances[right - 1]) || 1);
    samples[i * 2] = a[0] + (b[0] - a[0]) * fraction;
    samples[i * 2 + 1] = a[1] + (b[1] - a[1]) * fraction;
  }
  return samples;
}

function distance(a, i, b, j) {
  return Math.hypot(a[i] - b[j], a[i + 1] - b[j + 1]);
}

function alignedDistance(a, b) {
  let previous = new Float64Array(sampleCount + 1).fill(Infinity);
  let current = new Float64Array(sampleCount + 1);
  previous[0] = 0;
  for (let i = 0; i < sampleCount; i++) {
    current[0] = Infinity;
    for (let j = 1; j <= sampleCount; j++) {
      current[j] = distance(a, 2 * i, b, 2 * (j - 1)) +
        Math.min(current[j - 1], previous[j], previous[j - 1]);
    }
    [previous, current] = [current, previous];
  }
  return previous[sampleCount] / sampleCount;
}

export function makeRecognizer(words) {
  const buckets = new Map();
  words.forEach((word, rank) => {
    const start = word[0], end = word.at(-1);
    const id = start + end;
    if (!buckets.has(id)) buckets.set(id, []);
    buckets.get(id).push({word, rank, path: resample([...word].map(letter => keyCenters[letter]))});
  });
  return function recognize(points) {
    if (points.length < 2) return [];
    const path = resample(points);
    const shortlist = [];
    for (const [id, entries] of buckets) {
      const start = distance(path, 0, keyCenters[id[0]], 0);
      const end = distance(path, path.length - 2, keyCenters[id[1]], 0);
      if (start > 1.25 || end > 1.25) continue;
      const endpoints = start + end;
      for (const entry of entries) {
        let shape = 0;
        for (let i = 0; i < path.length; i += 8) shape += distance(path, i, entry.path, i);
        shortlist.push({entry, endpoints, score: endpoints + shape / 8});
      }
    }
    const finalists = shortlist.sort((a, b) => a.score - b.score).slice(0, 48);
    for (const candidate of finalists) {
      const {entry, endpoints} = candidate;
      candidate.score = alignedDistance(path, entry.path) + endpoints * 0.8 + Math.log1p(entry.rank) * 0.012;
    }
    return finalists.sort((a, b) => a.score - b.score).slice(0, 3).map(result => result.entry.word);
  };
}
