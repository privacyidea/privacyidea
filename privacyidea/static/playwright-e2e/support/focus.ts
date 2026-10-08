import { Page } from "@playwright/test";

export interface FocusResult {
  // Controls inside the page content (.admin-content) whose focus changes nothing on screen.
  misses: string[];
  // How many distinct controls inside the page content were checked; the shell around it (toolbar, navigation) is
  // walked through but not counted.
  checked: number;
}

// Resolves once the page's finite animations and transitions (a focus ring fades in) have run out and the browser has
// painted the result.
const painted = (page: Page) =>
  page.evaluate(async () => {
    const finite = document.getAnimations().filter((a) => (a.effect?.getComputedTiming().iterations ?? 1) !== Infinity);
    await Promise.allSettled(finite.map((a) => a.finished));
    await new Promise<void>((done) => requestAnimationFrame(() => requestAnimationFrame(() => done())));
  });

// The box of the focused control once two frames in a row agree on it.
async function settledRect(page: Page): Promise<{ x: number; y: number; width: number; height: number }> {
  const measure = () =>
    page.evaluate(
      () =>
        new Promise<{ x: number; y: number; width: number; height: number }>((done) =>
          requestAnimationFrame(() => {
            const r = (document.activeElement as HTMLElement).getBoundingClientRect();
            done({ x: r.left, y: r.top, width: r.width, height: r.height });
          })
        )
    );
  let last = await measure();
  for (let i = 0; i < 30; i++) {
    const now = await measure();
    if (now.x === last.x && now.y === last.y && now.width === last.width && now.height === last.height) {
      return now;
    }
    last = now;
  }
  return last;
}

// Tabs through the page and returns the controls whose keyboard focus changes nothing on screen. A focused control
// must look different from the same control unfocused: its surroundings are captured focused, focus is taken away,
// and they are captured again; identical pixels mean no indicator. The walk goes on past the shell until `wanted`
// controls of the page content were checked or `maxStops` Tab presses were made.
export async function focusIndicatorMisses(page: Page, wanted = 40, maxStops = 150): Promise<FocusResult> {
  await page.mouse.move(0, 0);
  // A text field's blinking caret is on in one capture and off in the other; it is not a focus indicator.
  const style = await page.addStyleTag({ content: "* { caret-color: transparent !important; }" });
  const invisible: string[] = [];
  const checkedControls = new Set<string>();

  try {
    for (let i = 0; i < maxStops && checkedControls.size < wanted; i++) {
      await page.keyboard.press("Tab");
      const target = await page.evaluate(() => {
        const e = document.activeElement as HTMLElement | null;
        if (!e || e === document.body || !e.matches(":focus-visible") || !e.closest(".admin-content")) {
          return null;
        }
        e.scrollIntoView({ block: "nearest", inline: "nearest" });
        const r = e.getBoundingClientRect();
        const name = e.tagName.toLowerCase() + (e.className ? "." + String(e.className).split(" ")[0] : "");
        // The position among the page's focusable elements tells two controls of the same kind apart.
        const index = [...document.querySelectorAll(".admin-content *")].indexOf(e);
        return r.width > 0 && r.height > 0 && r.bottom > 0 && r.top < innerHeight
          ? { name, index, x: r.left - 8, y: r.top - 8, width: r.width + 16, height: r.height + 16 }
          : null;
      });
      if (!target) {
        continue;
      }
      if (checkedControls.has(String(target.index))) {
        continue;
      }
      checkedControls.add(String(target.index));
      // The page may still be scrolling the control into view; the clip follows it once it stands still.
      const at = await settledRect(page);
      await painted(page);
      const clip = {
        x: Math.max(0, at.x - 8),
        y: Math.max(0, at.y - 8),
        width: Math.min(at.width + 16, 1900),
        height: Math.min(at.height + 16, 400)
      };
      const focused = await page.screenshot({ clip, animations: "disabled" });
      await page.evaluate(() => (document.activeElement as HTMLElement).blur());
      await painted(page);
      const plain = await page.screenshot({ clip, animations: "disabled" });
      if (focused.equals(plain)) {
        invisible.push(target.name);
      }
      // Back on the same control, as the keyboard would have it.
      await page.keyboard.press("Shift+Tab");
      await page.keyboard.press("Tab");
    }
  } finally {
    await style.evaluate((node) => (node as Element).remove());
  }
  return { misses: [...new Set(invisible)], checked: checkedControls.size };
}
