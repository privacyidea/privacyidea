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
import { NgClass } from "@angular/common";
import { Component, input, model } from "@angular/core";
import { MatFormFieldModule } from "@angular/material/form-field";
import { MatInput } from "@angular/material/input";
import { MatListItem } from "@angular/material/list";

@Component({
  selector: "app-details-list-display",
  standalone: true,
  imports: [NgClass, MatListItem],
  template: `
    <div [ngClass]="{ 'details-scrollable-container': true, 'height-77': items().length > 2 }">
      @for (item of items(); track item) {
        <mat-list-item class="height-auto pad-0">
          <span class="font-14">• {{ item }}</span>
        </mat-list-item>
      }
    </div>
  `
})
export class DetailsListDisplayComponent {
  items = input.required<string[]>();
}

@Component({
  selector: "app-details-description-cell",
  standalone: true,
  imports: [MatFormFieldModule, MatInput],
  template: `
    @if (isEditing()) {
      <mat-form-field
        class="input-width-m description height-126"
        subscriptSizing="dynamic">
        <textarea
          [value]="value()"
          (input)="value.set($any($event.target).value)"
          [attr.maxlength]="maxlength()"
          i18n-placeholder
          matInput
          placeholder="Enter description"
          [rows]="rows()"></textarea>
      </mat-form-field>
    } @else {
      <div class="details-description-div">
        <span class="details-table-item">
          {{ value() }}
        </span>
      </div>
    }
  `
})
export class DetailsDescriptionCellComponent {
  value = model.required<string>();
  isEditing = input(false);
  maxlength = input(80);
  rows = input(4);
}

@Component({
  selector: "app-details-default-value-cell",
  standalone: true,
  imports: [MatFormFieldModule, MatInput, NgClass],
  template: `
    @if (isEditing() && isNumber()) {
      <mat-form-field
        class="input-width-m height-52"
        subscriptSizing="dynamic">
        <input
          [value]="value()"
          (input)="value.set($any($event.target).value)"
          matInput
          type="number" />
      </mat-form-field>
    } @else if (isEditing()) {
      <mat-form-field
        class="input-width-m"
        subscriptSizing="dynamic">
        <textarea
          [value]="value()"
          (input)="value.set($any($event.target).value)"
          matInput
          rows="1"></textarea>
      </mat-form-field>
    } @else {
      <div [ngClass]="[divClass()]">
        <span [ngClass]="[spanClass()]">
          {{ displayText() }}
        </span>
      </div>
    }
  `
})
export class DetailsDefaultValueCellComponent {
  value = model.required<string>();
  isEditing = input(false);
  isNumber = input(false);
  divClass = input("");
  spanClass = input("");
  displayText = input("");
}
