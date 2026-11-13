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

import { Component, input } from "@angular/core";
import { ContainerTokenNotCreated } from "@services/container/container.service";

/** Lists the template tokens POST /container/init did not create, as "<type> (<error>)" in a red callout. */
@Component({
  selector: "app-tokens-not-created-callout",
  templateUrl: "./tokens-not-created-callout.component.html",
  styleUrl: "./tokens-not-created-callout.component.scss"
})
export class TokensNotCreatedCalloutComponent {
  /** The tokens that were not created. Renders nothing when undefined or empty. */
  readonly tokensNotCreated = input<ContainerTokenNotCreated[] | undefined>([]);
  /** True when the template created no token at all, which swaps the heading for the "none created" error. */
  readonly allFailed = input(false);
}
