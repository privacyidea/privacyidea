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
import { Component, computed, input } from "@angular/core";
import { MatIconButton } from "@angular/material/button";
import { MatIcon } from "@angular/material/icon";
import { MatTooltip } from "@angular/material/tooltip";

@Component({
  selector: "app-filter-hint",
  templateUrl: "./filter-hint.component.html",
  imports: [MatIcon, MatIconButton, MatTooltip],
  styleUrls: ["./filter-hint.component.scss"]
})
export class FilterHintComponent {
  readonly example = input<string>();
  readonly keywords = input<string[]>([]);
  readonly supportsKeywords = input<boolean>(true);
  readonly caseSensitive = input<boolean>(false);

  readonly hintText = computed(() => {
    const lines: string[] = [];
    if (this.supportsKeywords()) {
      lines.push($localize`Enter one or more "keyword: value" pairs, separated by spaces.`);
      lines.push($localize`Wrap values containing spaces in quotes, e.g. description: "my token".`);
    }
    lines.push($localize`Use "*" as a wildcard.`);
    lines.push(
      this.caseSensitive()
        ? $localize`Matching is case-sensitive.`
        : $localize`Matching is usually case-insensitive.`
    );

    const example = this.example();
    if (example) {
      lines.push($localize`Example: ${example}`);
    }

    const keywords = this.keywords();
    if (keywords.length > 0) {
      lines.push($localize`Available keywords: ${keywords.join(", ")}`);
    }

    return lines.join("\n");
  });
}
