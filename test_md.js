const fs = require('fs');

const text = fs.readFileSync('apps/mobile/src/components/astrology/reading.txt', 'utf8');

function testParser(text) {
  const lines = text.split('\n');
  const results = [];

  for (let i = 0; i < Math.min(lines.length, 10); i++) {
    const line = lines[i].trim();
    if (!line) {
      results.push(`[Line ${i}]: EMPTY`);
      continue;
    }

    if (line.startsWith('# ')) {
      results.push(`[Line ${i}]: MATCHED H1: "${line.slice(2)}"`);
      continue;
    }
    if (line.startsWith('## ')) {
      results.push(`[Line ${i}]: MATCHED H2: "${line.slice(3)}"`);
      continue;
    }
    if (line.startsWith('### ')) {
      results.push(`[Line ${i}]: MATCHED H3: "${line.slice(4)}"`);
      continue;
    }

    results.push(`[Line ${i}]: MATCHED Paragraph: "${line}"`);
  }

  return results;
}

console.log(testParser(text).join('\n'));
