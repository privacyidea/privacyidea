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

import { LiveAnnouncer } from "@angular/cdk/a11y";
import { inject, Injectable, signal } from "@angular/core";
import { Title } from "@angular/platform-browser";
import { RouterStateSnapshot, TitleStrategy } from "@angular/router";

/**
 * Names the page for whoever cannot see it: the document title, a heading the page itself does not draw, and a
 * polite announcement when the page changes (the page does not reload, so nothing else tells a screen reader that it
 * moved). The name is the `title` of the activated route.
 */
@Injectable({ providedIn: "root" })
export class PageTitleStrategy extends TitleStrategy {
  private readonly title = inject(Title);
  private readonly announcer = inject(LiveAnnouncer);
  private readonly appTitle = this.title.getTitle();

  // The page's name, for the heading the app shell renders.
  readonly heading = signal("");
  private path = "";

  override updateTitle(snapshot: RouterStateSnapshot): void {
    const heading = this.buildTitle(snapshot) ?? "";
    const path = snapshot.url.split(/[?#]/)[0];
    // A navigation within the same page (a query parameter, a sort, a filter) keeps the path and the heading, so it
    // announces nothing. Another record of the same list shares the heading but not the path, so it is announced.
    const changed = heading !== this.heading() || path !== this.path;
    this.heading.set(heading);
    this.path = path;
    this.title.setTitle(heading ? `${heading} - ${this.appTitle}` : this.appTitle);
    if (heading && changed) {
      void this.announcer.announce(heading, "polite");
    }
  }
}
