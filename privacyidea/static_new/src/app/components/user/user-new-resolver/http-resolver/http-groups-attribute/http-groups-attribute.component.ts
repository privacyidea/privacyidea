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

import { Component, Input, OnChanges, OnDestroy, OnInit, SimpleChanges } from "@angular/core";
import { FormGroup, FormsModule, ReactiveFormsModule } from "@angular/forms";
import { Subscription } from "rxjs";
import { MatInput, MatLabel } from "@angular/material/input";
import { MatSlideToggle } from "@angular/material/slide-toggle";
import { MatOption, MatSelect } from "@angular/material/select";
import { MatFormField, MatHint } from "@angular/material/form-field";

@Component({
  selector: "app-http-groups-attribute",
  imports: [
    FormsModule,
    MatFormField,
    MatHint,
    MatInput,
    MatLabel,
    MatOption,
    MatSelect,
    MatSlideToggle,
    ReactiveFormsModule
  ],
  templateUrl: "./http-groups-attribute.component.html",
  styleUrl: "./http-groups-attribute.component.scss"
})
export class HttpGroupsAttributeComponent implements OnInit, OnDestroy {
  @Input({ required: true }) userGroupsControl!: FormGroup;
  @Input({ required: true }) resolverType!: string;

  private activeSub?: Subscription;

  ngOnInit() {
    if (this.userGroupsControl) {
      this.activeSub?.unsubscribe();
      const activeControl = this.userGroupsControl.get("active");
      if (activeControl) {
        // Subscribe to changes in the "active" control to enable/disable other controls
        this.activeSub = activeControl.valueChanges.subscribe((active: boolean) => {
          const controls = ["user_groups_attribute", "method", "endpoint"];
          controls.forEach(ctrl => {
            const control = this.userGroupsControl.get(ctrl);
            if (active) {
              control?.enable({ emitEvent: false });
            } else {
              control?.disable({ emitEvent: false });
            }
          });
        });
        // Initial state
        const controls = ["user_groups_attribute", "method", "endpoint"];
        controls.forEach(ctrl => {
          const control = this.userGroupsControl.get(ctrl);
          if (activeControl.value) {
            control?.enable({ emitEvent: false });
          } else {
            control?.disable({ emitEvent: false });
          }
        });
        // convert method to be lowercase
        const methodControl = this.userGroupsControl.get("method");
        if (methodControl) {
          methodControl.valueChanges.subscribe(value => {
            if (value) {
              methodControl.setValue(value.toLowerCase(), { emitEvent: false });
            }
          });
        }
      }
    }
  }

  ngOnDestroy() {
    this.activeSub?.unsubscribe();
  }
}
