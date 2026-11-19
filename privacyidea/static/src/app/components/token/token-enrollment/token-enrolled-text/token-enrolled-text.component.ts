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

import { Component, computed, inject, input, output } from "@angular/core";
import { MatIconModule } from "@angular/material/icon";
import { ROUTE_PATHS } from "@app/route_paths";
import { AuthService, AuthServiceInterface } from "@services/auth/auth.service";
import { ContentService, ContentServiceInterface } from "@services/content/content.service";
import { Observable, of } from "rxjs";

@Component({
  selector: "app-token-enrolled-text",
  imports: [MatIconModule],
  templateUrl: "./token-enrolled-text.component.html",
  styleUrl: "./token-enrolled-text.component.scss"
})
export class TokenEnrolledTextComponent {
  protected readonly contentService: ContentServiceInterface = inject(ContentService);
  protected readonly authService: AuthServiceInterface = inject(AuthService);

  serial = input<string>();
  containerSerial = input<string>();
  username = input<string>();
  userRealm = input<string>();
  onlyAddToRealm = input<boolean>();
  rollover = input<boolean>(false);
  // Asked before a link closes the surrounding dialog; the link is only followed on true.
  confirmLeave = input<() => Observable<boolean>>();
  // Set while the user still has to act, e.g. verify the enrollment, before the token can be used.
  pending = input<boolean>(false);
  // Only the summary sentence, without the cards.
  summaryOnly = input<boolean>(false);
  switchRoute = output();

  // In self-service, the user would only see their own name.
  private readonly isAdmin = computed(() => this.authService.role() === "admin");
  protected readonly showUser = computed(
    () => this.isAdmin() && !!this.username() && !!this.userRealm() && !this.onlyAddToRealm()
  );
  protected readonly showRealmOnly = computed(() => this.isAdmin() && !!this.userRealm() && !!this.onlyAddToRealm());

  tokenSelected() {
    const serial = this.serial();
    if (!serial) {
      return;
    }
    this.leave(() => this.contentService.tokenSelected(serial));
  }

  natigateContainerDetails() {
    const containerSerial = this.containerSerial();
    if (!containerSerial) {
      return;
    }
    this.leave(() => this.contentService.navigateContainerDetails(containerSerial));
  }

  navigateUserDetails() {
    const username = this.username();
    const userRealm = this.userRealm();
    if (!username || !userRealm) {
      return;
    }
    this.leave(() => this.contentService.userSelected(username, userRealm));
  }

  navigateRealms() {
    this.leave(() => this.contentService.router.navigateByUrl(ROUTE_PATHS.USERS_REALMS));
  }

  private leave(navigate: () => void): void {
    const confirmLeave = this.confirmLeave();
    (confirmLeave ? confirmLeave() : of(true)).subscribe((confirmed) => {
      if (confirmed) {
        this.switchRoute.emit();
        navigate();
      }
    });
  }
}
