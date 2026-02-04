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
import { effect, inject, Injectable, signal } from "@angular/core";
import { MatDialog } from "@angular/material/dialog";
import { AuthService, AuthServiceInterface } from "../auth/auth.service";
import { WelcomeDialogComponent } from "../../components/shared/welcome-dialog/welcome-dialog.component";

@Injectable({ providedIn: "root" })
export class WelcomeDialogService {
  private readonly dialog = inject(MatDialog);
  private readonly auth: AuthServiceInterface = inject(AuthService);
  private readonly opened = signal<boolean>(false);

  constructor() {
    effect(() => {
      const isAuth = this.auth.isAuthenticated();
      const hideWelcome = this.auth.hideWelcome();

      if (isAuth && !hideWelcome && !this.opened()) {
        this.opened.set(true);
        this.dialog.open(WelcomeDialogComponent, {
          disableClose: true,
          autoFocus: false,
          width: "720px"
        });
      }
    });
  }
}
