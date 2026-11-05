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
import { Component, input, model } from "@angular/core";
import { MatFormField, MatLabel, MatSuffix } from "@angular/material/input";
import { MatOption, MatSelect } from "@angular/material/select";
import { ClearButtonComponent } from "@components/shared/clear-button/clear-button.component";

/**
 * A "-" entry in the realmdropdown policy is the privacyIDEA "no realm" sentinel: it is offered as a selectable option
 * but must not be sent as a realm parameter.
 */
export const NO_REALM_SENTINEL = "-";

/** Splits the comma separated `realms` of the config into the entries of the dropdown. */
export function parseRealms(realms: string | undefined): string[] {
  return (realms || "")
    .split(",")
    .map((r) => r.trim())
    .filter((r) => r);
}

/** The realm to send to the server: nothing for an empty selection and for the "no realm" sentinel. */
export function realmParam(realm: string): string | undefined {
  return realm && realm !== NO_REALM_SENTINEL ? realm : undefined;
}

/** The realm dropdown of the login page and the password recovery page. */
@Component({
  selector: "app-realm-select",
  standalone: true,
  imports: [ClearButtonComponent, MatFormField, MatLabel, MatOption, MatSelect, MatSuffix],
  templateUrl: "./realm-select.component.html",
  styleUrl: "./realm-select.component.scss"
})
export class RealmSelectComponent {
  realms = input.required<string[]>();
  realm = model.required<string>();

  clearRealmSelection(event: MouseEvent): void {
    event.stopPropagation();
    this.realm.set("");
  }
}
