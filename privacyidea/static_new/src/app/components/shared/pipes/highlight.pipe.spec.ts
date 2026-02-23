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

import { HighlightPipe } from './highlight.pipe';
import { DomSanitizer } from '@angular/platform-browser';
import { SecurityContext } from "@angular/core";

describe('HighlightPipe', () => {
  let sanitizer: DomSanitizer;
  let pipe: HighlightPipe;

  beforeEach(() => {
    // Minimal mock for DomSanitizer
    sanitizer = {
      sanitize: (ctx: SecurityContext, value: string | null) => value,
    } as DomSanitizer;
    pipe = new HighlightPipe(sanitizer);
  });

  it('should return escaped HTML if no search term is provided', () => {
    const result = pipe.transform('Hello <b>World</b> & "Test"', '');
    expect(result).toBe('Hello &lt;b&gt;World&lt;/b&gt; &amp; &quot;Test&quot;');
  });

  it('should return empty value if value is empty', () => {
    const result = pipe.transform('', 'test');
    expect(result).toBe('');
  });

  it('should highlight all matches of the search term (case-insensitive)', () => {
    const result = pipe.transform('Hello World, hello world!', 'hello');
    expect(result).toBe('<span class="highlight">Hello</span> World, <span class="highlight">hello</span> world!');
  });

  it('should return escaped HTML if search term is not found', () => {
    const result = pipe.transform('Hello <b>World</b>', 'foo');
    expect(result).toBe('Hello &lt;b&gt;World&lt;/b&gt;');
  });

  it('should escape special characters in value and highlight search term', () => {
    const result = pipe.transform('1 < 2 & 3 > 2', '2');
    expect(result).toBe('1 &lt; <span class="highlight">2</span> &amp; 3 &gt; <span class="highlight">2</span>');
  });

  it('should handle special regex characters in search term', () => {
    const result = pipe.transform('a+b*c', '+b*');
    expect(result).toBe('a<span class="highlight">+b*</span>c');
  });

  it('should not break on XSS attempt in value', () => {
    const result = pipe.transform('<img src=x onerror=alert(1)>', '');
    expect(result).toBe('&lt;img src=x onerror=alert(1)&gt;');
  });

  it('should not break on XSS attempt in search term', () => {
    const result = pipe.transform('normal text', '<script>alert(1)</script>');
    expect(result).toBe('normal text');
  });
});

