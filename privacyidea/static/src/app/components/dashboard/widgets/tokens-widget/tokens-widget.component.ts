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
import { Component, computed, effect, inject, signal, TemplateRef, untracked, viewChild } from "@angular/core";
import { MatButton } from "@angular/material/button";
import { MatIcon } from "@angular/material/icon";
import { MatMenu, MatMenuItem, MatMenuTrigger } from "@angular/material/menu";
import { RouterLink } from "@angular/router";
import { PiResponse } from "@app/app.component";
import { ROUTE_PATHS } from "@app/route_paths";
import { TokensWidgetIconComponent } from "@components/dashboard/widgets/tokens-widget/tokens-widget-icon.component";
import { WidgetStateComponent } from "@components/dashboard/widgets/widget-state/widget-state.component";
import { FilterValue } from "@core/models/filter_value/filter_value";
import { DashboardWidget, WidgetSize } from "@models/dashboard";
import { AuthService, AuthServiceInterface } from "@services/auth/auth.service";
import { DashboardDataRef, DashboardDataStore } from "@services/dashboard/dashboard-data-store.service";
import { DashboardLayoutService, DashboardLayoutServiceInterface } from "@services/dashboard/dashboard-layout.service";
import { RealmService, RealmServiceInterface } from "@services/realm/realm.service";
import { TokenCount, TokenCountParams, TokenService, TokenServiceInterface } from "@services/token/token.service";
import { UserCount, UserListResponseDetail, UserService, UserServiceInterface } from "@services/user/user.service";
import { catchError, forkJoin, of } from "rxjs";

/** Key the chosen realm is stored under in the widget instance settings. Empty value: the default realm. */
const REALM_SETTING = "realm";

export interface TokenCounts {
  total: number;
  hardware: number;
  software: number;
  unassigned_hardware: number;
  unassigned_software: number;
}

/**
 * Both counts come from one listing of the users, so they add up to the users of the realm. A count
 * is null while the numbers behind it are missing or unreadable. ``skippedResolvers`` names the
 * resolvers left out of both, so a partial count can say what it is missing.
 */
export interface UserTokenCounts {
  withTokens: number | null;
  withoutTokens: number | null;
  skippedResolvers: string[];
}

interface TokenCountResponses {
  total: PiResponse<TokenCount>;
  hardware: PiResponse<TokenCount>;
  software: PiResponse<TokenCount>;
  unassigned_hardware: PiResponse<TokenCount>;
  unassigned_software: PiResponse<TokenCount>;
}

type UserCountResponse = PiResponse<UserCount, UserListResponseDetail | undefined>;

@Component({
  selector: "app-tokens-widget",
  standalone: true,
  imports: [MatButton, MatIcon, MatMenu, MatMenuItem, MatMenuTrigger, RouterLink, WidgetStateComponent],
  templateUrl: "./tokens-widget.component.html",
  styleUrl: "./tokens-widget.component.scss"
})
export class TokensWidgetComponent extends DashboardWidget {
  static override readonly type = "tokens";
  static override readonly requiredAction = "tokenlist";
  static override readonly title = $localize`:@@dashboard.tokenUsage:Token Usage`;
  static override readonly icon = "shield";
  static override readonly titleLink = ROUTE_PATHS.TOKENS;
  static override readonly titleLinkAction = "tokenlist";
  static override readonly headerIcon = TokensWidgetIconComponent;
  static override readonly defaultSize: WidgetSize = { cols: 6, rows: 7 };
  static override readonly minSize: WidgetSize = { cols: 4, rows: 3 };
  static override readonly maxSize: WidgetSize = { cols: 12, rows: 11 };

  // Read by the widget frame, which renders these in its header.
  override readonly headerActions = viewChild<TemplateRef<unknown>>("headerActions");

  protected readonly routePaths = ROUTE_PATHS;

  private readonly tokenService: TokenServiceInterface = inject(TokenService);
  private readonly userService: UserServiceInterface = inject(UserService);
  private readonly authService: AuthServiceInterface = inject(AuthService);
  private readonly realmService: RealmServiceInterface = inject(RealmService);
  private readonly layoutService: DashboardLayoutServiceInterface = inject(DashboardLayoutService);
  private readonly store = inject(DashboardDataStore);

  // Fetched next to the token counts, not with them: a resolver that does not answer would
  // otherwise hold back the counts for as long as it takes to time out.
  private readonly dataRef = signal<DashboardDataRef<TokenCountResponses> | null>(null);
  private readonly usersRef = signal<DashboardDataRef<UserCountResponse | null> | null>(null);

  override readonly partialLoading = computed(
    () => (this.dataRef()?.revalidating() ?? false) || (this.usersRef()?.revalidating() ?? false)
  );
  override readonly refreshFailed = computed(() => {
    const ref = this.dataRef();
    return !!ref && ref.error() && ref.value() !== undefined;
  });

  readonly canListUsers = computed(() => this.authService.actionAllowed("userlist"));

  /**
   * The realm counted, which is always a single one: users can only be listed per realm, and across
   * every realm the "without tokens" count would walk every user store. The stored choice wins, then
   * the default realm, then the first realm there is. A stored realm that no longer exists is
   * skipped once the realms are known; before that it is kept, so the label does not flicker.
   * Empty only while none of them is known yet, or when there is no realm at all.
   */
  readonly realm = computed<string>(() => {
    const stored = this.instance()?.settings?.[REALM_SETTING];
    const realmsKnown = this.realmService.realmResource.hasValue();
    if (typeof stored === "string" && stored && (!realmsKnown || this.realmOptions().includes(stored))) {
      return stored;
    }
    return this.realmService.defaultRealm() || this.realmOptions()[0] || "";
  });

  /** There is nothing to count: no realm is configured, and none is on its way either. */
  readonly noRealm = computed(
    () => !this.realm() && this.realmService.defaultRealmResolved() && !this.realmService.realmResource.isLoading()
  );

  readonly realmLabel = computed(() => this.realm() || $localize`:@@dashboard.selectRealm:Select realm`);

  readonly realmOptions = computed(() => this.realmService.realmOptions());

  readonly skippedResolverNames = computed(() => this.userCounts().skippedResolvers.join(", "));

  /** An em dash while a count is on its way or turned out not to be countable. */
  readonly withTokensLabel = computed(() => this.countLabel(this.userCounts().withTokens));

  readonly withoutTokensLabel = computed(() => this.countLabel(this.userCounts().withoutTokens));

  readonly counts = computed<TokenCounts>(() => {
    const results = this.dataRef()?.value();
    return {
      total: results?.total.result?.value?.count ?? 0,
      hardware: results?.hardware.result?.value?.count ?? 0,
      software: results?.software.result?.value?.count ?? 0,
      unassigned_hardware: results?.unassigned_hardware.result?.value?.count ?? 0,
      unassigned_software: results?.unassigned_software.result?.value?.count ?? 0
    };
  });

  readonly showHardware = computed(() => {
    const { hardware, total } = this.counts();
    return hardware > 0 && hardware !== total;
  });

  readonly showSoftware = computed(() => {
    const { software, total } = this.counts();
    return software > 0 && software !== total;
  });

  readonly distinguishKinds = computed(() => {
    const { hardware, software } = this.counts();
    return hardware > 0 && software > 0;
  });

  readonly unassignedTotal = computed(() => {
    const { unassigned_hardware, unassigned_software } = this.counts();
    return unassigned_hardware + unassigned_software;
  });

  readonly userCounts = computed<UserTokenCounts>(() => {
    const response = this.usersRef()?.value();
    const counts = response?.result?.value;
    return {
      withTokens: counts?.with_tokens ?? null,
      withoutTokens: counts ? counts.count - counts.with_tokens : null,
      skippedResolvers: response?.detail?.skipped_resolvers ?? []
    };
  });

  // The realm the current data was loaded for, so the effect below does not load a realm again
  // that selectRealm already loaded.
  private loadedRealm: string | null = null;

  constructor() {
    super();
    // The default realm arrives after the widget is created, so the first load waits for it.
    effect(() => {
      const realm = this.realm();
      const resolved = this.realmService.defaultRealmResolved();
      untracked(() => {
        if (realm) {
          if (realm !== this.loadedRealm) {
            this.load(realm);
          }
        } else if (this.authService.actionAllowed("tokenlist")) {
          this.dropLoadedRealm();
          this.dataRef.set(null);
          this.usersRef.set(null);
          this.state.set(resolved ? "ready" : "loading");
        } else {
          this.state.set("denied");
        }
      });
    });
    effect(() => {
      const ref = this.dataRef();
      if (!ref) {
        return;
      }
      const value = ref.value();
      if (value === undefined) {
        this.state.set(ref.error() ? "error" : "loading");
        return;
      }
      this.state.set(Object.values(value).every((response) => response.result?.status === true) ? "ready" : "error");
    });
  }

  showAllTokens(): void {
    this.tokenService.presetFilter.set(this.withRealm(new FilterValue()));
  }

  showKind(kind: "hardware" | "software", unassignedOnly = false): void {
    let filter = new FilterValue().addEntry("infokey", "tokenkind").addEntry("infovalue", kind);
    if (unassignedOnly) {
      filter = filter.addEntry("assigned", "False");
    }
    this.tokenService.presetFilter.set(this.withRealm(filter));
  }

  showUnassigned(): void {
    this.tokenService.presetFilter.set(this.withRealm(new FilterValue().addEntry("assigned", "False")));
  }

  showUsers(hasTokens: boolean): void {
    this.userService.presetFilter.set(new FilterValue().addEntry("has_tokens", hasTokens ? "True" : "False"));
  }

  /** Count the tokens and users of this realm. */
  selectRealm(realm: string): void {
    const previous = this.realm();
    if (!realm || realm === previous) {
      return;
    }
    const id = this.instance()?.id;
    if (id) {
      this.layoutService.updateWidgetSettings(id, { [REALM_SETTING]: realm });
    }
    // The load is given the new realm: the instance input only carries it after the next
    // change detection run, so reading it back here would still yield the previous one.
    this.load(realm);
  }

  override reload(): void {
    const realm = this.realm();
    if (realm) {
      this.load(realm);
    }
  }

  private countLabel(count: number | null): string {
    return count === null ? "—" : `${count}`;
  }

  private storeKey(realm: string): string {
    return `dashboard:tokens:${realm}`;
  }

  private usersStoreKey(realm: string): string {
    return `dashboard:token-users:${realm}`;
  }

  /**
   * Adds the realm as an exact token realm, so the list shows the tokens these counts counted rather
   * than those of every realm containing the name. Applied last, because every other change to a
   * filter drops the exact marking.
   */
  private withRealm(filter: FilterValue): FilterValue {
    return filter.addEntry("tokenrealm", this.realm()).withExactKey("tokenrealm");
  }

  /** Dropped, or the entries of every realm ever loaded would be refetched on each refresh. */
  private dropLoadedRealm(): void {
    if (this.loadedRealm) {
      this.store.invalidate(this.storeKey(this.loadedRealm));
      this.store.invalidate(this.usersStoreKey(this.loadedRealm));
    }
    this.loadedRealm = null;
  }

  private load(realm: string): void {
    if (!this.authService.actionAllowed("tokenlist")) {
      this.state.set("denied");
      return;
    }
    if (this.loadedRealm !== realm) {
      this.dropLoadedRealm();
    }
    this.loadedRealm = realm;
    const scope: TokenCountParams = { tokenrealm: realm };
    this.dataRef.set(
      this.store.load(this.storeKey(realm), () =>
        forkJoin({
          total: this.tokenService.getTokenCount(scope),
          hardware: this.tokenService.getTokenCount({ ...scope, infokey: "tokenkind", infovalue: "hardware" }),
          software: this.tokenService.getTokenCount({ ...scope, infokey: "tokenkind", infovalue: "software" }),
          unassigned_hardware: this.tokenService.getTokenCount({
            ...scope,
            infokey: "tokenkind",
            infovalue: "hardware",
            assigned: "False"
          }),
          unassigned_software: this.tokenService.getTokenCount({
            ...scope,
            infokey: "tokenkind",
            infovalue: "software",
            assigned: "False"
          })
        })
      )
    );
    if (!this.canListUsers()) {
      this.usersRef.set(null);
      return;
    }
    this.usersRef.set(
      // A failure here only costs the "without tokens" row, not the whole widget.
      this.store.load(this.usersStoreKey(realm), () =>
        this.userService.fetchUserCount(realm).pipe(catchError(() => of(null)))
      )
    );
  }
}
