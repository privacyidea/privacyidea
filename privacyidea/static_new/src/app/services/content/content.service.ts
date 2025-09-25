/**
 * (c) NetKnights GmbH 2025,  https://netknights.it
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
import { computed, inject, Injectable, Signal, signal, WritableSignal } from "@angular/core";
import { toSignal } from "@angular/core/rxjs-interop";
import { NavigationEnd, Router } from "@angular/router";
import { filter, map, pairwise, startWith } from "rxjs";
import { ROUTE_PATHS } from "../../route_paths";

export interface ContentServiceInterface {
  router: Router;
  routeUrl: Signal<string>;
  previousUrl: Signal<string>;
  isProgrammaticTabChange: WritableSignal<boolean>;
  tokenSerial: WritableSignal<string>;
  containerSerial: WritableSignal<string>;
  tokenSelected: (serial: string) => void;
  containerSelected: (containerSerial: string) => void;
}

@Injectable({ providedIn: "root" })
export class ContentService {
  router = inject(Router);
  private readonly _urlPair = toSignal(
    this.router.events.pipe(
      filter((e): e is NavigationEnd => e instanceof NavigationEnd),
      map((e) => e.urlAfterRedirects),
      startWith(this.router.url),
      pairwise()
    ),
    { initialValue: [this.router.url, this.router.url] as const }
  );
  readonly routeUrl = computed(() => this._urlPair()[1]);
  readonly previousUrl = computed(() => this._urlPair()[0]);
  isProgrammaticTabChange = signal(false);
  tokenSerial = signal("");
  containerSerial = signal("");

  tokenSelected(serial: string) {
    if (this.routeUrl().includes("containers")) {
      this.isProgrammaticTabChange.set(true);
    }
    this.router.navigateByUrl(ROUTE_PATHS.TOKENS_DETAILS + serial);
    this.tokenSerial.set(serial);
  }

  containerSelected(containerSerial: string) {
    if (!this.routeUrl().includes("containers")) {
      this.isProgrammaticTabChange.set(true);
    }
    this.router.navigateByUrl(ROUTE_PATHS.TOKENS_CONTAINERS_DETAILS + containerSerial);
    this.containerSerial.set(containerSerial);
  }
}
