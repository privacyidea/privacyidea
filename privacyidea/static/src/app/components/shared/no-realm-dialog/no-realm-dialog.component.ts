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
import { Component, computed, inject } from "@angular/core";
import { Router } from "@angular/router";
import { AbstractDialogComponent } from "@components/shared/dialog/abstract-dialog/abstract-dialog.component";
import { DialogWrapperComponent } from "@components/shared/dialog/dialog-wrapper/dialog-wrapper.component";
import { DialogAction } from "@models/dialog";
import { ROUTE_PATHS } from "@app/route_paths";

type NoRealmAction = "create" | "later";

export interface NoRealmDialogData {
  noResolver: boolean;
}

/** Points an administrator to the realm management while no realm exists. Creates nothing itself. */
@Component({
  selector: "app-no-realm-dialog",
  standalone: true,
  imports: [DialogWrapperComponent],
  templateUrl: "./no-realm-dialog.component.html",
  styleUrl: "./no-realm-dialog.component.scss"
})
export class NoRealmDialogComponent extends AbstractDialogComponent<NoRealmDialogData | null, void> {
  private readonly router = inject(Router);

  /** True if no resolver exists either: a resolver has to be created before a realm. */
  readonly noResolver = this.data?.noResolver ?? false;

  readonly dialogTitle = this.noResolver
    ? $localize`:@@noRealmDialog.noResolver.title:No resolver and no realm exist yet`
    : $localize`:@@noRealmDialog.title:No realm exists yet`;

  readonly dialogActions = computed((): DialogAction<NoRealmAction>[] => [
    { type: "cancel", label: $localize`:@@noRealmDialog.later:Later`, value: "later" },
    {
      type: "confirm",
      label: this.noResolver
        ? $localize`:@@noRealmDialog.createResolver:Create resolver`
        : $localize`:@@dashboard.createRealm:Create realm`,
      value: "create",
      primary: true
    }
  ]);

  onDialogAction(action: NoRealmAction): void {
    if (action === "create") {
      void this.router.navigateByUrl(this.noResolver ? ROUTE_PATHS.USERS_RESOLVERS_NEW : ROUTE_PATHS.USERS_REALMS);
    }
    this.close();
  }
}
