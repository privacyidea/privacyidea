/**
 * (c) NetKnights GmbH 2026,  https://netknights.it
 *
 * This code is free software; you can redistribute it and/or
 * modify it under the terms of the GNU AFFERO GENERAL PUBLIC LICENSE
 * as published by the Free Software Foundation; either
 * version 3 of the License, or any later version.
 *
 * This code is distributed in the hope that it will be useful,
 * but WITHOUT ANY WARRANTY; without even the implied warranty of
 * MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE. See the
 * GNU AFFERO GENERAL PUBLIC LICENSE for more details.
 *
 * You should have received a copy of the GNU Affero General Public
 * License along with this program.  If not, see <http://www.gnu.org/licenses/>.
 *
 * SPDX-License-Identifier: AGPL-3.0-or-later
 **/

import {
  parseTemplate,
  TmplAstBoundText,
  TmplAstElement,
  TmplAstRecursiveVisitor,
  TmplAstText
} from "@angular/compiler";
import { readdirSync, readFileSync } from "node:fs";
import { join, relative, resolve } from "node:path";

// A matTooltip on a button or link names the element only where the component imports TooltipAriaLabelDirective; a
// missing import changes nothing at build time. This spec finds every such element in the templates under src/app
// and fails when its component neither imports the directive nor names the element itself (aria-label,
// aria-labelledby or visible text).
const APP_DIR = resolve(__dirname, "../../..");
const DIRECTIVE = "TooltipAriaLabelDirective";

interface Finding {
  file: string;
  element: string;
  line: number;
}

class TooltipElementVisitor extends TmplAstRecursiveVisitor {
  tooltipElements = 0;
  readonly unnamed: { element: string; line: number }[] = [];

  override visitElement(element: TmplAstElement): void {
    if ((element.name === "button" || element.name === "a") && TooltipElementVisitor.hasTooltip(element)) {
      this.tooltipElements++;
      if (!TooltipElementVisitor.hasOwnName(element)) {
        this.unnamed.push({ element: element.name, line: element.sourceSpan.start.line + 1 });
      }
    }
    super.visitElement(element);
  }

  private static hasTooltip(element: TmplAstElement): boolean {
    return (
      element.attributes.some((attribute) => attribute.name === "matTooltip") ||
      element.inputs.some((input) => input.name === "matTooltip")
    );
  }

  private static hasOwnName(element: TmplAstElement): boolean {
    const naming = ["aria-label", "aria-labelledby", "ariaLabel", "ariaLabelledby"];
    return (
      element.attributes.some((attribute) => naming.includes(attribute.name)) ||
      element.inputs.some((input) => naming.includes(input.name)) ||
      TooltipElementVisitor.hasVisibleText(element)
    );
  }

  // Text of the element itself, ignoring subtrees that are hidden from assistive technology (an icon's ligature).
  private static hasVisibleText(element: TmplAstElement): boolean {
    return TooltipElementVisitor.anyVisibleText(element.children);
  }

  private static anyVisibleText(nodes: unknown[]): boolean {
    return nodes.some((node) => {
      if (node instanceof TmplAstText) {
        return node.value.trim().length > 0;
      }
      if (node instanceof TmplAstBoundText) {
        return true;
      }
      if (node instanceof TmplAstElement) {
        const hidden = node.attributes.some(
          (attribute) => attribute.name === "aria-hidden" && attribute.value === "true"
        );
        return !hidden && node.name !== "mat-icon" && TooltipElementVisitor.anyVisibleText(node.children);
      }
      // ng-template and control-flow blocks (@if branches, @for, @switch cases) hold their content in one of these.
      const block = node as { children?: unknown[]; branches?: unknown[]; cases?: unknown[]; empty?: unknown };
      return TooltipElementVisitor.anyVisibleText([
        ...(block.children ?? []),
        ...(block.branches ?? []),
        ...(block.cases ?? []),
        ...(block.empty ? [block.empty] : [])
      ]);
    });
  }
}

function sourceFiles(dir: string): string[] {
  return readdirSync(dir, { withFileTypes: true }).flatMap((entry) => {
    const path = join(dir, entry.name);
    return entry.isDirectory() ? sourceFiles(path) : [path];
  });
}

function scan(template: string, file: string): { tooltipElements: number; unnamed: Finding[] } {
  const visitor = new TooltipElementVisitor();
  const parsed = parseTemplate(template, file, { preserveWhitespaces: false });
  parsed.nodes.forEach((node) => node.visit(visitor));
  return { tooltipElements: visitor.tooltipElements, unnamed: visitor.unnamed.map((hit) => ({ file, ...hit })) };
}

describe("matTooltip buttons and links", () => {
  const files = sourceFiles(APP_DIR).filter((file) => !file.endsWith(".spec.ts"));

  // [component source, template text, template file] for every component with a template.
  const components = files
    .filter((file) => file.endsWith(".ts"))
    .flatMap((file): [string, string, string][] => {
      const source = readFileSync(file, "utf8");
      const external = /templateUrl:\s*"([^"]+)"/.exec(source);
      if (external) {
        const templateFile = resolve(file, "..", external[1]);
        return [[source, readFileSync(templateFile, "utf8"), templateFile]];
      }
      const inline = /template:\s*`([^`]*)`/.exec(source);
      return inline ? [[source, inline[1], file]] : [];
    });

  describe("scan", () => {
    const unnamed = (template: string): number => scan(template, "inline.html").unnamed.length;

    it("reports an icon-only button and link whose tooltip is the only name", () => {
      expect(unnamed('<button matTooltip="Add"><mat-icon>add</mat-icon></button>')).toBe(1);
      expect(unnamed('<a [matTooltip]="tip" href="/x"><mat-icon aria-hidden="true">add</mat-icon></a>')).toBe(1);
    });

    it("accepts an element that names itself", () => {
      expect(unnamed('<button matTooltip="Add" aria-label="Add item"><mat-icon>add</mat-icon></button>')).toBe(0);
      expect(unnamed('<button matTooltip="Add" [attr.aria-label]="label"><mat-icon>add</mat-icon></button>')).toBe(0);
      expect(unnamed('<button matTooltip="Add" aria-labelledby="x"><mat-icon>add</mat-icon></button>')).toBe(0);
      expect(unnamed('<button matTooltip="Add"><mat-icon>add</mat-icon> Add</button>')).toBe(0);
      expect(unnamed('<button matTooltip="Add"><span>{{ label }}</span></button>')).toBe(0);
      expect(unnamed('<button matTooltip="Add">@if (show) {<span>Add</span>}</button>')).toBe(0);
    });

    it("ignores elements that are not buttons or links, or have no tooltip", () => {
      expect(unnamed('<span matTooltip="Add"></span>')).toBe(0);
      expect(unnamed("<button><mat-icon>add</mat-icon></button>")).toBe(0);
    });

    it("finds an element inside a control-flow block", () => {
      expect(unnamed('@if (show) {<button matTooltip="Add"><mat-icon>add</mat-icon></button>}')).toBe(1);
    });
  });

  it("finds the component templates", () => {
    expect(components.length).toBeGreaterThan(100);
  });

  it("finds the buttons and links that carry a tooltip", () => {
    const total = components.reduce((sum, [, template, file]) => sum + scan(template, file).tooltipElements, 0);

    expect(total).toBeGreaterThan(50);
  });

  it("imports TooltipAriaLabelDirective wherever a tooltip is the only name of a button or link", () => {
    const missing = components
      .filter(([source]) => !source.includes(DIRECTIVE))
      .flatMap(([, template, file]) => scan(template, file).unnamed)
      .map((hit) => `${relative(APP_DIR, hit.file)}:${hit.line} <${hit.element} matTooltip> has no accessible name`);

    expect(missing).toEqual([]);
  });
});
