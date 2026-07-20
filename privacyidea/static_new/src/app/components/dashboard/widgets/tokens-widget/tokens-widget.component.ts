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
import { RouterLink } from "@angular/router";
import { PiResponse } from "@app/app.component";
import { ROUTE_PATHS } from "@app/route_paths";
import { TokensWidgetIconComponent } from "@components/dashboard/widgets/tokens-widget/tokens-widget-icon.component";
import { WidgetStateComponent } from "@components/dashboard/widgets/widget-state/widget-state.component";
import { FilterValue } from "@core/models/filter_value/filter_value";
import { DashboardWidget, WidgetSize } from "@models/dashboard";
import { AuthService, AuthServiceInterface } from "@services/auth/auth.service";
import { DashboardDataRef, DashboardDataStore } from "@services/dashboard/dashboard-data-store.service";
import { TokenCount, TokenService, TokenServiceInterface } from "@services/token/token.service";
import { forkJoin } from "rxjs";

export interface TokenCounts {
  total: number;
  hardware: number;
  software: number;
  unassigned_hardware: number;
  unassigned_software: number;
}

interface TokenCountResponses {
  total: PiResponse<TokenCount>;
  hardware: PiResponse<TokenCount>;
  software: PiResponse<TokenCount>;
  unassigned_hardware: PiResponse<TokenCount>;
  unassigned_software: PiResponse<TokenCount>;
}

@Component({
  selector: "app-tokens-widget",
  standalone: true,
  imports: [RouterLink, WidgetStateComponent],
  templateUrl: "./tokens-widget.component.html",
  styleUrl: "./tokens-widget.component.scss"
})
export class TokensWidgetComponent extends DashboardWidget implements OnInit {
  static override readonly type = "tokens";
  static override readonly requiredAction = "tokenlist";
  static override readonly title = $localize`Token Usage`;
  static override readonly icon = "shield";
  static override readonly headerIcon = TokensWidgetIconComponent;
  static override readonly defaultSize: WidgetSize = { cols: 6, rows: 5 };
  static override readonly minSize: WidgetSize = { cols: 4, rows: 2 };
  static override readonly maxSize: WidgetSize = { cols: 12, rows: 9 };

  protected readonly routePaths = ROUTE_PATHS;

  private readonly tokenService: TokenServiceInterface = inject(TokenService);
  private readonly authService: AuthServiceInterface = inject(AuthService);
  private readonly store = inject(DashboardDataStore);

  private readonly dataRef = signal<DashboardDataRef<TokenCountResponses> | null>(null);
  override readonly partialLoading = computed(() => this.dataRef()?.revalidating() ?? false);

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

  constructor() {
    super();
    effect(() => {
      const ref = this.dataRef();
      if (!ref) {
        return;
      }
      const value = ref.value();
      if (value !== undefined) {
        this.state.set(Object.values(value).every((response) => response.result?.status === true) ? "ready" : "error");
      } else if (ref.error()) {
        this.state.set("error");
      } else {
        this.state.set("loading");
      }
    });
  }

  showAllTokens(): void {
    this.tokenService.presetFilter.set(new FilterValue());
  }

  showKind(kind: "hardware" | "software", unassignedOnly = false): void {
    let filter = new FilterValue().addEntry("infokey", "tokenkind").addEntry("infovalue", kind);
    if (unassignedOnly) {
      filter = filter.addEntry("assigned", "False");
    }
    this.tokenService.presetFilter.set(filter);
  }

  showUnassigned(): void {
    this.tokenService.presetFilter.set(new FilterValue().addEntry("assigned", "False"));
  }

  ngOnInit(): void {
    this.load();
  }

  override reload(): void {
    this.store.invalidate("dashboard:tokens");
    this.load();
  }

  private load(): void {
    if (!this.authService.actionAllowed("tokenlist")) {
      this.state.set("denied");
      return;
    }
    this.dataRef.set(
      this.store.load("dashboard:tokens", () =>
        forkJoin({
          total: this.tokenService.getTokenCount(),
          hardware: this.tokenService.getTokenCount({ infokey: "tokenkind", infovalue: "hardware" }),
          software: this.tokenService.getTokenCount({ infokey: "tokenkind", infovalue: "software" }),
          unassigned_hardware: this.tokenService.getTokenCount({
            infokey: "tokenkind",
            infovalue: "hardware",
            assigned: "False"
          }),
          unassigned_software: this.tokenService.getTokenCount({
            infokey: "tokenkind",
            infovalue: "software",
            assigned: "False"
          })
        })
      )
    );
  }
}
