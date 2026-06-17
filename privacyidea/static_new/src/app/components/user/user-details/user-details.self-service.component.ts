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
import { BreakpointObserver } from "@angular/cdk/layout";
import { Component, computed, inject, signal, Signal } from "@angular/core";
import { toSignal } from "@angular/core/rxjs-interop";
import { MatIcon } from "@angular/material/icon";
import { ScrollToTopDirective } from "@components/shared/directives/app-scroll-to-top.directive";
import { UserService, UserServiceInterface } from "@services/user/user.service";
import { map } from "rxjs";

@Component({
  selector: "app-user-details-self-service",
  standalone: true,
  imports: [ScrollToTopDirective, MatIcon],
  templateUrl: "./user-details.self-service.component.html",
  styleUrl: "./user-details.component.scss"
})
export class UserDetailsSelfServiceComponent {
  protected readonly userService: UserServiceInterface = inject(UserService);
  private breakpointObserver = inject(BreakpointObserver);

  expandedKeys = signal<Set<string>>(new Set<string>());

  isExpanded(key: string): boolean {
    return this.expandedKeys().has(key);
  }

  toggleExpanded(key: string): void {
    const next = new Set(this.expandedKeys());
    if (next.has(key)) {
      next.delete(key);
    } else {
      next.add(key);
    }
    this.expandedKeys.set(next);
  }

  private isSmall = toSignal(this.breakpointObserver.observe("(max-width: 1000px)").pipe(map((r) => r.matches)));
  private isMedium = toSignal(this.breakpointObserver.observe("(max-width: 1240px)").pipe(map((r) => r.matches)));

  colCount = computed(() => {
    if (this.isSmall()) return 1;
    if (this.isMedium()) return 2;
    return 3;
  });

  readonly labels: Record<string, string> = {
    username: $localize`Username`,
    givenname: $localize`Given name`,
    surname: $localize`Surname`,
    email: $localize`Email`,
    phone: $localize`Phone`,
    mobile: $localize`Mobile`,
    description: $localize`Description`,
    userid: $localize`User ID`,
    resolver: $localize`Resolver`
  };

  readonly excludedKeys = new Set<string>(["editable"]);
  readonly detailOrder: string[] = [
    "username",
    "givenname",
    "surname",
    "description",
    "email",
    "phone",
    "mobile",
    "userid",
    "resolver"
  ];

  userData = this.userService.user;

  detailsEntries = computed(() => {
    const data: Record<string, unknown> = this.userData() ?? {};
    const result: { key: string; label: string; value: unknown }[] = [];

    for (const key of this.detailOrder) {
      if (!(key in data)) continue;
      if (this.excludedKeys.has(key)) continue;
      result.push({
        key,
        label: this.labels[key] ?? key,
        value: this.normalizeValue(data[key])
      });
    }

    for (const [key, raw] of Object.entries(data)) {
      if (this.excludedKeys.has(key)) continue;
      if (this.detailOrder.includes(key)) continue;
      result.push({
        key,
        label: this.labels[key] ?? key,
        value: this.normalizeValue(raw)
      });
    }

    return result;
  });

  detailsColumns: Signal<{ key: string; label: string; value: unknown }[][]> = computed(() => {
    const entries = this.detailsEntries();
    const colCount = this.colCount();
    const perCol = Math.ceil(entries.length / colCount);
    return Array.from({ length: colCount }, (_, i) => entries.slice(i * perCol, (i + 1) * perCol));
  });

  protected readonly Array = Array;

  private normalizeValue(value: unknown): unknown {
    if (value === null || value === undefined) return "-";
    if (typeof value === "string" && value.trim() === "") return "-";
    return value;
  }
}
