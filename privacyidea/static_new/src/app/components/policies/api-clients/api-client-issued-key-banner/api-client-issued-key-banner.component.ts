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
import { Component, inject } from "@angular/core";
import { MatButtonModule } from "@angular/material/button";
import { MatIconModule } from "@angular/material/icon";
import { CopyButtonComponent } from "@components/shared/copy-button/copy-button.component";
import { ApiClientService, ApiClientServiceInterface } from "@services/api-client/api-client.service";

/**
 * The plaintext API key banner shown once right after an API client is created or its key
 * rotated (from the client list or its details page - `lastIssuedKey` is service-level
 * state, not page-tied, so this reads correctly wherever it is placed).
 */
@Component({
  selector: "app-api-client-issued-key-banner",
  standalone: true,
  imports: [MatButtonModule, MatIconModule, CopyButtonComponent],
  templateUrl: "./api-client-issued-key-banner.component.html",
  styleUrl: "./api-client-issued-key-banner.component.scss"
})
export class ApiClientIssuedKeyBannerComponent {
  protected readonly apiClientService: ApiClientServiceInterface = inject(ApiClientService);
}
