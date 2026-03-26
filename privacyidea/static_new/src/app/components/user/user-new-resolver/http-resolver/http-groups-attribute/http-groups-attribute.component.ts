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

import { Component, computed, Input, OnDestroy, OnInit, signal } from "@angular/core";
import { FormGroup, FormsModule, ReactiveFormsModule } from "@angular/forms";
import { Subscription } from "rxjs";
import { MatInput, MatLabel } from "@angular/material/input";
import { MatSlideToggle } from "@angular/material/slide-toggle";
import { MatOption, MatSelect } from "@angular/material/select";
import { MatFormField, MatHint } from "@angular/material/form-field";
import { MatTooltip } from "@angular/material/tooltip";

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
    ReactiveFormsModule,
    MatTooltip
  ],
  templateUrl: "./http-groups-attribute.component.html",
  styleUrl: "./http-groups-attribute.component.scss"
})
export class HttpGroupsAttributeComponent implements OnInit, OnDestroy {
  // Signal for the 'active' value
  readonly activeSignal = signal<boolean>(false);
  // Computed signal for the tooltip
  readonly slideToggleTooltipSignal = computed(() =>
    this.activeSignal() ? $localize`Disable user groups retrieval` : $localize`Enable user groups retrieval`
  );
  private activeSubscription?: Subscription;
  private methodSubscription?: Subscription;
  @Input({ required: true }) userGroupsControl!: FormGroup;
  @Input({ required: true }) resolverType!: string;

  ngOnInit() {
    if (this.userGroupsControl) {
      this.activeSubscription?.unsubscribe();
      const activeControl = this.userGroupsControl.get("active");
      if (activeControl) {
        const controls = ["pi_user_groups_key", "user_groups_attribute", "method", "endpoint"];

        const updateControls = (active: boolean) => {
          this.activeSignal.set(active);
          controls.forEach((ctrl) => {
            const control = this.userGroupsControl.get(ctrl);
            if (active) {
              control?.enable({ emitEvent: false });
            } else {
              control?.disable({ emitEvent: false });
            }
          });
        };

        this.activeSubscription = activeControl.valueChanges.subscribe(updateControls);
        updateControls(!!activeControl.value);

        const methodControl = this.userGroupsControl.get("method");
        if (methodControl) {
          this.methodSubscription?.unsubscribe();
          this.methodSubscription = methodControl.valueChanges.subscribe((value) => {
            if (value) {
              methodControl.setValue(value.toUpperCase(), { emitEvent: false });
            }
          });
        }
      }
    }
  }

  ngOnDestroy() {
    this.activeSubscription?.unsubscribe();
    this.methodSubscription?.unsubscribe();
  }
}
