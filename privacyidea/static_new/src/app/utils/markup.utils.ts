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

export interface MarkupSegment {
  text: string;
  isMarkup: boolean;
}

// Tags with their attributes, where a quoted value may contain a ">", and character entities.
// A "<" that does not start a tag name is left in the text, so an unescaped one only affects
// itself instead of swallowing everything up to the next ">".
const markupPattern = /<\/?[a-zA-Z][^>"']*(?:(?:"[^"]*"|'[^']*')[^>"']*)*>|&[a-zA-Z#][a-zA-Z0-9]*;/g;

// Splits an HTML string into its markup and text parts, in order. Deciding whether a text matches a
// search term and highlighting the matches in it are both done on the text parts only, so that a
// term can never match a tag or entity name in one of the two and not in the other.
export function splitMarkupSegments(value: string): MarkupSegment[] {
  const segments: MarkupSegment[] = [];
  let lastIndex = 0;
  for (const markup of value.matchAll(markupPattern)) {
    const start = markup.index!;
    if (start > lastIndex) {
      segments.push({ text: value.slice(lastIndex, start), isMarkup: false });
    }
    segments.push({ text: markup[0], isMarkup: true });
    lastIndex = start + markup[0].length;
  }
  if (lastIndex < value.length) {
    segments.push({ text: value.slice(lastIndex), isMarkup: false });
  }
  return segments;
}
