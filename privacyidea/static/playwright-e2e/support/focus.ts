import { Page } from "@playwright/test";

// Tabs through the page and returns the controls whose keyboard focus changes nothing on screen. A focused control
// must look different from the same control unfocused: its surroundings are captured focused, focus is taken away,
// and they are captured again; identical pixels mean no indicator.
export async function focusIndicatorMisses(page: Page, steps = 20): Promise<string[]> {
  await page.mouse.move(0, 0);
  const invisible: string[] = [];

  for (let i = 0; i < steps; i++) {
    await page.keyboard.press("Tab");
    const target = await page.evaluate(() => {
      const e = document.activeElement as HTMLElement | null;
      if (!e || e === document.body || !e.matches(":focus-visible")) {
        return null;
      }
      e.scrollIntoView({ block: "nearest", inline: "nearest" });
      const r = e.getBoundingClientRect();
      const name = e.tagName.toLowerCase() + (e.className ? "." + String(e.className).split(" ")[0] : "");
      return r.width > 0 && r.height > 0 && r.bottom > 0 && r.top < innerHeight
        ? { name, x: r.left - 8, y: r.top - 8, width: r.width + 16, height: r.height + 16 }
        : null;
    });
    if (!target) {
      continue;
    }
    const clip = {
      x: Math.max(0, target.x),
      y: Math.max(0, target.y),
      width: Math.min(target.width, 1900),
      height: Math.min(target.height, 400)
    };
    const focused = await page.screenshot({ clip, animations: "disabled" });
    await page.evaluate(() => (document.activeElement as HTMLElement).blur());
    const plain = await page.screenshot({ clip, animations: "disabled" });
    if (focused.equals(plain)) {
      invisible.push(target.name);
    }
    // Back on the same control, as the keyboard would have it.
    await page.keyboard.press("Shift+Tab");
    await page.keyboard.press("Tab");
  }
  return [...new Set(invisible)];
}
