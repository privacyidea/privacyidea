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
import { AuthService, AuthServiceInterface } from "../../../services/auth/auth.service";
import { Component, computed, effect, inject, linkedSignal, signal, WritableSignal } from "@angular/core";
import { ContainerService, ContainerServiceInterface } from "../../../services/container/container.service";
import { ContentService, ContentServiceInterface } from "../../../services/content/content.service";
import { EditableElement, EditButtonsComponent } from "../../shared/edit-buttons/edit-buttons.component";
import { FormsModule, ReactiveFormsModule } from "@angular/forms";
import { MatAutocomplete, MatAutocompleteTrigger } from "@angular/material/autocomplete";
import { MatCell, MatColumnDef, MatRow, MatTable, MatTableModule } from "@angular/material/table";
import { OverflowService, OverflowServiceInterface } from "../../../services/overflow/overflow.service";
import { RealmService, RealmServiceInterface } from "../../../services/realm/realm.service";
import { TableUtilsService, TableUtilsServiceInterface } from "../../../services/table-utils/table-utils.service";
import { TokenDetails, TokenService, TokenServiceInterface } from "../../../services/token/token.service";

import { ClearableInputComponent } from "../../shared/clearable-input/clearable-input.component";
import { CopyButtonComponent } from "../../shared/copy-button/copy-button.component";
import { MatDialog } from "@angular/material/dialog";
import { MatFormFieldModule } from "@angular/material/form-field";
import { MatIcon } from "@angular/material/icon";
import { MatIconButton } from "@angular/material/button";
import { MatInput } from "@angular/material/input";
import { MatListItem } from "@angular/material/list";
import { MatSelectModule } from "@angular/material/select";
import { NgClass } from "@angular/common";
import { ROUTE_PATHS } from "../../../route_paths";
import { Router } from "@angular/router";
import { ScrollToTopDirective } from "../../shared/directives/app-scroll-to-top.directive";
import { TokenDetailsActionsComponent } from "./token-details-actions/token-details-actions.component";
import { TokenDetailsInfoComponent } from "./token-details-info/token-details-info.component";
import { TokenDetailsUserComponent } from "./token-details-user/token-details-user.component";
import {
  SshMachineAssignDialogData,
  TokenSshMachineAssignDialogComponent
} from "./token-machine-attach-dialog/token-ssh-machine-attach-dialog/token-ssh-machine-attach-dialog";
import { TokenDetailsMachineComponent } from "./token-details-machine/token-details-machine.component";
import { PolicyAction } from "../../../services/auth/policy-actions";
import { MachineService, MachineServiceInterface, TokenApplications } from "../../../services/machine/machine.service";

export const tokenDetailsKeyMap = [
  { key: "tokentype", label: "Type" },
  { key: "active", label: "Status" },
  { key: "maxfail", label: "Max Count" },
  { key: "failcount", label: "Fail Count" },
  { key: "rollout_state", label: "Rollout State" },
  { key: "otplen", label: "OTP Length" },
  { key: "count_window", label: "Count Window" },
  { key: "sync_window", label: "Sync Window" },
  { key: "count", label: "Count" },
  { key: "description", label: "Description" },
  { key: "realms", label: "Token Realms" },
  { key: "tokengroup", label: "Token Groups" },
  { key: "container_serial", label: "Container Serial" }
];

export const tokenDetailsRightsMap = [
  { key: "maxfail", right: "set" },
  { key: "count_window", right: "set" },
  { key: "sync_window", right: "set" },
  { key: "description", right: "setdescription" },
  { key: "realms", right: "tokenrealms" },
  { key: "tokengroup", right: "tokengroups" },
  { key: "container_serial", right: "container_add_token" }
];

export const userDetailsKeyMap = [
  { key: "user_realm", label: "User Realm" },
  { key: "username", label: "User" },
  { key: "resolver", label: "Resolver" },
  { key: "user_id", label: "User ID" }
];

export const infoDetailsKeyMap = [{ key: "info", label: "Information" }];

@Component({
  imports: [
    MatCell,
    MatTableModule,
    MatColumnDef,
    MatIcon,
    MatListItem,
    MatRow,
    MatTable,
    NgClass,
    FormsModule,
    MatInput,
    MatFormFieldModule,
    MatSelectModule,
    ReactiveFormsModule,
    MatIconButton,
    TokenDetailsUserComponent,
    MatAutocomplete,
    MatAutocompleteTrigger,
    TokenDetailsInfoComponent,
    TokenDetailsActionsComponent,
    EditButtonsComponent,
    CopyButtonComponent,
    ScrollToTopDirective,
    ClearableInputComponent,
    CopyButtonComponent,
    ClearableInputComponent,
    ScrollToTopDirective,
    TokenDetailsMachineComponent
  ],
  templateUrl: "./token-details.component.html",
  styleUrls: ["./token-details.component.scss"]
})
export class TokenDetailsComponent {
  protected readonly matDialog: MatDialog = inject(MatDialog);
  protected readonly tokenService: TokenServiceInterface = inject(TokenService);
  protected readonly containerService: ContainerServiceInterface = inject(ContainerService);
  protected readonly realmService: RealmServiceInterface = inject(RealmService);
  protected readonly overflowService: OverflowServiceInterface = inject(OverflowService);
  protected readonly tableUtilsService: TableUtilsServiceInterface = inject(TableUtilsService);
  protected readonly contentService: ContentServiceInterface = inject(ContentService);
  protected readonly authService: AuthServiceInterface = inject(AuthService);
  protected readonly machineService: MachineServiceInterface = inject(MachineService);
  private router = inject(Router);
  tokenIsActive = this.tokenService.tokenIsActive;
  tokenIsRevoked = this.tokenService.tokenIsRevoked;
  isProgrammaticTabChange = this.contentService.isProgrammaticTabChange;
  containerSerial = this.containerService.containerSerial;
  tokenSerial = this.tokenService.tokenSerial;
  isEditingUser = signal(false);
  isEditingInfo = signal(false);
  setPinValue = signal("");
  repeatPinValue = signal("");

  isAttachedToMachine = computed<boolean>(() => {
    const tokenApplications = this.machineService.tokenApplications();
    if (!tokenApplications) return false;
    if (tokenApplications.length === 0) return false;
    return true;
  });

  tokenDetailResource = this.tokenService.tokenDetailResource;
  tokenDetails: WritableSignal<TokenDetails> = linkedSignal({
    source: this.tokenDetailResource.value,
    computation: (res) => {
      return res && res.result?.value?.tokens[0]
        ? (res.result?.value.tokens[0] as TokenDetails)
        : {
            active: false,
            container_serial: "",
            count: 0,
            count_window: 0,
            description: "",
            failcount: 0,
            id: 0,
            info: {},
            locked: false,
            maxfail: 0,
            otplen: 0,
            realms: [],
            resolver: "",
            revoked: false,
            rollout_state: "",
            serial: "",
            sync_window: 0,
            tokengroup: [],
            tokentype: "hotp",
            user_id: "",
            user_realm: "",
            username: ""
          };
    }
  });
  tokenDetailData = linkedSignal({
    source: this.tokenDetails,
    computation: (details) => {
      if (!details) {
        return tokenDetailsKeyMap.map((detail) => ({
          keyMap: detail,
          value: "",
          isEditing: signal(false)
        }));
      }
      return tokenDetailsKeyMap
        .map((detail) => ({
          keyMap: detail,
          value: details[detail.key as keyof TokenDetails],
          isEditing: signal(false)
        }))
        .filter((detail) => detail.value !== undefined);
    }
  });
  infoData = linkedSignal({
    source: this.tokenDetails,
    computation: (details) => {
      if (!details) {
        return infoDetailsKeyMap.map((detail) => ({
          keyMap: detail,
          value: "",
          isEditing: signal(false)
        }));
      }
      return infoDetailsKeyMap
        .map((detail) => ({
          keyMap: detail,
          value: details[detail.key as keyof TokenDetails],
          isEditing: signal(false)
        }))
        .filter((detail) => detail.value !== undefined);
    }
  });
  userData = linkedSignal({
    source: this.tokenDetails,
    computation: (details) => {
      if (!details) {
        return userDetailsKeyMap.map((detail) => ({
          keyMap: detail,
          value: "",
          isEditing: signal(false)
        }));
      }
      return userDetailsKeyMap
        .map((detail) => ({
          keyMap: detail,
          value: details[detail.key as keyof TokenDetails],
          isEditing: signal(false)
        }))
        .filter((detail) => detail.value !== undefined);
    }
  });
  tokengroupOptions = signal<string[]>([]);
  selectedTokengroup = signal<string[]>([]);
  tokenType = linkedSignal({
    source: this.tokenDetails,
    computation: () => this.tokenDetails()?.tokentype ?? ""
  });
  userRealm = "";
  maxfail = 0;
  isAnyEditingOrRevoked = computed(() => {
    return (
      this.tokenDetailData().some((element) => element.isEditing()) ||
      this.isEditingUser() ||
      this.isEditingInfo() ||
      this.tokenIsRevoked()
    );
  });

  constructor() {
    effect(() => {
      if (!this.tokenDetails()) return;
      this.tokenIsActive.set(this.tokenDetails().active);
      this.tokenIsRevoked.set(this.tokenDetails().revoked);
      this.maxfail = this.tokenDetails().maxfail;
      this.containerService.selectedContainer.set(this.tokenDetails().container_serial);
      this.realmService.selectedRealms.set(this.tokenDetails().realms);
      this.userRealm = this.userData().find((detail) => detail.keyMap.key === "user_realm")?.value || "";
    });
  }

  resetFailCount(): void {
    this.tokenService.resetFailCount(this.tokenSerial()).subscribe({
      next: () => {
        this.tokenDetailResource.reload();
      }
    });
  }

  cancelTokenEdit(element: EditableElement) {
    this.resetEdit(element.keyMap.key);
    element.isEditing.set(!element.isEditing());
  }

  saveTokenEdit(element: EditableElement<string>) {
    switch (element.keyMap.key) {
      case "container_serial":
        this.containerService.selectedContainer.set(this.containerService.selectedContainer()?.trim() ?? null);
        this.saveContainer();
        break;
      case "tokengroup":
        this.saveTokengroup(this.selectedTokengroup());
        break;
      case "realms":
        this.saveRealms();
        break;
      default:
        this.saveTokenDetail(element.keyMap.key, element.value);
        break;
    }
    element.isEditing.set(!element.isEditing());
  }

  toggleTokenEdit(element: EditableElement): void {
    switch (element.keyMap.key) {
      case "tokengroup":
        if (this.tokengroupOptions().length === 0) {
          this.tokenService.getTokengroups().subscribe({
            next: (response) => {
              const tokengroups = response.result?.value || {};
              this.tokengroupOptions.set(Object.keys(tokengroups));
              this.selectedTokengroup.set(
                this.tokenDetailData().find((detail) => detail.keyMap.key === "tokengroup")?.value
              );
            }
          });
        }
        break;
    }
    element.isEditing.set(!element.isEditing());
  }

  saveTokenDetail(key: string, value: string): void {
    this.tokenService.saveTokenDetail(this.tokenSerial(), key, value).subscribe({
      next: () => {
        this.tokenDetailResource.reload();
      }
    });
  }

  saveContainer() {
    const selectedContainer = this.containerService.selectedContainer();
    if (selectedContainer) {
      this.containerService.assignContainer(this.tokenSerial(), selectedContainer).subscribe({
        next: () => {
          this.tokenDetailResource.reload();
        }
      });
    }
  }

  deleteContainer() {
    const selectedContainer = this.containerService.selectedContainer();
    if (selectedContainer) {
      this.containerService.unassignContainer(this.tokenSerial(), selectedContainer).subscribe({
        next: () => {
          this.tokenDetailResource.reload();
        }
      });
    }
  }

  isEditableElement(key: string) {
    const rightEntry = tokenDetailsRightsMap.find((entry) => entry.key === key);
    return !!(rightEntry && this.authService.actionAllowed(rightEntry.right as PolicyAction));
  }

  isNumberElement(key: string) {
    return key === "maxfail" || key === "count_window" || key === "sync_window";
  }

  containerSelected(containerSerial: string) {
    this.isProgrammaticTabChange.set(true);
    this.router.navigateByUrl(ROUTE_PATHS.TOKENS_CONTAINERS_DETAILS + containerSerial);
    this.containerSerial.set(containerSerial);
  }

  openSshMachineAssignDialog() {
    const data: SshMachineAssignDialogData = {
      tokenSerial: this.tokenSerial(),
      tokenDetails: this.tokenDetails(),
      tokenType: this.tokenType()
    };

    this.matDialog.open(TokenSshMachineAssignDialogComponent, {
      data: data
    });
  }

  private resetEdit(type: string): void {
    switch (type) {
      case "container_serial":
        this.containerService.selectedContainer.set("");
        break;
      case "tokengroup":
        this.selectedTokengroup.set(this.tokenDetailData().find((detail) => detail.keyMap.key === "tokengroup")?.value);
        break;
      case "realms":
        this.realmService.selectedRealms.set(
          this.tokenDetailData().find((detail) => detail.keyMap.key === "realms")?.value
        );
        break;
      default:
        this.tokenDetailResource.reload();
        break;
    }
  }

  private saveRealms() {
    this.tokenService.setTokenRealm(this.tokenSerial(), this.realmService.selectedRealms()).subscribe({
      next: () => {
        this.tokenDetailResource.reload();
      }
    });
  }

  private saveTokengroup(value: string[]) {
    this.tokenService.setTokengroup(this.tokenSerial(), value).subscribe({
      next: () => {
        this.tokenDetailResource.reload();
      }
    });
  }
}
