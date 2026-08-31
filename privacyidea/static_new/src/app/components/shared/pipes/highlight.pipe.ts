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

import { inject, Pipe, PipeTransform, SecurityContext } from "@angular/core";
import { DomSanitizer } from "@angular/platform-browser";

@Pipe({
  name: "highlight",
  standalone: true
})
export class HighlightPipe implements PipeTransform {
  private sanitizer = inject(DomSanitizer);

  transform(value: string, searchTerm: string | string[], containsMarkup = false): string {
    const terms = (Array.isArray(searchTerm) ? searchTerm : [searchTerm]).filter((term) => !!term);
    if (terms.length === 0 || !value) {
      return containsMarkup ? (this.sanitizer.sanitize(SecurityContext.HTML, value) ?? "") : this.escapeHtml(value);
    }
    // Longer terms first so overlapping matches prefer the longer one in the alternation.
    const alternation = terms
      .sort((a, b) => b.length - a.length)
      .map((term) => term.replace(/[.*+?^${}()|[\]\\]/g, "\\$&"))
      .join("|");
    // g - global (all occurrences), i - case-insensitive
    const regex = new RegExp(alternation, "gi");
    const highlighted = containsMarkup ? this.highlightAroundMarkup(value, regex) : this.highlightEscaped(value, regex);
    return this.sanitizer.sanitize(SecurityContext.HTML, highlighted) ?? "";
  }

  // Match against the raw value and HTML-escape the matched and unmatched pieces separately. Escaping
  // the whole string first would let the regex match inside generated entities (e.g. searching "&"
  // hitting the "&" of "&amp;"), corrupting the output and failing to match terms with HTML metacharacters.
  private highlightEscaped(value: string, regex: RegExp): string {
    let highlighted = "";
    let lastIndex = 0;
    for (const match of value.matchAll(regex)) {
      const start = match.index!;
      highlighted += this.escapeHtml(value.slice(lastIndex, start));
      highlighted += `<span class="highlight">${this.escapeHtml(match[0])}</span>`;
      lastIndex = start + match[0].length;
    }
    return highlighted + this.escapeHtml(value.slice(lastIndex));
  }

  // The value already is HTML, so tags and entities are handed through untouched and only the text
  // between them is searched. Escaping would show the markup as literal text; sanitizing the result
  // still strips everything active.
  private highlightAroundMarkup(value: string, regex: RegExp): string {
    let highlighted = "";
    let lastIndex = 0;
    for (const markup of value.matchAll(/<[^>]*>|&[a-zA-Z#][a-zA-Z0-9]*;/g)) {
      const start = markup.index!;
      highlighted += this.highlightPlain(value.slice(lastIndex, start), regex);
      highlighted += markup[0];
      lastIndex = start + markup[0].length;
    }
    return highlighted + this.highlightPlain(value.slice(lastIndex), regex);
  }

  private highlightPlain(text: string, regex: RegExp): string {
    let highlighted = "";
    let lastIndex = 0;
    for (const match of text.matchAll(regex)) {
      const start = match.index!;
      highlighted += text.slice(lastIndex, start);
      highlighted += `<span class="highlight">${match[0]}</span>`;
      lastIndex = start + match[0].length;
    }
    return highlighted + text.slice(lastIndex);
  }

  escapeHtml(text: string): string {
    if (!text) return "";
    return text.replace(/[&<>"']/g, function (c) {
      return { "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;" }[c] || c;
    });
  }
}
