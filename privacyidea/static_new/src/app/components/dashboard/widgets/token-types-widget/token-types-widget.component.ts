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
import { Component, computed, effect, inject, OnInit, signal } from "@angular/core";
import { MatIcon } from "@angular/material/icon";
import { MatTooltip } from "@angular/material/tooltip";
import { RouterLink } from "@angular/router";
import { PiResponse } from "@app/app.component";
import { ROUTE_PATHS } from "@app/route_paths";
import { TokenTypesWidgetIconComponent } from "@components/dashboard/widgets/token-types-widget/token-types-widget-icon.component";
import { WidgetStateComponent } from "@components/dashboard/widgets/widget-state/widget-state.component";
import { FilterValue } from "@core/models/filter_value/filter_value";
import { DashboardWidget, WidgetSize } from "@models/dashboard";
import { AuthService, AuthServiceInterface } from "@services/auth/auth.service";
import { DashboardDataRef, DashboardDataStore } from "@services/dashboard/dashboard-data-store.service";
import { TokenCount, TokenService, TokenServiceInterface, TokenTypeKey } from "@services/token/token.service";
import { tokenTypes } from "@utils/token.utils";
import { catchError, map, merge, of, scan } from "rxjs";

export interface TokenTypeCount {
  key: TokenTypeKey;
  name: string;
  count: number | null;
  stale?: boolean;
}

interface TokenTypeAccumulator {
  items: TokenTypeCount[];
  indexByKey: Map<TokenTypeKey, number>;
}

@Component({
  selector: "app-token-types-widget",
  standalone: true,
  imports: [MatIcon, MatTooltip, RouterLink, WidgetStateComponent],
  templateUrl: "./token-types-widget.component.html",
  styleUrl: "./token-types-widget.component.scss"
})
export class TokenTypesWidgetComponent extends DashboardWidget implements OnInit {
  static override readonly type = "token-types";
  static override readonly requiredAction = "tokenlist";
  static override readonly title = $localize`Tokens by Type`;
  static override readonly icon = "shield";
  static override readonly headerIcon = TokenTypesWidgetIconComponent;
  static override readonly defaultSize: WidgetSize = { cols: 6, rows: 5 };
  static override readonly minSize: WidgetSize = { cols: 4, rows: 3 };
  static override readonly maxSize: WidgetSize = { cols: 12, rows: 12 };

  protected readonly routePaths = ROUTE_PATHS;

  private readonly tokenService: TokenServiceInterface = inject(TokenService);
  private readonly authService: AuthServiceInterface = inject(AuthService);
  private readonly store = inject(DashboardDataStore);

  private readonly typeCountsRef = signal<DashboardDataRef<TokenTypeCount[]> | null>(null);
  private readonly expectedLoadCount = signal(tokenTypes.length);

  readonly typeCounts = computed<TokenTypeCount[]>(() => {
    const results = this.typeCountsRef()?.value();
    if (!results) {
      return [];
    }
    return results
      .filter((entry) => entry.count === null || entry.count > 0)
      .sort((a, b) => (b.count ?? -1) - (a.count ?? -1));
  });

  readonly loadedTypeCount = computed(() => this.typeCountsRef()?.value()?.length ?? 0);
  readonly hasPartialData = computed(
    () => this.loadedTypeCount() > 0 && this.loadedTypeCount() < this.expectedLoadCount()
  );
  readonly loadingMore = computed(() => this.typeCountsRef()?.revalidating() ?? false);
  override readonly partialLoading = computed(() => this.hasPartialData() && this.loadingMore());
  readonly allTypesFailed = computed(() => {
    const results = this.typeCountsRef()?.value();
    return !!results && results.length > 0 && results.every((entry) => entry.count === null);
  });
  readonly allTypesLoaded = computed(() => this.loadedTypeCount() >= this.expectedLoadCount());
  override readonly loading = computed(() => {
    const state = this.state();
    if (state === "denied" || state === "error") {
      return false;
    }
    return !this.allTypesLoaded() || this.loadingMore();
  });

  constructor() {
    super();
    effect(() => {
      const ref = this.typeCountsRef();
      if (!ref) {
        return;
      }
      if (ref.error() || (!ref.revalidating() && this.allTypesFailed())) {
        this.state.set("error");
        return;
      }
      if (ref.value() !== undefined) {
        this.state.set("ready");
      } else {
        this.state.set("loading");
      }
    });
  }

  showType(type: TokenTypeKey): void {
    this.tokenService.presetFilter.set(new FilterValue().addEntry("type", type));
  }

  ngOnInit(): void {
    this.load(false);
  }

  override reload(): void {
    const previous = this.store.peek<TokenTypeCount[]>("dashboard:tokens:by_type")?.value();
    this.store.invalidate("dashboard:tokens:by_type");
    this.load(true, previous);
  }

  private load(forceAllTypes: boolean, previousCounts?: TokenTypeCount[]): void {
    if (!this.authService.actionAllowed("tokenlist")) {
      this.state.set("denied");
      return;
    }

    const cachedRef = this.store.peek<TokenTypeCount[]>("dashboard:tokens:by_type");
    const cached = cachedRef?.value() ?? undefined;
    const keysToLoad =
      forceAllTypes || cached === undefined
        ? tokenTypes.map((type) => type.key)
        : cached.filter((entry) => entry.count === null || entry.count > 0).map((entry) => entry.key);

    this.expectedLoadCount.set(keysToLoad.length);

    if (cachedRef) {
      this.typeCountsRef.set(cachedRef);
    }

    if (keysToLoad.length === 0) {
      return;
    }

    const typeByKey = new Map(tokenTypes.map((type) => [type.key, type]));
    const initialCounts = cached ?? [];
    const previousByKey = new Map((previousCounts ?? initialCounts).map((entry) => [entry.key, entry]));
    const initialAccumulator: TokenTypeAccumulator = {
      items: initialCounts,
      indexByKey: new Map(initialCounts.map((entry, index) => [entry.key, index]))
    };

    this.typeCountsRef.set(
      this.store.load("dashboard:tokens:by_type", () =>
        merge(
          ...keysToLoad.map((typeKey) => {
            const name = typeByKey.get(typeKey)?.name || typeKey;
            return this.tokenService.getTokenCount({ type: typeKey }).pipe(
              map<PiResponse<TokenCount>, TokenTypeCount>((response) => ({
                key: typeKey,
                name,
                count: response.result?.value?.count ?? 0
              })),
              catchError(() => {
                const fallback = previousByKey.get(typeKey);
                if (fallback && fallback.count !== null) {
                  return of<TokenTypeCount>({ key: typeKey, name, count: fallback.count, stale: true });
                }
                return of<TokenTypeCount>({ key: typeKey, name, count: null });
              })
            );
          })
        ).pipe(
          scan((accumulated: TokenTypeAccumulator, entry) => {
            const index = accumulated.indexByKey.get(entry.key);
            const nextItems = [...accumulated.items];

            if (index === undefined) {
              accumulated.indexByKey.set(entry.key, nextItems.length);
              nextItems.push(entry);
            } else {
              nextItems[index] = entry;
            }

            return {
              items: nextItems,
              indexByKey: accumulated.indexByKey
            };
          }, initialAccumulator),
          map((accumulated) => accumulated.items)
        )
      )
    );
  }
}
