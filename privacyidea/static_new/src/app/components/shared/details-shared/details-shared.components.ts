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
import { Component, Input } from "@angular/core";
import { FormsModule } from "@angular/forms";
import { MatFormFieldModule } from "@angular/material/form-field";
import { MatInput } from "@angular/material/input";
import { MatListItem } from "@angular/material/list";
import { NgClass } from "@angular/common";

@Component({
  selector: "app-details-list-display",
  standalone: true,
  imports: [NgClass, MatListItem],
  template: `
    <div
      [ngClass]="{ 'details-scrollable-container': true, 'height-77': items.length > 2 }">
      @for (item of items; track item) {
        <mat-list-item class="height-auto pad-0">
          <span class="font-14">• {{ item }}</span>
        </mat-list-item>
      }
    </div>
  `
})
export class DetailsListDisplayComponent {
  @Input({ required: true }) items: string[] = [];
}

@Component({
  selector: "app-details-description-cell",
  standalone: true,
  imports: [FormsModule, MatFormFieldModule, MatInput],
  template: `
    @if (isEditing) {
      <mat-form-field
        class="input-width-m description height-126" subscriptSizing="dynamic">
        <textarea
          [(ngModel)]="value"
          [maxlength]="maxlength"
          i18n-placeholder
          matInput
          placeholder="Enter description"
          [rows]="rows"></textarea>
      </mat-form-field>
    } @else {
      <div class="details-description-div">
        <span class="details-table-item">
          {{ value }}
        </span>
      </div>
    }
  `
})
export class DetailsDescriptionCellComponent {
  @Input({ required: true }) value: any;
  @Input() isEditing = false;
  @Input() maxlength = 80;
  @Input() rows = 4;
}

@Component({
  selector: "app-details-default-value-cell",
  standalone: true,
  imports: [FormsModule, MatFormFieldModule, MatInput, NgClass],
  template: `
    @if (isEditing && isNumber) {
      <mat-form-field
        class="input-width-m height-52" subscriptSizing="dynamic">
        <input
          [(ngModel)]="value" matInput type="number" />
      </mat-form-field>
    } @else if (isEditing) {
      <mat-form-field
        class="input-width-m" subscriptSizing="dynamic">
        <textarea
          [(ngModel)]="value" matInput rows="1"></textarea>
      </mat-form-field>
    } @else {
      <div [ngClass]="[divClass]">
        <span [ngClass]="[spanClass]">
          {{ displayText }}
        </span>
      </div>
    }
  `
})
export class DetailsDefaultValueCellComponent {
  @Input({ required: true }) value: any;
  @Input() isEditing = false;
  @Input() isNumber = false;
  @Input() divClass = "";
  @Input() spanClass = "";
  @Input() displayText = "";
}

