/**
 * (c) NetKnights GmbH 2025,  https://netknights.it
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
import { Component, Input, signal } from "@angular/core";
import { CdkCopyToClipboard } from "@angular/cdk/clipboard";
import { MatIcon } from "@angular/material/icon";

@Component({
  selector: "app-copy-button",
  standalone: true,
  imports: [CdkCopyToClipboard, MatIcon],
  templateUrl: "./copy-button.component.html",
  styleUrls: ["./copy-button.component.scss"]
})
export class CopyButtonComponent {
  @Input() copyText: string = "";
  copied = signal(false);

  onCopy(): void {
    this.copied.set(true);
    setTimeout(() => this.copied.set(false), 1600);
  }
}
