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
import { Audit, AuditData, AuditService, AuditServiceInterface } from "@services/audit/audit.service";
import { AuthService, AuthServiceInterface } from "@services/auth/auth.service";
import { DashboardDataRef, DashboardDataStore } from "@services/dashboard/dashboard-data-store.service";
import { forkJoin } from "rxjs";

export interface FailedUser {
  user: string;
  realm: string;
  fails: number;
  latestError: string;
}

export interface AuthenticationCounts {
  success: number;
  fail: number;
  users: FailedUser[];
  serials: string[];
}

interface AuthenticationResponses {
  success: PiResponse<Audit>;
  fail: PiResponse<Audit>;
}

@Component({
  selector: "app-authentications-widget",
  standalone: true,
  imports: [RouterLink, WidgetStateComponent],
  templateUrl: "./authentications-widget.component.html",
  styleUrl: "./authentications-widget.component.scss"
})
export class AuthenticationsWidgetComponent extends DashboardWidget implements OnInit {
  static override readonly type = "authentications";
  static override readonly title = $localize`Authentications`;
  static override readonly icon = "receipt_long";
  static override readonly defaultSize: WidgetSize = { cols: 8, rows: 6 };
  static override readonly minSize: WidgetSize = { cols: 5, rows: 5 };
  static override readonly maxSize: WidgetSize = { cols: 10, rows: 8 };

  private readonly auditService: AuditServiceInterface = inject(AuditService);
  private readonly authService: AuthServiceInterface = inject(AuthService);
  private readonly store = inject(DashboardDataStore);

  private readonly dataRef = signal<DashboardDataRef<AuthenticationResponses> | null>(null);

  readonly counts = computed<AuthenticationCounts>(() => {
    const results = this.dataRef()?.value();
    const failData = results?.fail.result?.value?.auditdata ?? [];
    return {
      success: results?.success.result?.value?.count ?? 0,
      fail: results?.fail.result?.value?.count ?? 0,
      users: this.aggregateUsers(failData),
      serials: this.collectSerials(failData)
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
    if (!this.authService.actionAllowed("auditlog")) {
      this.state.set("denied");
      return;
    }
    const baseParams = { timelimit: "1d", action: "*validate*" };
    this.dataRef.set(
      this.store.load("dashboard:authentications", () =>
        forkJoin({
          success: this.auditService.fetchAuditPage({ ...baseParams, success: "1" }),
          fail: this.auditService.fetchAuditPage({ ...baseParams, success: "0" })
        })
      )
    );
  }

  private aggregateUsers(auditdata: AuditData[]): FailedUser[] {
    const dict: Record<string, FailedUser> = {};
    for (const entry of auditdata) {
      if (entry.user) {
        const key = entry.user + "-" + entry.realm;
        if (!dict[key]) {
          dict[key] = { user: entry.user, realm: entry.realm ?? "", fails: 1, latestError: entry.date ?? "" };
        } else {
          dict[key].fails++;
          if ((entry.date ?? "") > dict[key].latestError) {
            dict[key].latestError = entry.date ?? "";
          }
        }
      }
    }
    return Object.values(dict).sort((a, b) =>
      b.latestError > a.latestError ? 1 : b.latestError < a.latestError ? -1 : 0
    );
  }

  private collectSerials(auditdata: AuditData[]): string[] {
    const serials: string[] = [];
    for (const entry of auditdata) {
      if (!entry.user && entry.serial) {
        serials.push(entry.serial);
      }
    }
    return serials;
  }
}
