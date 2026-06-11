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
import { WidgetStateComponent } from "@components/dashboard/widgets/widget-state/widget-state.component";
import { DashboardWidget, WidgetSize } from "@models/dashboard";
import { AuthService, AuthServiceInterface } from "@services/auth/auth.service";
import { DashboardDataRef, DashboardDataStore } from "@services/dashboard/dashboard-data-store.service";
import { Tokens, TokenService, TokenServiceInterface } from "@services/token/token.service";
import { forkJoin } from "rxjs";

export interface TokenCounts {
  total: number;
  hardware: number;
  software: number;
  unassigned_hardware: number;
  unassigned_software: number;
}

interface TokenCountResponses {
  total: PiResponse<Tokens>;
  hardware: PiResponse<Tokens>;
  software: PiResponse<Tokens>;
  unassigned_hardware: PiResponse<Tokens>;
  unassigned_software: PiResponse<Tokens>;
}

@Component({
  selector: "app-tokens-widget",
  standalone: true,
  imports: [RouterLink, WidgetStateComponent],
  templateUrl: "./tokens-widget.component.html",
  styleUrls: ["../dashboard-widget.scss", "./tokens-widget.component.scss"]
})
export class TokensWidgetComponent extends DashboardWidget implements OnInit {
  static override readonly type = "tokens";
  static override readonly title = $localize`Tokens`;
  static override readonly icon = "shield";
  static override readonly defaultSize: WidgetSize = { cols: 6, rows: 8 };
  static override readonly minSize: WidgetSize = { cols: 4, rows: 5 };
  static override readonly maxSize: WidgetSize = { cols: 12, rows: 9 };

  private readonly tokenService: TokenServiceInterface = inject(TokenService);
  private readonly authService: AuthServiceInterface = inject(AuthService);
  private readonly store = inject(DashboardDataStore);

  private readonly dataRef = signal<DashboardDataRef<TokenCountResponses> | null>(null);

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

  constructor() {
    super();
    effect(() => {
      const ref = this.dataRef();
      if (!ref) {
        return;
      }
      if (ref.value() !== undefined) {
        this.state.set("ready");
      } else if (ref.error()) {
        this.state.set("error");
      } else {
        this.state.set("loading");
      }
    });
  }

  ngOnInit(): void {
    if (!this.authService.actionAllowed("tokenlist")) {
      this.state.set("denied");
      return;
    }
    this.dataRef.set(
      this.store.load("dashboard:tokens", () =>
        forkJoin({
          total: this.tokenService.getTokenCount({ pagesize: 0 }),
          hardware: this.tokenService.getTokenCount({ pagesize: 0, infokey: "tokenkind", infovalue: "hardware" }),
          software: this.tokenService.getTokenCount({ pagesize: 0, infokey: "tokenkind", infovalue: "software" }),
          unassigned_hardware: this.tokenService.getTokenCount({
            pagesize: 0,
            infokey: "tokenkind",
            infovalue: "hardware",
            assigned: "False"
          }),
          unassigned_software: this.tokenService.getTokenCount({
            pagesize: 0,
            infokey: "tokenkind",
            infovalue: "software",
            assigned: "False"
          })
        })
      )
    );
  }
}
