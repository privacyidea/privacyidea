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
import { Component, effect, inject } from "@angular/core";
import { FormControl, FormsModule } from "@angular/forms";
import { MatFormField, MatLabel } from "@angular/material/form-field";
import { MatInput } from "@angular/material/input";
import { MatSelect, MatSelectModule } from "@angular/material/select";
import { MatOption } from "@angular/material/core";
import { MatButtonModule } from "@angular/material/button";
import { MatIconModule } from "@angular/material/icon";
import { MatCardModule } from "@angular/material/card";
import { HttpErrorResponse } from "@angular/common/http";

import { Resolver, ResolverService, ResolverType } from "../../../services/resolver/resolver.service";
import { NotificationService } from "../../../services/notification/notification.service";
import { PasswdResolverComponent } from "./passwd-resolver/passwd-resolver.component";
import { ScrollToTopDirective } from "../../shared/directives/app-scroll-to-top.directive";
import { LdapResolverComponent } from "./ldap-resolver/ldap-resolver.component";
import { SqlResolverComponent } from "./sql-resolver/sql-resolver.component";
import { ScimResolverComponent } from "./scim-resolver/scim-resolver.component";

@Component({
  selector: "app-user-new-resolver",
  standalone: true,
  imports: [
    FormsModule,
    MatFormField,
    MatLabel,
    MatInput,
    MatSelectModule,
    MatSelect,
    MatOption,
    MatButtonModule,
    MatIconModule,
    MatCardModule,
    PasswdResolverComponent,
    ScrollToTopDirective,
    LdapResolverComponent,
    SqlResolverComponent,
    ScimResolverComponent
  ],
  templateUrl: "./user-new-resolver.component.html",
  styleUrl: "./user-new-resolver.component.scss"
})
export class UserNewResolverComponent {
  private readonly resolverService = inject(ResolverService);
  private readonly notificationService = inject(NotificationService);
  private editInitialized = false;
  additionalFormFields: { [key: string]: FormControl<any> } = {};
  resolverName = "";
  resolverType: ResolverType | "" = "";
  formData: Record<string, any> = {};
  isSaving = false;
  isTesting = false;

  constructor() {
    effect(() => {
      const selectedName = this.resolverService.selectedResolverName();
      const resource = (this.resolverService as any).selectedResolverResource?.value?.();

      if (!selectedName || !resource?.result?.value) {
        console.log("No resolver selected.");
        console.log("name"+selectedName)
        console.log("resource"+resource)
        return;
      }

      if (this.editInitialized) {
        console.log("Edit already initialized.");
        return;
      }

      const resolver = resource.result.value as Resolver;
      console.log("Edit initialized with resolver:", resolver);
      this.resolverName = resolver.resolvername;
      this.resolverType = resolver.type;
      this.formData = { ...(resolver.data || {}) };
      this.editInitialized = true;
    });
  }

  get isEditMode(): boolean {
    return !!this.resolverService.selectedResolverName();
  }

  onSave(): void {
    const name = this.resolverName.trim();
    if (!name) {
      this.notificationService.openSnackBar($localize`Please enter a resolver name.`);
      return;
    }
    if (!this.resolverType) {
      this.notificationService.openSnackBar($localize`Please select a resolver type.`);
      return;
    }

    const payload: any = {
      type: this.resolverType,
      ...this.formData
    };

    for (const [key, control] of Object.entries(this.additionalFormFields)) {
      if (!control) continue;
      payload[key] = control.value;
    }

    this.isSaving = true;

    this.resolverService
      .postResolver(name, payload)
      .subscribe({
        next: () => {
          this.notificationService.openSnackBar(
            this.isEditMode
              ? $localize`Resolver "${name}" updated.`
              : $localize`Resolver "${name}" created.`
          );
          this.resolverService.resolversResource.reload?.();

          if (!this.isEditMode) {
            this.resolverName = "";
            this.resolverType = "";
            this.formData = {};
            this.additionalFormFields = {};
          }
        },
        error: (err: HttpErrorResponse) => {
          const message = err.error?.result?.error?.message || err.message;
          this.notificationService.openSnackBar(
            $localize`Failed to save resolver. ${message}`
          );
        }
      })
      .add(() => (this.isSaving = false));
  }

  onTest(): void {
    this.isTesting = true;

    this.resolverService
      .postResolverTest()
      .subscribe({
        next: () => {
          this.notificationService.openSnackBar(
            $localize`Resolver test executed. Check server response.`
          );
        },
        error: (err: HttpErrorResponse) => {
          const message = err.error?.result?.error?.message || err.message;
          this.notificationService.openSnackBar(
            $localize`Failed to test resolver. ${message}`
          );
        }
      })
      .add(() => (this.isTesting = false));
  }

  updateAdditionalFormFields(event: { [key: string]: FormControl<any> | undefined | null }): void {
    const validControls: { [key: string]: FormControl<any> } = {};
    for (const key in event) {
      if (event.hasOwnProperty(key) && event[key] instanceof FormControl) {
        validControls[key] = event[key] as FormControl<any>;
      }
    }
    this.additionalFormFields = validControls;
  }
}
