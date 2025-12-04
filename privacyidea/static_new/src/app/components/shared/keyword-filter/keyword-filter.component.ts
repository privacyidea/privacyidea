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
import { Component, inject, Input, signal, WritableSignal } from "@angular/core";
import { TableUtilsService, TableUtilsServiceInterface } from "../../../services/table-utils/table-utils.service";
import { FilterValue } from "../../../core/models/filter_value";

@Component({
  selector: "app-keyword-filter",
  standalone: true,
  imports: [],
  templateUrl: "./keyword-filter.component.html",
  styleUrl: "./keyword-filter.component.scss"
})
export class KeywordFilterComponent {
  private readonly tableUtilsService: TableUtilsServiceInterface = inject(TableUtilsService);
  @Input() apiFilter: string[] = [];
  @Input() apiFilterKeyMap: Record<string, string> = {};
  @Input() advancedApiFilter: string[] = [];
  @Input({ required: true }) filterHTMLInputElement!: HTMLInputElement;
  @Input({ required: true }) filterValue!: WritableSignal<FilterValue>;
}
